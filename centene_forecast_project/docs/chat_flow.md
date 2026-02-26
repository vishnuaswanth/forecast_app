# Chat System Flow Diagram

## Architecture Overview

```
Browser (WebSocket)
    │
    ▼
consumers.py  ──────────────────────────────────────────────────────────────
ChatConsumer.receive()
    │
    ├── type = "user_message"         → handle_user_message()
    ├── type = "confirm_cph_update"   → handle_confirm_cph_update()
    └── type = "new_conversation"     → handle_new_conversation()
```

---

## Scenario 1 — Standard User Message (most common path)

```
Browser sends:
  { type: "user_message", message: "Show March 2025 Amisys data", selected_row: null }

consumers.py → handle_user_message()
  │
  ├─ save_message('user', text)          → DB: ChatMessage (role=user)
  ├─ send_json({ type: 'typing', is_typing: True })
  │
  ▼
chat_service.py → process_message()
  │
  ├─ STEP 1: sanitizer.sanitize(user_text)
  │          → returns (sanitized_text, sanitization_metadata)
  │          → if empty after sanitize → return error response immediately
  │
  ├─ STEP 2: _get_message_history(conversation_id, limit=10)
  │          → DB: last 10 ChatMessages → list[{role, content}]
  │
  └─ STEP 3: llm_service.run_agent(sanitized_text, conversation_id, history, selected_row)
             │
             ├─ context_manager.get_context(conversation_id)
             │   → Redis / local cache / DB → ConversationContext
             │
             ├─ make_agent_tools(conversation_id, context, context_manager)
             │   → list of 6 StructuredTools (closures)
             │
             ├─ _build_system_prompt(context, selected_row)
             │   → instructions + context summary + selected_row block
             │
             ├─ llm.bind_tools(tools)
             │
             ├─ llm_with_tools.ainvoke(messages)   ← FIRST LLM CALL
             │   messages = [SystemMessage, ...history..., HumanMessage]
             │
             └─ (branch on response)
```

---

## Scenario 1a — LLM calls a tool

```
             response.tool_calls is not empty
             │
             ├─ For each tool_call:
             │   └─ _invoke_tool(tools, tool_call)
             │       └─ tool.ainvoke(args)    ← tool executes
             │
             ├─ messages.append(AIMessage with tool_calls)
             ├─ messages.append(ToolMessage(content=tool_result.message))
             │
             └─ llm.ainvoke(messages)         ← SECOND LLM CALL
                 → text_response (natural language summary)

  Returns: { text: str, ui_component: str, data: dict }

chat_service returns:
  { response_type: 'assistant_response', message: text, ui_component: ui, metadata: {...} }

consumers.py:
  ├─ send_json({ type: 'typing', is_typing: False })
  ├─ save_message('assistant', text)
  └─ send_json({
        type: 'assistant_response',
        message: text,
        ui_component: <HTML>,
        message_id: ...,
        metadata: {...}
     })
```

---

## Scenario 1b — LLM does NOT call a tool (clarification)

```
             response.tool_calls is empty
             │
             text_response = response.content   (plain text reply)
             ui_component  = ''                 (no UI card)

  Returns: { text: str, ui_component: '', data: {} }

consumers.py sends:
  { type: 'assistant_response', message: "Which month/year did you want?", ui_component: '' }
```

---

## Scenario 2 — Tool: get_forecast_data

```
User: "Show March 2025 Amisys domestic data"

LLM calls: get_forecast_data(month=3, year=2025, platforms=["Amisys"], localities=["Domestic"])

_get_forecast_data():
  ├─ fetch_forecast_data(params)  → FastAPI GET /api/llm/forecast/data
  │   ├─ Success → { records: [...], totals: {...}, months: {Month1: "Apr-25", ...} }
  │   ├─ APIClientError → error UI card (validation type, no admin contact)
  │   └─ APIError       → error UI card (api type, with admin contact)
  │
  ├─ context_manager.update_entities(...)
  │   stores: month, year, platforms, localities, states, case_types, report_config
  │
  └─ if show_totals_only:
  │     ui = generate_totals_table_html(totals, months)
  │     message = "Forecast totals for March 2025"
  └─ elif records:
  │     ui = generate_forecast_table_html(records, months, show_full=(len<=5), max_preview=5)
  │     message = "Found N records" | "Showing 5 of N records. Click View All..."
  └─ else (no records):
        ui = generate_error_ui("No records found...", validation, no admin)
        message = "No records found"

Returns: { message: str, ui_component: HTML table, data: full API response }

Browser receives:
  { type: 'assistant_response',
    message: "Here's the March 2025 Amisys domestic data...",
    ui_component: <forecast table HTML with pagination> }
```

