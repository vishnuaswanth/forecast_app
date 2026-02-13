# Centene Workforce Forecasting - Problem Statement & Success Measures

## Executive Summary

This document outlines the business problem addressed by the Centene Workforce Forecasting application, defines measurable success criteria, and rates each solution component by business impact.

---

## Problem Statement

> **How can Centene's workforce planning team reduce capacity misalignment by accurately forecasting case handler requirements across 5+ platforms and multiple geographic markets, achieving ≤5% variance between forecasted and actual staffing needs within the next 6-month planning horizon?**

---

## SMART Framework

| Element | Application |
|---------|-------------|
| **Specific** | Addresses the exact gap between client case volume forecasts (CF) and available agent capacity (HC × CPH) across Amisys, Facets, QNXT, HealthRules, and Xcelys platforms |
| **Measurable** | Target ≤5% capacity gap percentage; tracked via KPIs: Client Forecast, Head Count, Capacity, and Gap % across all business units |
| **Actionable** | Enables managers to upload forecast/roster data, reallocate FTEs, adjust CPH targets, and run what-if scenarios to close gaps proactively |
| **Relevant** | Directly impacts operational costs (overstaffing = excess payroll) and service quality (understaffing = missed SLAs) for executives, workforce managers, and operations teams |
| **Time-bound** | 6-month rolling forecast visibility with monthly upload cycles and real-time execution monitoring |

---

## Core Problem

Manual workforce planning using spreadsheets leads to:
- Reactive staffing decisions
- Delayed gap identification
- Inconsistent capacity calculations across platforms
- Limited visibility for executives
- Time-consuming data consolidation

---

## Solutions Delivered

### Core Platform Capabilities

| # | Solution | Description |
|---|----------|-------------|
| 1 | **Centralized Visibility** | Single dashboard showing capacity gaps across all platforms, markets, and locations |
| 2 | **Proactive Gap Detection** | Identifies shortages/surpluses 6 months ahead |
| 3 | **Scenario Planning** | What-if analysis for FTE reallocation and CPH adjustments |
| 4 | **Automated Processing** | Batch upload of forecast and roster files replaces manual data entry |
| 5 | **Audit Trail** | Complete history of staffing decisions for compliance and analysis |

### AI-Powered Chat Assistant

| # | Solution | Description |
|---|----------|-------------|
| 6 | **Natural Language Queries** | Query forecast/roster data using conversational language instead of complex UI navigation |
| 7 | **Intelligent Filter Validation** | Proactive typo detection with fuzzy matching, auto-correction, and smart suggestions |
| 8 | **Context-Aware Conversations** | Multi-turn memory retains filters and preferences across queries |
| 9 | **Smart Error Diagnosis** | Identifies which filter breaks a query and provides actionable fix suggestions |
| 10 | **Input Sanitization** | Enterprise-grade security removing XSS/injection threats from user input |

---

## Success Measures & Solution Ratings

### Summary Matrix

| Solution | Success Measure | Target KPI | Current State (Assumed) | Impact Rating |
|----------|-----------------|------------|------------------------|---------------|
| **Centralized Visibility** | Time to access capacity data across all platforms | < 30 seconds | 2-4 hours (manual consolidation) | ⭐⭐⭐⭐⭐ **Critical** |
| **Proactive Gap Detection** | Lead time for identifying staffing gaps | 6 months ahead | 2-4 weeks (reactive) | ⭐⭐⭐⭐⭐ **Critical** |
| **Scenario Planning** | Decision turnaround for reallocation requests | < 1 hour | 2-3 days (manual recalculation) | ⭐⭐⭐⭐ **High** |
| **Automated Processing** | Data processing time per upload cycle | < 5 minutes | 4-8 hours (manual entry) | ⭐⭐⭐⭐ **High** |
| **Audit Trail** | Compliance readiness for staffing decisions | 100% traceability | Partial/inconsistent records | ⭐⭐⭐ **Medium** |

---

## Detailed Success Framework

### 1. Centralized Visibility ⭐⭐⭐⭐⭐ Critical

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Dashboard load time | N/A | < 3 sec | System monitoring |
| Data freshness | Weekly updates | Real-time (15 min cache) | Cache TTL config |
| Platform coverage | Siloed views | 5 platforms unified | Feature checklist |
| User adoption rate | 0% | > 90% of managers | Login analytics |

**Business Value:** Eliminates information silos; enables executive-level decisions without waiting for manual reports.

---

