"""
LLM Service
CoT tool-calling agent: message in → LLM reasons → calls the right tool →
data + UI returned immediately. No preprocessing, no confirmation round-trip.

Error Handling:
- All LLM calls are wrapped with proper exception handling
- OpenAI/LangChain errors are converted to LLMError subclasses
- All error responses include safe UI components and proper logging
"""
import json
import logging
import time
from typing import Dict, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from django.conf import settings
import httpx

from chat_app.services.tools.agent_tools import make_agent_tools
from chat_app.services.tools.ui_tools import generate_error_ui, generate_fte_details_ui, generate_cph_preview_ui
from chat_app.services.tools.validation import ConversationContext
from chat_app.services.tools.calculation_tools import calculate_cph_impact, determine_locality, validate_cph_value
from chat_app.utils.context_manager import ConversationContextManager
from chat_app.utils.llm_logger import get_llm_logger, get_correlation_id, create_correlation_id
from chat_app.exceptions import classify_openai_error
from chat_app.utils.error_handler import log_error

logger = logging.getLogger(__name__)
llm_logger = get_llm_logger()


class LLMService:
    """
    CoT tool-calling agent using LangChain + OpenAI.

    run_agent() is the single entry point:
      1. Build context-aware system prompt
      2. Bind tools to the LLM
      3. LLM reasons (CoT) and optionally calls a tool
      4. Execute the tool → get UI + data
      5. LLM writes a natural language response
      6. Return {text, ui_component, data}
    """

    def __init__(self):
        """Initialize LLM service with OpenAI client."""
        # SSL handling for corporate networks
        self.http_client = httpx.Client(
            verify=False,
            timeout=30.0,
            transport=httpx.HTTPTransport(verify=False),
        )
        self.http_async_client = httpx.AsyncClient(
            verify=False,
            timeout=30.0,
            transport=httpx.AsyncHTTPTransport(verify=False),
        )

        llm_config = getattr(settings, 'LLM_CONFIG', {})
        self.model_name = llm_config.get('model', 'gpt-4o-mini')
        self.temperature = llm_config.get('temperature', 0.1)
        self.max_tokens = llm_config.get('max_tokens', 4096)

        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            openai_api_key=llm_config.get('api_key'),
            max_tokens=self.max_tokens,
            http_client=self.http_client,
            http_async_client=self.http_async_client,
        )

        self.context_manager = ConversationContextManager()

        logger.info(f"[LLM Service] Initialized with model: {self.model_name}")
        llm_logger._log(
            logging.INFO,
            'llm_service_initialized',
            {'model': self.model_name, 'temperature': self.temperature, 'max_tokens': self.max_tokens},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    async def run_agent(
        self,
        user_text: str,
        conversation_id: str,
        message_history: List[dict] = None,
        selected_row: dict = None,
    ) -> Dict:
        """
        CoT agent: reason → call tool → write response.

        Args:
            user_text: Sanitized user message
            conversation_id: Conversation identifier
            message_history: Recent chat history (list of {role, content} dicts)
            selected_row: Currently selected forecast row (optional)

        Returns:
            {'text': str, 'ui_component': str, 'data': dict}
        """
        correlation_id = get_correlation_id() or create_correlation_id(conversation_id)
        start_time = time.time()

        logger.info(f"[LLM Service] run_agent: '{user_text[:120]}'")

        # Persist selected_row into context if provided
        if selected_row:
            await self.context_manager.update_entities(
                conversation_id, selected_row=selected_row
            )

        # Get current context
        context = await self.context_manager.get_context(conversation_id)

        # Build tools and bind them to the LLM
        tools = make_agent_tools(conversation_id, context, self.context_manager)
        llm_with_tools = self.llm.bind_tools(tools)

        # Build message list
        system_prompt = self._build_system_prompt(context, selected_row)
        messages: List = [SystemMessage(content=system_prompt)]

        if message_history:
            for msg in message_history[-10:]:
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages.append(AIMessage(content=msg['content']))

        messages.append(HumanMessage(content=user_text))

        # Log LLM request
        llm_logger.log_llm_request(
            correlation_id=correlation_id,
            model=self.model_name,
            messages=[{'role': type(m).__name__, 'content': m.content} for m in messages],
            config={'temperature': self.temperature},
            request_type='agent_run',
        )

        # First LLM call (may produce tool calls)
        try:
            response = await llm_with_tools.ainvoke(messages)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            llm_error = classify_openai_error(e)
            log_error(logger, llm_error, {'duration_ms': duration_ms}, correlation_id, 'run_agent')
            raise llm_error

        ui_component = ''
        tool_data = {}

        if response.tool_calls:
            messages.append(response)  # AIMessage with tool calls

            for tool_call in response.tool_calls:
                logger.info(f"[LLM Service] Calling tool: {tool_call['name']} args={tool_call.get('args')}")
                llm_logger.log_tool_execution(
                    correlation_id=correlation_id,
                    tool_name=tool_call['name'],
                    parameters=tool_call.get('args', {}),
                    status='started',
                )

                tool_start = time.time()
                result = await self._invoke_tool(tools, tool_call)
                tool_duration = (time.time() - tool_start) * 1000

                llm_logger.log_tool_execution(
                    correlation_id=correlation_id,
                    tool_name=tool_call['name'],
                    parameters=tool_call.get('args', {}),
                    result_summary={'has_ui': bool(result.get('ui_component'))},
                    duration_ms=tool_duration,
                    status='success',
                )

                if result.get('ui_component'):
                    ui_component = result['ui_component']
                if result.get('data'):
                    tool_data = result['data']

                messages.append(ToolMessage(
                    content=result.get('message', ''),
                    tool_call_id=tool_call['id'],
                ))

            # Second LLM call to generate natural language response
            try:
                final = await self.llm.ainvoke(messages)
                text_response = final.content
            except Exception as e:
                logger.warning(f"[LLM Service] Final response generation failed: {e}")
                text_response = result.get('message', 'Done.')
        else:
            # No tool call – clarification or fallback
            text_response = response.content

        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"[LLM Service] run_agent complete in {duration_ms:.0f}ms")
        llm_logger.log_llm_response(
            correlation_id=correlation_id,
            response={'has_tool_calls': bool(response.tool_calls), 'text_length': len(text_response)},
            duration_ms=duration_ms,
            model=self.model_name,
        )

        return {
            'text': text_response,
            'ui_component': ui_component,
            'data': tool_data,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _invoke_tool(self, tools: list, tool_call: dict) -> dict:
        """Find and invoke the matching tool, returning a normalised result dict."""
        tool_name = tool_call['name']
        tool_args = tool_call.get('args', {})

        for tool in tools:
            if tool.name == tool_name:
                try:
                    result = await tool.ainvoke(tool_args)
                    if isinstance(result, dict):
                        return result
                    return {'message': str(result), 'ui_component': '', 'data': {}}
                except Exception as e:
                    logger.error(f"[LLM Service] Tool '{tool_name}' raised: {e}", exc_info=True)
                    return {
                        'message': f'Tool {tool_name} failed: {str(e)}',
                        'ui_component': generate_error_ui(
                            f'Failed to execute {tool_name}: {str(e)}',
                            error_type='api', admin_contact=True
                        ),
                        'data': {},
                    }

        logger.error(f"[LLM Service] Tool not found: {tool_name}")
        return {
            'message': f'Unknown tool: {tool_name}',
            'ui_component': generate_error_ui(f'Unknown tool: {tool_name}'),
            'data': {},
        }

    def _build_system_prompt(
        self,
        context: ConversationContext,
        selected_row: dict = None,
    ) -> str:
        """
        Build the CoT system prompt with context summary and optional row info.
        """
        context_summary = context.get_context_summary_for_llm()

        selected_row_block = ''
        if selected_row:
            selected_row_block = f"""
SELECTED ROW:
  Main LOB: {selected_row.get('main_lob', 'N/A')}
  State:    {selected_row.get('state', 'N/A')}
  Case Type:{selected_row.get('case_type', 'N/A')}
  CPH:      {selected_row.get('target_cph', 'N/A')}
  Monthly data: {json.dumps(selected_row.get('months', {}), indent=2)}

If the user refers to "this row", "the selected row", "FTEs", or wants to change CPH,
they mean the selected row above.
"""

        return f"""You are a workforce capacity planning assistant for Centene.

CURRENT SESSION CONTEXT:
{context_summary}
{selected_row_block}
INSTRUCTIONS — Think step by step before calling a tool:
1. Understand exactly what the user wants (data query, filter change, CPH edit, FTE details, report list, etc.)
2. Identify any filters mentioned (month, year, platform, locality, state, case type)
3. If month/year is missing AND not in context → reply with a plain clarification question asking which month/year the user wants. Do NOT call any tool.
4. Apply context filter rules:
   - "also" / "add" / "include" → operation="extend" in update_filters OR include in get_forecast_data
   - "only" / "change to" / "switch" → operation="replace"
   - "remove" / "without" / "exclude" → operation="remove"
   - "reset filters" / "clear filters" / "show all" → operation="reset" in update_filters
   - "start over" / "clear everything" / "reset all" → call clear_context
   - No filter mentioned → use context filters as defaults for get_forecast_data
5. Call the appropriate tool with complete parameters
6. After the tool returns, write a clear, friendly natural language summary of what was retrieved or done.

TOOLS AVAILABLE:
  get_forecast_data        – fetch records/totals for a period + filters
  get_available_reports    – list available report periods
  get_fte_details          – FTE breakdown for the selected row
  preview_cph_change       – CPH impact preview for the selected row
  update_filters           – merge/replace/remove/reset context filters without fetching data
  clear_context            – wipe all context (full reset)

IMPORTANT:
- Always prefer calling get_forecast_data with the full merged filter set rather than
  calling update_filters then immediately get_forecast_data in two steps.
- Only call update_filters alone when the user explicitly asks to change filters
  WITHOUT requesting new data in the same turn.
"""

    # ─────────────────────────────────────────────────────────────────────────
    # Legacy helpers kept for CPH update flow (still used by chat_service)
    # ─────────────────────────────────────────────────────────────────────────

    async def generate_fte_details(self, row_data: dict, conversation_id: str) -> dict:
        """
        Generate FTE details response for selected row.
        (Legacy path – used internally; agent flow uses get_fte_details tool.)
        """
        correlation_id = get_correlation_id() or create_correlation_id(conversation_id)
        logger.info(f"[LLM Service] Generating FTE details for row: {row_data.get('main_lob')}")

        ui_component = generate_fte_details_ui(row_data)

        return {
            'success': True,
            'category': 'get_fte_details',
            'confidence': 1.0,
            'message': f"FTE details for {row_data.get('main_lob')}",
            'ui_component': ui_component,
            'response_type': 'fte_details',
            'metadata': {
                'row_key': (
                    f"{row_data.get('main_lob')}|{row_data.get('state')}|{row_data.get('case_type')}"
                ),
                'correlation_id': correlation_id,
            },
        }

    async def generate_cph_preview(
        self,
        row_data: dict,
        new_cph: float,
        conversation_id: str,
        context: 'ConversationContext' = None,
    ) -> dict:
        """
        Calculate new values with modified CPH and generate preview.
        (Legacy path – CPH confirm flow still uses this.)
        """
        correlation_id = get_correlation_id() or create_correlation_id(conversation_id)
        logger.info(f"[LLM Service] Generating CPH preview: {row_data.get('target_cph')} -> {new_cph}")

        is_valid, error_msg = validate_cph_value(new_cph)
        if not is_valid:
            return {
                'success': False,
                'category': 'modify_cph',
                'confidence': 1.0,
                'message': error_msg,
                'ui_component': generate_error_ui(error_msg),
                'response_type': 'assistant_response',
                'metadata': {'error': 'invalid_cph_value', 'correlation_id': correlation_id},
            }

        locality = determine_locality(
            row_data.get('main_lob', ''),
            row_data.get('case_type', ''),
        )
        report_configuration = context.report_configuration if context else None
        impact_data = calculate_cph_impact(row_data, new_cph, report_configuration)
        ui_component = generate_cph_preview_ui(row_data, new_cph, impact_data, locality)

        return {
            'success': True,
            'category': 'modify_cph',
            'confidence': 1.0,
            'message': f"Preview of CPH change from {row_data.get('target_cph')} to {new_cph}",
            'ui_component': ui_component,
            'response_type': 'cph_preview',
            'preview_data': {
                'main_lob': row_data.get('main_lob'),
                'state': row_data.get('state'),
                'case_type': row_data.get('case_type'),
                'old_cph': row_data.get('target_cph'),
                'new_cph': new_cph,
                'locality': locality,
                'months': impact_data,
            },
            'metadata': {
                'old_cph': row_data.get('target_cph'),
                'new_cph': new_cph,
                'locality': locality,
                'correlation_id': correlation_id,
            },
        }

    async def extract_cph_value(self, user_text: str, current_cph: float) -> float:
        """
        Extract new CPH value from user message via LLM.
        Handles: "change to 3.5", "increase by 10%", "set target CPH to 4"

        Raises:
            ValueError: If CPH value cannot be extracted
        """
        prompt = f"""Extract the new CPH value from this user message.
Current CPH: {current_cph}
User message: "{user_text}"

Rules:
- "change to X" / "set to X" / "set CPH to X" → return X
- "increase by X%" → return {current_cph} * (1 + X/100), rounded to 2 decimals
- "decrease by X%" → return {current_cph} * (1 - X/100), rounded to 2 decimals
- "increase by X" → return {current_cph} + X
- "decrease by X" → return {current_cph} - X
- Just a number like "3.5" → return 3.5

Respond with ONLY the numeric value, nothing else. Example: 3.5"""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            return float(raw)
        except (ValueError, TypeError):
            import re
            matches = re.findall(r'\d+\.?\d*', user_text)
            if matches:
                return float(matches[0])
            raise ValueError(f"Could not extract CPH value from: {user_text}")
        except Exception as e:
            logger.error(f"[LLM Service] CPH extraction error: {e}")
            raise ValueError(f"Could not extract CPH value: {str(e)}")