---

## Scenario 3 — Tool: get_available_reports

```
User: "What reports are available?"

LLM calls: get_available_reports()

_get_available_reports():
  ├─ fetch_available_reports()  → FastAPI GET /api/llm/forecast/available-reports
  │   └─ Exception → error UI card (api type, with admin contact)
  │
  └─ generate_available_reports_ui(data)
      renders: table of report periods | status | record count | freshness

Returns: { message: "Found N reports (M current). Available: Jan 2025, Feb 2025...",
           ui_component: <reports card HTML>, data: {...} }

Browser receives:
  { type: 'assistant_response', message: str, ui_component: <reports table> }
```

---

## Scenario 4 — Tool: get_fte_details

```
User: "Show me the FTE breakdown for this row"
(selected_row was sent with the message OR is in context.selected_forecast_row)

LLM calls: get_fte_details(row_key=null)

_get_fte_details():
  ├─ context_manager.get_context(conversation_id)
  │   → fresh_ctx.selected_forecast_row
  │
  ├─ if no selected row:
  │     return error UI "Please select a row from the forecast table first."
  │
  └─ generate_fte_details_ui(row_data)
      renders: FTE Req / FTE Avail / Capacity / Gap per month
               + Domestic/Global badge + Target CPH

Returns: { message: "FTE details for Amisys Medicaid Domestic | CA | Claims Processing",
           ui_component: <fte-details-card HTML>, data: { row_key: str } }

Browser receives:
  { type: 'assistant_response', message: str, ui_component: <FTE details card> }
```

---

## Scenario 5 — Tool: preview_cph_change (two-phase confirm flow)

### Phase 1 — Preview

```
User: "Increase CPH to 14" (row selected)

LLM calls: preview_cph_change(new_cph=14, operation="set_to")

_preview_cph_change():
  ├─ context_manager.get_context() → get selected row
  ├─ resolve final_cph from operation:
  │     set_to          → final_cph = new_cph
  │     increase_by_pct → final_cph = current * (1 + pct/100)
  │     decrease_by_pct → final_cph = current * (1 - pct/100)
  │     add_to          → final_cph = current + new_cph
  │     subtract_from   → final_cph = current - new_cph
  │
  ├─ validate_cph_value(final_cph) → if invalid: error UI
  │
  ├─ calculate_cph_impact(row_data, final_cph, report_config)
  │   → impact_data: { "Apr-25": { old: {...}, new: {...}, config: {...} }, ... }
  │
  └─ generate_cph_preview_ui(row_data, final_cph, impact_data, locality)
      renders: CPH old→new, per-month FTE/Capacity/Gap old→new
               + "Confirm Change" button (data-update=JSON)
               + "Cancel" button

Returns: { message: "Preview: CPH 12 → 14 for Amisys...",
           ui_component: <cph-preview-card HTML with Confirm/Cancel buttons>,
           data: { old_cph, new_cph, impact } }

Browser receives:
  { type: 'assistant_response', ui_component: <preview card with buttons> }
  → User sees: preview card with Confirm Change / Cancel
```

### Phase 2 — Confirm (user clicks "Confirm Change")

```
Browser sends:
  { type: "confirm_cph_update",
    update_data: { main_lob, state, case_type, old_cph, new_cph, ... } }

consumers.py → handle_confirm_cph_update()
  │
  ├─ send_json({ type: 'typing', is_typing: True })
  │
  └─ chat_service.execute_cph_update(update_data, conversation_id, user)
      │
      ├─ (TODO: call backend API when ready)
      └─ currently: returns success card UI
                    "CPH changed from X to Y for LOB - State"

Browser receives:
  { type: 'cph_update_result',
    success: true,
    message: "CPH update recorded.",
    ui_component: <update-success-card HTML> }
```

---

## Scenario 6 — Tool: update_filters