### 2. Proactive Gap Detection ⭐⭐⭐⭐⭐ Critical

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Forecast accuracy | ±15-20% variance | ≤ 5% variance | Gap % tracking |
| Early warning lead time | 2-4 weeks | 6 months | Forecast horizon |
| Missed SLA incidents due to understaffing | Untracked | Reduce by 50% | Incident reports |
| Overstaffing cost | Unquantified | Reduce by 10-15% | Payroll analysis |

**Business Value:** Shifts from reactive firefighting to strategic workforce planning.

---

### 3. Scenario Planning (What-If Analysis) ⭐⭐⭐⭐ High

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Reallocation decision time | 2-3 days | < 1 hour | Time tracking |
| Scenarios evaluated per decision | 1-2 | 5+ | Edit view usage |
| CPH adjustment accuracy | Manual calculation errors | Automated, error-free | Validation logs |
| Preview before commit | Not available | 100% changes previewed | Feature usage |

**Business Value:** Empowers managers to test staffing strategies before committing resources.

---

### 4. Automated Processing ⭐⭐⭐⭐ High

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| File processing time | 4-8 hours manual | < 5 minutes | Execution monitoring |
| Data entry errors | 5-10% | < 0.1% | Validation failures |
| Upload success rate | N/A | > 95% | Execution status |
| Monthly cycle time | 1-2 weeks | 1-2 days | End-to-end tracking |

**Business Value:** Frees workforce planners from data entry to focus on strategic analysis.

---

### 5. Audit Trail ⭐⭐⭐ Medium

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Change traceability | Partial | 100% | Audit log coverage |
| Audit preparation time | Days | Minutes | Export functionality |
| Compliance findings | Unknown | Zero gaps | Audit results |
| Historical data retention | Inconsistent | 12+ months | Database retention |

**Business Value:** Reduces compliance risk and enables root cause analysis for staffing decisions.

---

## AI-Powered Chat Assistant (chat_app)

The **chat_app** is an AI-powered natural language interface that transforms how users interact with the forecasting system. Instead of navigating complex filter UIs, users can query data conversationally.

### Overview

| Aspect | Description |
|--------|-------------|
| **Technology** | LangChain + OpenAI LLM for intent classification |
| **Interface** | Real-time WebSocket communication |
| **Integration** | Seamless connection to FastAPI backend via repository pattern |
| **Persistence** | Conversation history and context stored in database |

### Chat App Features & Ratings

| # | Feature | Description | Impact Rating |
|---|---------|-------------|---------------|
| 6 | **Natural Language Queries** | Query forecast/roster data using conversational language | ⭐⭐⭐⭐⭐ **Critical** |
| 7 | **Intelligent Filter Validation** | Proactive typo detection with fuzzy matching and auto-correction | ⭐⭐⭐⭐⭐ **Critical** |
| 8 | **Context-Aware Conversations** | Multi-turn memory retains filters across queries | ⭐⭐⭐⭐ **High** |
| 9 | **Smart Error Diagnosis** | Identifies which filter breaks a query and suggests fixes | ⭐⭐⭐⭐ **High** |
| 10 | **Input Sanitization** | Security-first approach removing XSS/injection threats | ⭐⭐⭐ **Medium** |

---

### 6. Natural Language Queries ⭐⭐⭐⭐⭐ Critical

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Query success rate | N/A | > 95% | Intent classification accuracy |
| Time to get data | 5-10 clicks (UI navigation) | Single sentence | User interaction logs |
| User training required | Hours (learn UI) | Minutes (natural language) | Onboarding time |
| Query complexity supported | Simple filters only | Multi-filter combinations | Feature coverage |

**Business Value:** Democratizes data access; any user can query complex forecast data without training on filter UIs.

**Example Queries:**
- "Show Amisys forecast for March 2025"
- "Get Medicaid data for California and Texas"
- "What are the totals for Domestic claims?"

**Supported Intents (11+ categories):**
| Intent | Description |
|--------|-------------|
| `get_forecast_data` | Query forecast data with filters |
| `get_roster_data` | View team/staff information |
| `list_available_reports` | Discover available data |
| `reallocate_forecast_data` | Move resources between units |
| `allocate_ramp_ftes` | Allocate training employees |
| `modify_cph` | Adjust target CPH values |
| `clear_context` | Reset conversation state |
| `update_context` | Selective filter reset |

---

### 7. Intelligent Filter Validation ⭐⭐⭐⭐⭐ Critical

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Typo auto-correction rate | 0% | > 90% (high confidence) | Fuzzy match logs |
| Invalid query prevention | Post-API failure | Pre-API validation | Validation intercepts |
| User correction prompts | Never | 60-90% confidence range | Confirmation dialogs |
| False positive rate | N/A | < 5% | User feedback |

