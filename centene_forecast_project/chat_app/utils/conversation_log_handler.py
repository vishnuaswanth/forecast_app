"""
ConversationFileHandler - per-conversation human-readable log files.

Creates one log file per conversation under logs/conversations/:
    logs/conversations/{conversation_id}.log

Each file is divided into TURNS, one per unique correlation_id.
Within a turn, every pipeline stage is printed in a fixed-width,
time-stamped, labelled format that reads top-to-bottom without
needing to understand JSON.

Example output
──────────────
════════════════════════════════════════════════════════════════════════════════
  CONVERSATION: a1b2c3d4-e5f6-7890-abcd-ef1234567890
  Started: 2026-02-23 10:30:00 UTC
════════════════════════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────────────────────────
  TURN 1  ·  2026-02-23 10:30:00  ·  abc12345-none0000-1708012345678
────────────────────────────────────────────────────────────────────────────────
  10:30:00.123  [MESSAGE START  ]  ▶  Type: user_message
  10:30:00.124  [INPUT          ]     Message: "show me forecast for january CA"
                                     Modified by sanitizer: No  |  Length: 38 chars
  10:30:00.200  [LLM REQUEST    ]  →  Model: gpt-4  |  Messages in context: 3
  10:30:03.441  [LLM RESPONSE   ]  ←  Duration: 3241ms
                                     Tokens: 472 total  (410 prompt + 62 completion)
  10:30:03.450  [CLASSIFIED     ]  ◆  Category: get_forecast_data  |  Confidence: 91%
                                     Reasoning: User asked for forecast data for January CA
  10:30:03.490  [COMPLETE       ]  ■  SUCCESS  |  Total time: 3490ms  |  Category: get_forecast_data

────────────────────────────────────────────────────────────────────────────────
  TURN 2  ·  2026-02-23 10:30:15  ·  abc12345-def67890-1708012360000
────────────────────────────────────────────────────────────────────────────────
  10:30:15.001  [TOOL START     ]  ▶  Tool: confirm_category_get_forecast_data
  10:30:15.010  [API CALL       ]  →  GET /forecast/data  →  200  (180ms)
  10:30:15.011  [QUERY          ]  ←  ✓ success  |  Records: 42  |  Duration: 185ms
  10:30:15.015  [TOOL DONE      ]  ✓  Tool: confirm_category_get_forecast_data  |  Duration: 210ms
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Event → (display label, icon) mapping
# Label is padded to 14 chars so columns line up.
# ─────────────────────────────────────────────────────────────────────────────
_EVENT_CONFIG: Dict[str, tuple] = {
    'message_processing_start': ('MESSAGE START', '▶'),
    'user_input_received':      ('INPUT',         ' '),
    'message_preprocessed':     ('PREPROCESS',    ' '),
    'llm_request':              ('LLM REQUEST',   '→'),
    'llm_response':             ('LLM RESPONSE',  '←'),
    'intent_classification':    ('CLASSIFIED',    '◆'),
    'parameter_extraction':     ('PARAMS',        ' '),
    'filter_validation':        ('VALIDATE',      ' '),
    'validation_summary':       ('VALIDATE SUM',  ' '),
    'api_call':                 ('API CALL',      '→'),
    'query_execution':          ('QUERY',         '←'),
    'combination_diagnostic':   ('DIAGNOSTIC',    ' '),
    'tool_execution_completed': ('TOOL DONE',     '✓'),
    'tool_execution_failed':    ('TOOL FAILED',   '✗'),
    'message_processing_complete': ('COMPLETE',   '■'),
    'error':                    ('ERROR',         '✗'),
    'websocket_connect':        ('CONNECTED',     '●'),
    'websocket_disconnect':     ('DISCONNECTED',  '○'),
}

_LINE_WIDTH   = 80
_SEPARATOR    = '─' * _LINE_WIDTH
_HEAVY_SEP    = '═' * _LINE_WIDTH
_LABEL_WIDTH  = 14   # width of the label field inside [...]
_TS_WIDTH     = 12   # "HH:MM:SS.mmm"
# indent for detail lines that wrap under the first line
_DETAIL_INDENT = ' ' * (_TS_WIDTH + 2 + _LABEL_WIDTH + 4 + 2)


# ─────────────────────────────────────────────────────────────────────────────
# Handler
# ─────────────────────────────────────────────────────────────────────────────

class ConversationFileHandler(logging.Handler):
    """
    Routes llm_workflow log records to per-conversation plain-text files.

    File path:  <settings.LOG_DIR>/conversations/<conversation_id>.log

    A new TURN header is written each time a previously-unseen
    correlation_id appears for a conversation, so every message in the
    chat gets its own clearly delimited section.
    """

    def __init__(self):
        super().__init__()
        self._log_dir: Optional[str] = None
        # {conversation_id: last_seen_correlation_id}
        self._last_correlation: Dict[str, Optional[str]] = {}
        # {conversation_id: turn_counter}
        self._turn_counter: Dict[str, int] = {}

    # ── path helpers ──────────────────────────────────────────────────────────

    def _conversations_dir(self) -> str:
        if self._log_dir is None:
            from django.conf import settings
            self._log_dir = os.path.join(settings.LOG_DIR, 'conversations')
            os.makedirs(self._log_dir, exist_ok=True)
        return self._log_dir

    def _file_path(self, conversation_id: str) -> str:
        safe = ''.join(c for c in conversation_id if c.isalnum() or c in '-_')
        return os.path.join(self._conversations_dir(), f"{safe}.log")

    # ── header writers ────────────────────────────────────────────────────────

    @staticmethod
    def _write_conversation_header(f, conversation_id: str) -> None:
        ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        f.write(_HEAVY_SEP + '\n')
        f.write(f'  CONVERSATION: {conversation_id}\n')
        f.write(f'  Started: {ts}\n')
        f.write(_HEAVY_SEP + '\n')

    @staticmethod
    def _write_turn_header(f, correlation_id: str, turn_num: int) -> None:
        ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        f.write('\n')
        f.write(_SEPARATOR + '\n')
        f.write(f'  TURN {turn_num}  ·  {ts}  ·  {correlation_id}\n')
        f.write(_SEPARATOR + '\n')

    # ── event formatter ───────────────────────────────────────────────────────

    def _format_record(self, record: logging.LogRecord,
                       event: str, data: dict) -> str:
        label, icon = _EVENT_CONFIG.get(event, (event.upper()[:_LABEL_WIDTH], ' '))
        ts = datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:_TS_WIDTH]

        # Error/warning marker appended to icon
        if record.levelno >= logging.ERROR:
            icon = '✗'
        elif record.levelno >= logging.WARNING and icon == ' ':
            icon = '!'

        first_line = f'  {ts}  [{label:<{_LABEL_WIDTH}}]  {icon}  '
        detail_lines = self._build_detail(event, data)

        if not detail_lines:
            return first_line.rstrip()

        lines = [first_line + detail_lines[0]]
        for dl in detail_lines[1:]:
            lines.append(_DETAIL_INDENT + dl)

        return '\n'.join(lines)

    @staticmethod
    def _build_detail(event: str, data: dict) -> list:
        """Return a list of plain-text strings describing the event."""
        lines = []

        if event == 'message_processing_start':
            lines.append(f"Type: {data.get('message_type', '?')}")

        elif event == 'user_input_received':
            preview = data.get('input_preview') or data.get('sanitized_input', '')
            modified = 'Yes' if data.get('was_modified') else 'No'
            length = data.get('sanitized_input_length',
                              data.get('raw_input_length', '?'))
            lines.append(f'Message: "{preview}"')
            lines.append(f'Modified by sanitizer: {modified}  |  Length: {length} chars')

        elif event == 'message_preprocessed':
            entities = data.get('entities_extracted', [])
            corrections = data.get('corrections_made', 0)
            confidence = data.get('confidence', 0)
            prev_ctx = 'Yes' if data.get('uses_previous_context') else 'No'
            lines.append(
                f'Entities found: {", ".join(entities) or "none"}  |  '
                f'Corrections: {corrections}  |  '
                f'Confidence: {confidence:.0%}  |  '
                f'Uses context: {prev_ctx}'
            )

        elif event == 'llm_request':
            lines.append(
                f"Model: {data.get('model', '?')}  |  "
                f"Messages in context: {data.get('message_count', '?')}  |  "
                f"Type: {data.get('request_type', 'chat_completion')}"
            )

        elif event == 'llm_response':
            duration = data.get('duration_ms', '?')
            usage = data.get('token_usage') or {}
            lines.append(f'Duration: {duration}ms')
            if usage:
                pt = usage.get('prompt_tokens', '?')
                ct = usage.get('completion_tokens', '?')
                tt = usage.get('total_tokens', '?')
                lines.append(f'Tokens: {tt} total  ({pt} prompt + {ct} completion)')

        elif event == 'intent_classification':
            category   = data.get('category', '?')
            confidence = data.get('confidence', 0)
            duration   = data.get('duration_ms', '')
            reasoning  = data.get('reasoning', '')
            dur_str    = f'  |  Duration: {duration}ms' if duration else ''
            lines.append(
                f'Category: {category}  |  '
                f'Confidence: {confidence * 100:.0f}%{dur_str}'
            )
            if reasoning:
                lines.append(f'Reasoning: {reasoning}')

        elif event == 'parameter_extraction':
            params = data.get('params') or {}
            lines.append(f"Source: {data.get('source', '?')}  |  Parameters found: {len(params)}")
            for k, v in params.items():
                if v is not None:
                    lines.append(f'  {k}: {v}')

        elif event == 'filter_validation':
            field    = data.get('field', '?')
            original = data.get('original_value', '?')
            corrected = data.get('corrected_value')
            is_valid = data.get('is_valid', True)
            confidence = data.get('confidence')
            status = '✓ valid' if is_valid else '✗ invalid'
            line = f'{field}: "{original}"  →  {status}'
            if corrected and corrected != original:
                line += f'  (auto-corrected to "{corrected}")'
            if confidence:
                line += f'  confidence: {confidence * 100:.0f}%'
            lines.append(line)
            suggestions = data.get('suggestions') or []
            if suggestions and not is_valid:
                lines.append(f'Suggestions: {", ".join(str(s) for s in suggestions[:3])}')

        elif event == 'validation_summary':
            lines.append(
                f"Validated: {data.get('total_validated', 0)}  |  "
                f"Auto-corrected: {data.get('auto_corrected', 0)}  |  "
                f"Needs review: {data.get('needs_confirmation', 0)}  |  "
                f"Rejected: {data.get('rejected', 0)}"
            )

        elif event == 'api_call':
            method   = data.get('method', 'GET')
            endpoint = data.get('endpoint', '?')
            status   = data.get('response_status', '?')
            duration = data.get('duration_ms', '?')
            lines.append(f'{method} {endpoint}  →  {status}  ({duration}ms)')
            if data.get('error'):
                lines.append(f'Error: {data["error"]}')

        elif event == 'query_execution':
            count    = data.get('record_count', '?')
            duration = data.get('duration_ms', '?')
            success  = data.get('success', True)
            status   = '✓ success' if success else '✗ failed'
            lines.append(f'{status}  |  Records: {count}  |  Duration: {duration}ms')
            if data.get('error'):
                lines.append(f'Error: {data["error"]}')

        elif event == 'combination_diagnostic':
            is_combo  = data.get('is_combination_issue', False)
            is_data   = data.get('is_data_issue', False)
            filters   = data.get('problematic_filters') or []
            total     = data.get('total_records_available', '?')
            issue     = 'combination mismatch' if is_combo else ('no data' if is_data else 'none')
            lines.append(f'Issue type: {issue}  |  Total records available: {total}')
            if filters:
                lines.append(f'Problematic filters: {", ".join(filters)}')

        elif event in ('tool_execution_completed', 'tool_execution_failed'):
            tool     = data.get('tool_name', '?')
            status   = data.get('status', '?')
            duration = data.get('duration_ms', '')
            dur_str  = f'  |  Duration: {duration}ms' if duration else ''
            lines.append(f'Tool: {tool}  |  Status: {status}{dur_str}')
            result = data.get('result_summary') or {}
            for k, v in result.items():
                if v is not None:
                    lines.append(f'  {k}: {v}')
            if data.get('error'):
                lines.append(f'Error: {data["error"]}')

        elif event == 'message_processing_complete':
            total    = data.get('total_duration_ms', '?')
            success  = data.get('success', True)
            category = data.get('category', '')
            status   = 'SUCCESS' if success else 'FAILED'
            cat_str  = f'  |  Category: {category}' if category else ''
            lines.append(f'{status}  |  Total time: {total}ms{cat_str}')

        elif event == 'error':
            stage = data.get('stage', '?')
            etype = data.get('error_type', '?')
            emsg  = data.get('error_message', '?')
            lines.append(f'Stage: {stage}  |  Type: {etype}')
            lines.append(f'Message: {emsg}')
            traceback = data.get('traceback', '')
            if traceback:
                tb_lines = [l for l in traceback.strip().splitlines() if l.strip()]
                lines.append('Traceback (last 3 lines):')
                for tb_line in tb_lines[-3:]:
                    lines.append(f'  {tb_line.strip()}')

        elif event in ('websocket_connect', 'websocket_disconnect'):
            user = data.get('user_id', '?')
            conv = data.get('conversation_id', '?')
            code = data.get('close_code', '')
            code_str = f'  |  Close code: {code}' if code else ''
            lines.append(f'User: {user}  |  Conversation: {conv}{code_str}')

        else:
            # Generic fallback: dump non-null fields
            for k, v in data.items():
                if v is not None:
                    lines.append(f'{k}: {v}')

        return lines

    # ── emit ──────────────────────────────────────────────────────────────────

    def emit(self, record: logging.LogRecord) -> None:
        try:
            conversation_id = getattr(record, 'conversation_id', None)
            correlation_id  = getattr(record, 'correlation_id', None)
            event           = getattr(record, 'event', 'unknown')
            data            = getattr(record, 'data', {}) or {}

            # Also try to pick up conversation_id from data dict
            # (e.g. websocket_connect logs it there)
            if not conversation_id:
                conversation_id = data.get('conversation_id')

            if not conversation_id:
                return  # Nothing to route without a conversation

            file_path  = self._file_path(conversation_id)
            is_new_file = not os.path.exists(file_path)

            last_corr  = self._last_correlation.get(conversation_id)
            is_new_turn = correlation_id and correlation_id != last_corr

            with open(file_path, 'a', encoding='utf-8') as f:
                if is_new_file:
                    self._write_conversation_header(f, conversation_id)

                if is_new_turn:
                    turn_num = self._turn_counter.get(conversation_id, 0) + 1
                    self._turn_counter[conversation_id] = turn_num
                    self._last_correlation[conversation_id] = correlation_id
                    self._write_turn_header(f, correlation_id, turn_num)

                line = self._format_record(record, event, data)
                f.write(line + '\n')

        except Exception:
            self.handleError(record)