```
User: "Also add Texas" (existing context has CA, Amisys)

LLM calls: update_filters(operation="extend", states=["TX"])

_update_filters():
  ├─ get fresh context
  ├─ operation = "extend":
  │     final_states = set(existing + new) = ["CA", "TX"]
  ├─ context_manager.update_entities(conversation_id, active_states=["CA","TX"])
  └─ generate_context_update_ui("Added: States: TX")

Returns: { message: "Added: States: TX",
           ui_component: <success card>, data: { operation, platforms, states, ... } }

operation variants:
  extend   → merges new into existing
  replace  → overwrites (only for mentioned fields)
  remove   → subtracts from existing
  reset    → context_manager.reset_filters(keep_month_year=True)
             → generates card with preserved period

Browser receives:
  { type: 'assistant_response', message: "Added Texas to state filters.", ui_component: <card> }
```

---

## Scenario 7 — Tool: clear_context

```
User: "Start over" / "Clear everything" / "Reset all"

LLM calls: clear_context()

_clear_context():
  └─ context_manager.clear_context(conversation_id)
     → wipes: filters, selected_row, cached data, report period
  └─ generate_clear_context_ui()  → green success card "Context Cleared"

Browser receives:
  { type: 'assistant_response', message: "All filters and previous selections reset...",
    ui_component: <context-cleared success card> }
```

---

## Scenario 8 — New Conversation

```
Browser sends:
  { type: "new_conversation", old_conversation_id: "uuid..." }

consumers.py → handle_new_conversation()
  ├─ mark_conversation_inactive(old_conversation_id)  → DB
  ├─ context_manager.clear_context(old_conversation_id)
  └─ create_new_conversation()  → new DB ChatConversation record

Browser receives:
  { type: 'system', message: 'New conversation started. Previous archived.',
    conversation_id: <new_uuid> }
```

---

## Error Scenarios

```
Stage                   What Happens                          Browser Receives
─────────────────────── ───────────────────────────────────── ──────────────────────────────
Empty message           send_error("Empty message")           { type: 'error', message: ... }
Invalid JSON            send_error("Invalid JSON format")     { type: 'error', message: ... }
Save user msg fails     send_error("Failed to save message")  { type: 'error', message: ... }
Empty after sanitize    returns error assistant_response      { type: 'assistant_response',
                                                                ui_component: <error card> }
LLMError                create_error_response()               { type: 'assistant_response',
                                                                ui_component: <error card> }
APIClientError          user-friendly message + UI card       { type: 'assistant_response',
                                                                ui_component: <info card> }
APIError                generic error + admin contact         { type: 'assistant_response',
                                                                ui_component: <error card> }
ValidationError         field message + UI card               { type: 'assistant_response',
                                                                ui_component: <info card> }
Tool execution fails    error UI from _invoke_tool()          { type: 'assistant_response',
                                                                ui_component: <error card> }
No row selected for     error message + validation card       { type: 'assistant_response',
  FTE/CPH tools                                               ui_component: <info card> }
CPH update fails        { type: 'cph_update_result',
                          success: false, message: str }
```

---

## WebSocket Message Types Reference

```
Direction   Type                   When
──────────  ─────────────────────  ──────────────────────────────────────────
→ Inbound   user_message           User sends a chat message
→ Inbound   confirm_cph_update     User clicks "Confirm Change" on CPH preview
→ Inbound   new_conversation       User starts a fresh conversation

← Outbound  system                 Connection established, new conversation
← Outbound  typing                 is_typing: true/false  (processing indicator)
← Outbound  assistant_response     LLM reply (always this type now; may include ui_component)
← Outbound  cph_update_result      Result of CPH confirm (success: bool, ui_component)
← Outbound  error                  Fatal consumer-level error
```

---

## Return Value Shape Reference

```
All tool responses:
  { message: str, ui_component: str (HTML), data: dict }

chat_service.process_message():
  { response_type: 'assistant_response',
    message: str,
    ui_component: str,
    metadata: { correlation_id, sanitization, data } }

chat_service.execute_cph_update():
  { success: bool, message: str, ui_component: str }

consumers → WebSocket (assistant_response):
  { type: 'assistant_response',
    message: str,
    ui_component: str,
    message_id: str,
    metadata: dict }

consumers → WebSocket (cph_update_result):
  { type: 'cph_update_result',
    success: bool,
    message: str,
    ui_component: str }
```