**Business Value:** Prevents frustrating "no data found" errors by catching and correcting issues before API calls.

**Confidence-Based Correction:**
| Confidence Level | Action |
|-----------------|--------|
| **> 90%** | Auto-correct silently |
| **60-90%** | Ask user confirmation |
| **< 60%** | Reject and show suggestions |

**Spell Correction Examples:**
| User Input | Corrected To |
|------------|--------------|
| "Amysis" | "Amisys" |
| "Medicad" | "Medicaid" |
| "Calfornia" | "California" → "CA" |

---

### 8. Context-Aware Conversations ⭐⭐⭐⭐ High

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Filter re-entry required | Every query | Only when changing | Context persistence |
| Follow-up query success | N/A | > 90% | Multi-turn completion |
| Context retention | None | Full session persistence | Database storage |
| Context reference accuracy | N/A | > 95% | Reference resolution |

**Business Value:** Eliminates repetitive filter selection; users can drill down or pivot without re-specifying all criteria.

**Context Memory Includes:**
- Selected report type (forecast/roster)
- Time period (month/year)
- Active filters (platforms, markets, states, case types)
- User preferences (e.g., "show totals only")
- Selected row for detailed queries

**Follow-up Query Examples:**
| Query | Behavior |
|-------|----------|
| "Now show Texas" | Keeps month/year, adds TX state filter |
| "Same but for Facets" | Keeps all filters, swaps platform |
| "Show all data" | Resets filters but keeps period |
| "What about Medicare?" | Keeps location, changes market |

---

### 9. Smart Error Diagnosis ⭐⭐⭐⭐ High

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Root cause identification | Manual investigation | Automatic diagnosis | Diagnosis accuracy |
| Suggested alternatives | None | Valid options shown | Suggestion relevance |
| User resolution time | 10+ minutes | < 1 minute | Time to successful query |
| Zero-result queries explained | 0% | 100% | Diagnosis coverage |

**Business Value:** When queries return no data, the system explains exactly why and how to fix it.

**Combination Diagnosis Process:**
1. Query returns 0 records
2. System identifies which filter breaks the combination
3. Shows available options for each filter level
4. LLM generates natural language guidance

**Diagnosis Output Example:**
```
No data found for: Amisys + Medicare + California

Diagnosis:
✗ California has no Medicare data for Amisys
✓ Available states for Amisys Medicare: TX, FL, GA
✓ California has data for: Medicaid, Marketplace
```

---

### 10. Input Sanitization ⭐⭐⭐ Medium

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Security threat detection | None | 100% coverage | Sanitization logs |
| XSS/injection prevention | N/A | All vectors blocked | Security audit |
| False positive rate | N/A | < 1% | User complaints |
| Processing overhead | N/A | < 10ms | Performance monitoring |

**Business Value:** Enterprise-grade security protecting against malicious input without impacting user experience.

**Threats Detected & Neutralized:**
- Cross-site scripting (XSS) attempts
- SQL injection patterns
- Command injection attempts
- Malformed input handling

---

## Chat App Architecture

### Data Flow

