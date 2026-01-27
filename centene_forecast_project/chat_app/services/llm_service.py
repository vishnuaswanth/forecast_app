"""
LLM Service
Real LLM-powered chat service using LangChain + OpenAI for intent classification and query execution.
"""
import logging
import calendar
from typing import Dict, List, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from django.conf import settings
import httpx

from chat_app.services.tools.forecast_tools import (
    get_forecast_data_tool,
    fetch_forecast_data,
    fetch_available_reports,
    validate_report_exists
)
from chat_app.services.tools.ui_tools import (
    generate_forecast_table_html,
    generate_totals_table_html,
    generate_confirmation_ui,
    generate_error_ui,
    generate_clarification_ui,
    generate_available_reports_ui
)
from chat_app.services.tools.validation import (
    ForecastQueryParams,
    IntentClassification,
    ConversationContext,
    IntentCategory
)
from chat_app.utils.context_manager import ConversationContextManager
from chat_app.utils.chunking import ForecastDataChunker
from chat_app.prompts.system_prompts import CLASSIFICATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LLMService:
    """
    Real LLM-powered chat service using LangChain + OpenAI.

    Handles intent classification, parameter extraction, and forecast query execution.
    """

    def __init__(self):
        """Initialize LLM service with OpenAI client and supporting services."""
        # SSL handling for corporate networks
        self.http_client = httpx.Client(
            verify=False,
            timeout=30.0,
            transport=httpx.HTTPTransport(verify=False)
        )

        # Get LLM configuration from settings
        llm_config = getattr(settings, 'LLM_CONFIG', {})

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=llm_config.get('model', 'gpt-4o-mini'),
            temperature=llm_config.get('temperature', 0.1),
            openai_api_key=llm_config.get('api_key'),
            max_tokens=llm_config.get('max_tokens', 4096),
            http_client=self.http_client
        )

        # Structured output LLM for classification
        self.structured_llm = self.llm.with_structured_output(IntentClassification)

        # Context manager
        self.context_manager = ConversationContextManager()

        # Data chunker
        self.chunker = ForecastDataChunker()

        logger.info(f"[LLM Service] Initialized with model: {llm_config.get('model', 'gpt-4o-mini')}")

    async def categorize_intent(
        self,
        user_text: str,
        conversation_id: str,
        message_history: List[dict] = None
    ) -> Dict:
        """
        Classify user intent with LLM.

        Args:
            user_text: User's message (already sanitized by ChatService)
            conversation_id: Conversation identifier
            message_history: Optional list of previous messages

        Returns:
            Dictionary with:
                - category: Intent category
                - confidence: Confidence score
                - parameters: Extracted parameters
                - ui_component: HTML for UI
                - metadata: Additional info
        """
        logger.info(f"[LLM Service] Categorizing intent for: '{user_text[:100]}...'")

        # Get conversation context
        context = await self.context_manager.get_context(conversation_id)

        # Format input into clear, compact prompt
        from chat_app.utils.input_sanitizer import get_sanitizer
        sanitizer = get_sanitizer()

        # Build context dictionary for formatting
        context_dict = {
            'current_forecast_month': context.current_forecast_month,
            'current_forecast_year': context.current_forecast_year,
            'last_platform': context.active_platforms[0] if context.active_platforms else None,
            'last_market': context.active_markets[0] if context.active_markets else None,
        }

        # Format prompt: clear separation of context and user query
        formatted_prompt = sanitizer.format_for_llm(user_text, context_dict)
        logger.debug(f"[LLM Service] Formatted prompt: {formatted_prompt}")

        # Build messages with history
        messages = [SystemMessage(content=CLASSIFICATION_SYSTEM_PROMPT)]

        # Add recent conversation history (last 5 turns)
        if message_history:
            for msg in message_history[-5:]:
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages.append(AIMessage(content=msg['content']))

        # Add formatted user query (compact, clear, preserves all parameters)
        messages.append(HumanMessage(content=formatted_prompt))

        # Classify with structured output
        try:
            classification: IntentClassification = await self.structured_llm.ainvoke(messages)
            logger.info(
                f"[LLM Service] Classification: {classification.category.value} "
                f"(confidence: {classification.confidence:.2f})"
            )
        except Exception as e:
            logger.error(f"[LLM Service] Classification error: {str(e)}", exc_info=True)
            # Fallback to unknown category
            classification = IntentClassification(
                category=IntentCategory.UNKNOWN,
                confidence=0.0,
                reasoning=f"Classification failed: {str(e)}",
                requires_clarification=True,
                missing_parameters=[]
            )

        # Check if we need clarification
        if classification.requires_clarification or classification.confidence < 0.7:
            return await self._handle_clarification(classification, context, user_text)

        # Extract parameters
        params = await self._extract_parameters(user_text, classification, context)

        # Build confirmation UI
        ui_component = generate_confirmation_ui(classification.category.value, params)

        return {
            'category': classification.category.value,
            'confidence': classification.confidence,
            'parameters': params,
            'ui_component': ui_component,
            'metadata': {
                'reasoning': classification.reasoning,
                'missing_params': classification.missing_parameters,
                'context_used': context.dict() if context else {}
            }
        }

    async def _extract_parameters(
        self,
        user_text: str,
        classification: IntentClassification,
        context: ConversationContext
    ) -> dict:
        """
        Extract parameters using LLM with Pydantic validation.

        Args:
            user_text: User's message
            classification: Intent classification result
            context: Conversation context

        Returns:
            Dictionary of extracted parameters
        """
        if classification.category == IntentCategory.GET_FORECAST_DATA:
            # Use structured output with ForecastQueryParams
            # Build compact context
            context_parts = []
            if context.current_forecast_month:
                month_name = calendar.month_name[context.current_forecast_month]
                context_parts.append(f"Last: {month_name} {context.current_forecast_year or ''}")
            if context.active_platforms:
                context_parts.append(f"Platforms: {', '.join(context.active_platforms[:3])}")
            if context.active_markets:
                context_parts.append(f"Markets: {', '.join(context.active_markets[:3])}")

            context_str = " | ".join(context_parts) if context_parts else "No previous filters"

            # Compact extraction prompt - preserves all parameters
            extraction_prompt = f"""
Query: {user_text}
Context: {context_str}

Extract: month (1-12), year, platforms[], markets[], localities[], states[], case_types[], forecast_months[]
Rules:
- Extract ALL mentioned values
- Use context only if parameter not stated
- Multi-values → lists: "CA and TX" → ["CA", "TX"]
- Month names → numbers: "March" → 3
- "totals only" → show_totals_only=True
- Preserve exact case type names: "Claims Processing", "Enrollment"
"""

            param_llm = self.llm.with_structured_output(ForecastQueryParams)

            try:
                params = await param_llm.ainvoke([HumanMessage(content=extraction_prompt)])
                logger.info(f"[LLM Service] Extracted parameters: {params.dict()}")
                return params.dict()
            except Exception as e:
                logger.warning(f"[LLM Service] Parameter extraction failed: {str(e)}")
                # Fallback to context defaults
                return {
                    'month': context.current_forecast_month or datetime.now().month,
                    'year': context.current_forecast_year or datetime.now().year
                }

        return {}

    async def _handle_clarification(
        self,
        classification: IntentClassification,
        context: ConversationContext,
        user_text: str
    ) -> dict:
        """
        Generate clarification request.

        Args:
            classification: Intent classification result
            context: Conversation context
            user_text: User's message

        Returns:
            Dictionary with clarification response
        """
        logger.info(f"[LLM Service] Handling clarification for: {classification.category.value}")

        # Use LLM to generate natural clarification
        clarification_prompt = f"""
The user said: "{user_text}"

Classification: {classification.category}
Confidence: {classification.confidence}
Missing: {classification.missing_parameters}

Generate a friendly, concise clarification question asking for the missing information.
Be specific about what's needed.
"""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=clarification_prompt)])
            clarification_text = response.content
        except Exception as e:
            logger.error(f"[LLM Service] Clarification generation error: {str(e)}")
            clarification_text = "I need more information to help you. Could you please provide more details?"

        return {
            'category': 'clarification_needed',
            'confidence': 0.0,
            'parameters': {},
            'ui_component': generate_clarification_ui(clarification_text),
            'metadata': {'original_classification': classification.dict() if classification else {}}
        }

    async def execute_available_reports_query(
        self,
        parameters: dict,
        conversation_id: str
    ) -> Dict:
        """
        List available forecast reports.

        Fetches all available reports from the backend and generates a UI card
        with report details. Uses the LLM to generate a natural language summary.

        Args:
            parameters: Query parameters (unused for this query, no params required)
            conversation_id: Conversation identifier

        Returns:
            Dictionary with:
                - success: Boolean
                - message: Natural language summary
                - data: Raw reports data
                - ui_component: HTML card listing reports
                - metadata: Report count info
        """
        logger.info("[LLM Service] Executing available reports query")

        try:
            data = await fetch_available_reports()
        except Exception as e:
            logger.error(f"[LLM Service] Failed to fetch available reports: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f"Failed to retrieve available reports: {str(e)}",
                'ui_component': generate_error_ui(f"Could not fetch available reports: {str(e)}")
            }

        # Generate UI card
        ui_html = generate_available_reports_ui(data)

        # Build natural language summary
        reports = data.get('reports', [])
        current_reports = [r for r in reports if r.get('is_valid', False)]
        total = len(reports)

        if total == 0:
            message = (
                "There are no forecast reports currently available. "
                "Please upload forecast data to get started."
            )
        else:
            # Build summary of available periods
            report_periods = [f"{r.get('month', '?')} {r.get('year', '?')}" for r in reports[:5]]
            periods_str = ", ".join(report_periods)
            if total > 5:
                periods_str += f", and {total - 5} more"

            message = (
                f"I found {total} forecast report{'s' if total != 1 else ''} available"
                f" ({len(current_reports)} current). "
                f"Available periods: {periods_str}."
            )

        logger.info(f"[LLM Service] Available reports query complete - {total} reports")

        return {
            'success': True,
            'message': message,
            'data': data,
            'ui_component': ui_html,
            'metadata': {
                'report_count': total,
                'current_count': len(current_reports)
            }
        }

    async def execute_forecast_query(
        self,
        parameters: dict,
        conversation_id: str
    ) -> Dict:
        """
        Execute forecast data query with pre-flight validation and combination diagnosis.

        NEW FEATURES:
        1. Pre-flight validation using FilterValidator
        2. Auto-correction for high-confidence typos (>90%)
        3. Confirmation UI for medium-confidence matches (60-90%)
        4. Combination diagnosis when query returns 0 records

        Args:
            parameters: Query parameters
            conversation_id: Conversation identifier

        Returns:
            Dictionary with:
                - success: Boolean
                - message: Status message
                - data: Forecast data
                - ui_component: HTML for display
                - metadata: Additional info (including validation_summary)
        """
        logger.info(f"[LLM Service] Executing forecast query with params: {parameters}")

        # Validate parameters
        try:
            params = ForecastQueryParams(**parameters)
        except Exception as e:
            logger.error(f"[LLM Service] Parameter validation error: {str(e)}")
            return {
                'success': False,
                'message': f"Invalid parameters: {str(e)}",
                'ui_component': generate_error_ui(f"Invalid parameters: {str(e)}")
            }

        # STEP 0: Validate report exists for the given month/year
        try:
            validation = await validate_report_exists(params.month, params.year)

            if not validation['exists']:
                month_name = calendar.month_name[params.month]
                logger.info(
                    f"[LLM Service] No report for {month_name} {params.year} - "
                    f"showing available reports"
                )

                # Build UI showing available reports
                available_reports = validation.get('available_reports', [])
                reports_data = {
                    'reports': available_reports,
                    'total_reports': len(available_reports)
                }
                ui_html = generate_available_reports_ui(reports_data)

                # Add header message about the missing report
                no_data_header = f'''
                <div class="alert alert-warning mb-3">
                    <h6 class="alert-heading">
                        <i class="bi bi-exclamation-triangle"></i> No Data Available
                    </h6>
                    <p class="mb-0">
                        No forecast report exists for <strong>{month_name} {params.year}</strong>.
                        Please choose from the available reports below, or upload data for this period.
                    </p>
                </div>
                '''

                return {
                    'success': False,
                    'message': f'No forecast report found for {month_name} {params.year}.',
                    'ui_component': no_data_header + ui_html,
                    'metadata': {
                        'report_validation': 'no_report',
                        'requested_period': f'{month_name} {params.year}',
                        'available_report_count': len(available_reports)
                    }
                }
        except Exception as e:
            # If validation fails, log and proceed (don't block the query)
            logger.warning(
                f"[LLM Service] Report validation failed: {str(e)} - proceeding without validation"
            )

        # PRE-FLIGHT FILTER VALIDATION
        from chat_app.services.tools.validation_tools import FilterValidator, ConfidenceLevel
        from chat_app.services.tools.validation import FilterValidationSummary
        from chat_app.services.tools.ui_tools import generate_validation_confirmation_ui

        validator = FilterValidator()

        try:
            validation_results = await validator.validate_all(params)
        except Exception as e:
            logger.warning(f"[LLM Service] Validation failed: {e} - proceeding without validation")
            validation_results = {}

        # Process validation results
        validation_summary = FilterValidationSummary()

        for field_name, results in validation_results.items():
            for result in results:
                if result.confidence_level == ConfidenceLevel.HIGH:
                    # Auto-correct (>90% confidence)
                    if result.corrected_value:
                        validation_summary.auto_corrected.setdefault(field_name, []).append(
                            result.corrected_value
                        )
                        # Apply correction to params
                        field_list = getattr(params, field_name, None)
                        if field_list and result.original_value in field_list:
                            idx = field_list.index(result.original_value)
                            field_list[idx] = result.corrected_value
                            logger.info(
                                f"[LLM Service] Auto-corrected: "
                                f"{result.original_value} → {result.corrected_value}"
                            )

                elif result.confidence_level == ConfidenceLevel.MEDIUM:
                    # Needs confirmation (60-90% confidence)
                    validation_summary.needs_confirmation.setdefault(field_name, []).append(
                        (result.original_value, result.corrected_value, result.confidence)
                    )

                elif not result.is_valid:
                    # Rejected (<60% confidence)
                    validation_summary.rejected.setdefault(field_name, []).append(
                        (result.original_value, result.suggestions)
                    )

        # If we have confirmations or rejections, return confirmation UI
        if validation_summary.has_issues():
            logger.info(
                f"[LLM Service] Validation issues: "
                f"{validation_summary.get_confirmation_count()} confirmations, "
                f"{validation_summary.get_rejection_count()} rejections"
            )

            return {
                'success': False,
                'message': 'Filter validation requires user input',
                'ui_component': generate_validation_confirmation_ui(
                    validation_summary,
                    params
                ),
                'metadata': {
                    'validation_summary': validation_summary.dict(),
                    'requires_confirmation': True
                }
            }

        # Fetch data using tool (with validation disabled since we already validated)
        try:
            data = await fetch_forecast_data(params, enable_validation=False)
        except Exception as e:
            logger.error(f"[LLM Service] API call failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f"API error: {str(e)}",
                'ui_component': generate_error_ui(f"Failed to fetch data: {str(e)}")
            }

        # Cache data in context
        await self.context_manager.update_entities(
            conversation_id,
            last_forecast_data=data,
            current_forecast_month=params.month,
            current_forecast_year=params.year,
            active_platforms=params.platforms or [],
            active_markets=params.markets or [],
            active_localities=params.localities or [],
            active_states=params.states or []
        )

        # Check if we got 0 records - trigger combination diagnosis (NEW)
        if len(data.get('records', [])) == 0:
            logger.info("[LLM Service] Query returned 0 records - starting combination diagnosis")

            from chat_app.services.tools.validation_tools import CombinationDiagnostic

            diagnostic = CombinationDiagnostic()

            try:
                diagnosis_result = await diagnostic.diagnose(params, data)

                # Generate diagnostic UI with LLM-powered guidance
                ui_html = await self._generate_diagnostic_guidance(
                    params,
                    diagnosis_result
                )

                return {
                    'success': False,
                    'message': 'No records found - diagnosis provided',
                    'data': data,
                    'ui_component': ui_html,
                    'metadata': {
                        'diagnosis': {
                            'is_data_issue': diagnosis_result.is_data_issue,
                            'is_combination_issue': diagnosis_result.is_combination_issue,
                            'problematic_filters': diagnosis_result.problematic_filters,
                            'total_records_available': diagnosis_result.total_records_available
                        },
                        'validation_summary': validation_summary.dict()
                    }
                }

            except Exception as e:
                logger.error(f"[LLM Service] Diagnosis failed: {e}", exc_info=True)
                # Fallback to existing _generate_no_data_guidance
                ui_html = await self._generate_no_data_guidance(params, data)

                return {
                    'success': False,
                    'message': 'No data found - suggestions provided',
                    'data': data,
                    'ui_component': ui_html,
                    'metadata': {'validation_summary': validation_summary.dict()}
                }

        # Cache data in context
        await self.context_manager.update_entities(
            conversation_id,
            last_forecast_data=data,
            current_forecast_month=params.month,
            current_forecast_year=params.year,
            active_platforms=params.platforms or [],
            active_markets=params.markets or [],
            active_localities=params.localities or [],
            active_states=params.states or []
        )

        # Generate UI based on user preference
        if params.show_totals_only:
            ui_html = generate_totals_table_html(data.get('totals', {}), data.get('months', {}))
            message = f"Here are the forecast totals for {calendar.month_name[params.month]} {params.year}"
        else:
            records = data.get('records', [])

            if len(records) <= 5:
                # Show all records
                ui_html = generate_forecast_table_html(records, data.get('months', {}), show_full=True)
                message = f"Found {len(records)} forecast records"
            else:
                # Show top 5 with "View Full" button
                ui_html = generate_forecast_table_html(
                    records,
                    data.get('months', {}),
                    show_full=False,
                    max_preview=5
                )
                message = f"Showing 5 of {len(records)} forecast records. Click 'View All' to see more."

        # Add validation summary note if auto-corrections were made
        if validation_summary.get_correction_count() > 0:
            corrections_note = "<div class='alert alert-info mt-2'><small>"
            corrections_note += f"Note: Auto-corrected {validation_summary.get_correction_count()} filter value(s). "
            for field_name, corrections in validation_summary.auto_corrected.items():
                corrections_note += f"{field_name}: {', '.join(corrections)}. "
            corrections_note += "</small></div>"
            ui_html += corrections_note

        logger.info(f"[LLM Service] Query executed successfully - {len(data.get('records', []))} records")

        return {
            'success': True,
            'message': message,
            'data': data,
            'ui_component': ui_html,
            'metadata': {
                'record_count': len(data.get('records', [])),
                'months_included': list(data.get('months', {}).values()),
                'filters_applied': data.get('filters_applied', {}),
                'validation_summary': validation_summary.dict()
            }
        }

    async def _generate_no_data_guidance(
        self,
        params: ForecastQueryParams,
        api_response: dict
    ) -> str:
        """
        Generate helpful LLM-powered guidance when no forecast data is found.

        Uses the LLM to provide actionable suggestions based on the query parameters
        and API response context.

        Args:
            params: Query parameters that returned no results
            api_response: Full API response (with empty records)

        Returns:
            HTML string with helpful guidance
        """
        # Build context for LLM
        month_name = calendar.month_name[params.month]

        # Extract applied filters
        applied_filters = []
        if params.platforms:
            applied_filters.append(f"Platforms: {', '.join(params.platforms)}")
        if params.markets:
            applied_filters.append(f"Markets: {', '.join(params.markets)}")
        if params.localities:
            applied_filters.append(f"Localities: {', '.join(params.localities)}")
        if params.main_lobs:
            applied_filters.append(f"LOBs: {', '.join(params.main_lobs)}")
        if params.states:
            applied_filters.append(f"States: {', '.join(params.states)}")
        if params.case_types:
            applied_filters.append(f"Case Types: {', '.join(params.case_types)}")
        if params.forecast_months:
            applied_filters.append(f"Forecast Months: {', '.join(params.forecast_months)}")

        filters_text = "\n- ".join(applied_filters) if applied_filters else "None (querying all data)"

        # Create LLM prompt for helpful guidance
        guidance_prompt = f"""
The user queried forecast data with these parameters:
- Report Month: {month_name} {params.year}
- Filters Applied:
  {filters_text}

The API returned ZERO records (no data found).

Generate a helpful, empathetic response that:
1. Acknowledges that no data was found for their specific query
2. Provides 2-3 actionable suggestions such as:
   - Check if forecast data has been uploaded for {month_name} {params.year}
   - Try removing some filters to broaden the search
   - Verify the month/year combination is correct
   - Check if data exists for nearby months (e.g., {calendar.month_name[params.month - 1 if params.month > 1 else 12]} or {calendar.month_name[params.month + 1 if params.month < 12 else 1]})
   - Upload forecast data if it hasn't been uploaded yet
3. Offer to help with a different query

Keep the tone friendly, professional, and solution-oriented. Format as plain text (not HTML).
Be concise - maximum 4-5 sentences.
"""

        try:
            logger.info(f"[LLM Service] Generating no-data guidance for {month_name} {params.year}")
            response = await self.llm.ainvoke([HumanMessage(content=guidance_prompt)])
            guidance_text = response.content.strip()

            logger.info(f"[LLM Service] Generated guidance: {guidance_text[:100]}...")
        except Exception as e:
            logger.error(f"[LLM Service] Failed to generate guidance: {str(e)}")
            # Fallback message
            guidance_text = (
                f"No forecast data was found for {month_name} {params.year} with your specified filters. "
                f"Please check if the data has been uploaded for this period, or try adjusting your filters."
            )

        # Build HTML with helpful styling
        html = f'''
        <div class="alert alert-warning" role="alert">
            <h6 class="alert-heading"><i class="bi bi-exclamation-triangle"></i> No Data Found</h6>
            <p class="mb-2">{guidance_text}</p>
            <hr>
            <div class="mt-2">
                <strong>Your Query:</strong>
                <ul class="mb-0 mt-1">
                    <li>Report Period: {month_name} {params.year}</li>
                    {f'<li>Filters: {", ".join(applied_filters)}</li>' if applied_filters else '<li>No filters applied</li>'}
                </ul>
            </div>
            <div class="mt-3">
                <small class="text-muted">
                    <strong>Suggestions:</strong> Try uploading forecast data for this period,
                    or ask me to show data for a different month/year.
                </small>
            </div>
        </div>
        '''

        return html

    async def _generate_diagnostic_guidance(
        self,
        params: ForecastQueryParams,
        diagnosis: 'CombinationDiagnosticResult'
    ) -> str:
        """
        Generate LLM-powered diagnostic guidance for filter combination issues.

        Uses the LLM to explain the diagnosis in natural language and provide
        actionable recommendations.

        Args:
            params: Original query parameters
            diagnosis: Combination diagnostic result from CombinationDiagnostic

        Returns:
            HTML string with diagnostic guidance
        """
        from langchain.schema import HumanMessage
        from chat_app.services.tools.ui_tools import generate_combination_diagnostic_ui

        # Build context for LLM
        month_name = calendar.month_name[params.month]

        if diagnosis.is_data_issue:
            # Simple data availability issue - use basic template
            return generate_combination_diagnostic_ui(
                diagnosis.diagnosis_message,
                {},
                diagnosis.total_records_available
            )

        # Build LLM prompt for combination issue
        guidance_prompt = f"""
The user queried forecast data but got 0 results due to filter combination issues.

Query Details:
- Month/Year: {month_name} {params.year}
- Total records available: {diagnosis.total_records_available}

Problematic Filters: {', '.join(diagnosis.problematic_filters)}

Applied Filters:
"""

        if params.platforms:
            guidance_prompt += f"\n- Platforms: {', '.join(params.platforms)}"
        if params.markets:
            guidance_prompt += f"\n- Markets: {', '.join(params.markets)}"
        if params.localities:
            guidance_prompt += f"\n- Localities: {', '.join(params.localities)}"
        if params.states:
            guidance_prompt += f"\n- States: {', '.join(params.states)}"
        if params.case_types:
            guidance_prompt += f"\n- Case Types: {', '.join(params.case_types)}"

        guidance_prompt += f"\n\nWorking Combinations:"
        for filter_name, valid_values in diagnosis.working_combinations.items():
            guidance_prompt += f"\n- {filter_name}: {', '.join(valid_values[:5])}"
            if len(valid_values) > 5:
                guidance_prompt += f" (and {len(valid_values) - 5} more)"

        guidance_prompt += """

Generate a helpful, empathetic response that:
1. Explains why the combination didn't work
2. Suggests removing the problematic filter(s)
3. Provides 2-3 specific alternatives using the working combinations
4. Offers to help with a different query

Keep the tone friendly and solution-oriented. Format as plain text (not HTML).
Be concise - maximum 5-6 sentences.
"""

        try:
            logger.info(f"[LLM Service] Generating combination diagnostic guidance")
            response = await self.llm.ainvoke([HumanMessage(content=guidance_prompt)])
            guidance_text = response.content.strip()

            logger.info(f"[LLM Service] Generated diagnostic guidance: {guidance_text[:100]}...")
        except Exception as e:
            logger.error(f"[LLM Service] Failed to generate diagnostic guidance: {str(e)}")
            # Fallback to simple message
            guidance_text = diagnosis.diagnosis_message

        # Generate HTML UI with LLM guidance
        return generate_combination_diagnostic_ui(
            guidance_text,
            diagnosis.working_combinations,
            diagnosis.total_records_available
        )

    def _build_context_prompt(self, context: ConversationContext) -> str:
        """
        Build context information for LLM classification.

        Args:
            context: Conversation context

        Returns:
            Context prompt string
        """
        month_name = (
            calendar.month_name[context.current_forecast_month]
            if context.current_forecast_month else 'None'
        )

        # Build active filters summary
        active_filters = []
        if context.active_platforms:
            active_filters.append(f"Platforms={context.active_platforms}")
        if context.active_markets:
            active_filters.append(f"Markets={context.active_markets}")
        if context.active_localities:
            active_filters.append(f"Localities={context.active_localities}")
        if context.active_states:
            active_filters.append(f"States={context.active_states}")

        filters_str = ", ".join(active_filters) if active_filters else "None"

        last_record_count = (
            context.last_forecast_data.get('total_records', 0)
            if context.last_forecast_data else 0
        )

        return f"""
Conversation Context:
- Forecast period: {month_name} {context.current_forecast_year or 'None'}
- Active filters: {filters_str}
- Turn count: {context.turn_count}
- Has cached data: {'Yes' if context.last_forecast_data else 'No'}
- Last query returned: {last_record_count} records
"""