```
User Query (Natural Language)
    ↓
WebSocket Connection (Real-time)
    ↓
Input Sanitization (Security)
    ↓
Message Preprocessing
    ├── Text Normalization
    ├── Spell Correction
    └── Entity Extraction (XML tags)
    ↓
Context Manager (Retrieve/Update State)
    ↓
LLM Service (Intent Classification + Parameter Extraction)
    ↓
Validation Tools (Filter Validation + Diagnosis)
    ↓
Forecast/Roster Tools (FastAPI Backend Calls)
    ↓
UI Tools (HTML Response Generation)
    ↓
WebSocket Response (Real-time)
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| WebSocket Consumer | `consumers.py` | Real-time message handling |
| LLM Service | `llm_service.py` | Intent classification via OpenAI |
| Chat Service | `chat_service.py` | Orchestration layer |
| Context Manager | `context_manager.py` | Conversation state persistence |
| Forecast Tools | `forecast_tools.py` | Data retrieval from backend |
| Validation Tools | `validation_tools.py` | Filter validation & diagnosis |
| Message Preprocessor | `message_preprocessor.py` | Text normalization & entity extraction |

---

## Chat App Success Measures Summary

| Feature | Success Measure | Target KPI | Current State | Impact Rating |
|---------|-----------------|------------|---------------|---------------|
| **Natural Language Queries** | Query success rate | > 95% accuracy | N/A (new capability) | ⭐⭐⭐⭐⭐ **Critical** |
| **Intelligent Filter Validation** | Typo auto-correction | > 90% high-confidence fixes | 0% (manual re-entry) | ⭐⭐⭐⭐⭐ **Critical** |
| **Context-Aware Conversations** | Filter re-entry eliminated | > 90% follow-up success | 100% re-entry required | ⭐⭐⭐⭐ **High** |
| **Smart Error Diagnosis** | Root cause identification | 100% zero-result explained | Manual investigation | ⭐⭐⭐⭐ **High** |
| **Input Sanitization** | Threat detection coverage | 100% vectors blocked | None | ⭐⭐⭐ **Medium** |

---

## Impact Summary

### Core Platform Solutions

| Rating | Solutions | Business Impact |
|--------|-----------|-----------------|
| ⭐⭐⭐⭐⭐ **Critical** | Centralized Visibility, Proactive Gap Detection | Directly prevents SLA breaches and optimizes $M in staffing costs |
| ⭐⭐⭐⭐ **High** | Scenario Planning, Automated Processing | Reduces operational overhead by 80%+ and accelerates decisions |
| ⭐⭐⭐ **Medium** | Audit Trail | Risk mitigation and compliance enablement |

### AI Chat Assistant Solutions

| Rating | Solutions | Business Impact |
|--------|-----------|-----------------|
| ⭐⭐⭐⭐⭐ **Critical** | Natural Language Queries, Intelligent Filter Validation | Democratizes data access; eliminates query failures from user errors |
| ⭐⭐⭐⭐ **High** | Context-Aware Conversations, Smart Error Diagnosis | Reduces time-to-insight by 90%; eliminates frustrating dead-ends |
| ⭐⭐⭐ **Medium** | Input Sanitization | Enterprise security without UX compromise |

### Combined Impact Matrix

| Category | Core Platform | AI Chat Assistant | Combined |
|----------|---------------|-------------------|----------|
| **Data Access** | Dashboard-based | Conversational | Multi-modal access |
| **User Training** | Hours | Minutes | Reduced onboarding |
| **Error Handling** | Reactive | Proactive | Prevention-first |
| **Query Complexity** | UI-limited | Natural language | Unlimited flexibility |

---

## ROI Indicators

### Core Platform ROI

| Category | Estimated Impact |
|----------|------------------|
| **Labor Cost Optimization** | 10-15% reduction in overstaffing waste |
| **SLA Compliance** | 50% fewer understaffing incidents |
| **Operational Efficiency** | 80% reduction in data processing time |
| **Decision Speed** | 90% faster reallocation decisions |
| **Risk Reduction** | 100% audit traceability |

### AI Chat Assistant ROI

| Category | Estimated Impact |
|----------|------------------|
| **User Productivity** | 70% reduction in time-to-data (clicks → conversation) |
| **Error Prevention** | 90% reduction in "no data found" frustration |
| **Training Costs** | 60% reduction in onboarding time |
| **Query Success Rate** | 95%+ first-attempt success (vs. trial-and-error) |
| **User Adoption** | Higher engagement through intuitive interface |
| **Security Posture** | 100% input threat neutralization |

---

## Key Performance Indicators (KPIs)

The application tracks the following core metrics:

| KPI | Abbreviation | Definition |
|-----|--------------|------------|
| **Client Forecast** | CF | Volume of cases expected to be received (provided by client) |
| **Head Count** | HC | Number of Full-Time Equivalent (FTE) employees available |
| **Cases Per Hour** | CPH | Productivity rate (cases an agent can handle per hour) |
| **Capacity** | Cap | Total cases that can be handled = HC × CPH × Hours Available |
| **Capacity Gap** | Gap | CF minus Capacity (negative = shortage, positive = surplus) |
| **Gap Percentage** | Gap % | Absolute gap ÷ CF × 100 (severity indicator) |

---

## Target Users

| Role | Permissions | Primary Use Cases |
|------|-------------|-------------------|
| **Admin** | Full system access | System maintenance, configuration, user management |
| **Manager** | View dashboards, edit allocations, upload files | Executive reporting, capacity planning, what-if analysis |
| **Viewer** | Read-only dashboard access | Stakeholder reporting, capacity status visibility |

---


## Appendix: Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend Framework** | Django + FastAPI |
| **Frontend** | jQuery, DataTables, Select2 |
| **AI/ML** | LangChain + OpenAI |
| **Real-time** | Django Channels (WebSocket) |
| **Authentication** | LDAP (NTT Data) |
| **Background Jobs** | Django-Q |
| **Caching** | Multi-tier (locmem, filebased, Redis) |

---

*Document Version: 1.1*
*Last Updated: February 2026*
*Includes: Core Platform + AI Chat Assistant*
