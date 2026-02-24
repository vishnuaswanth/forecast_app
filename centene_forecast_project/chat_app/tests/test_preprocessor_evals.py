"""
Preprocessor Evaluation — Error Analysis

Run with:  python test_preprocessor_evals.py
       or: pytest test_preprocessor_evals.py -v -s

Each eval case declares explicit checks.  After running all cases the
script prints a full error-analysis report:

  • pass / fail count per category
  • for every failure: what was expected, what was actually returned
  • a quick summary table so failures are easy to prioritise
"""
import asyncio
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# ── Django bootstrap ──────────────────────────────────────────────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'centene_forecast_project.settings')
import django
django.setup()
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from chat_app.services.message_preprocessor import MessagePreprocessor
from chat_app.services.tools.validation import ConversationContext


# ===========================================================================
# Helpers
# ===========================================================================

def _run(text: str, context=None):
    p = MessagePreprocessor(llm=None)
    return asyncio.get_event_loop().run_until_complete(p.preprocess(text, context=context))


def _ctx(**kwargs) -> ConversationContext:
    return ConversationContext(
        conversation_id='eval-test',
        forecast_report_month=kwargs.pop('month', None),
        forecast_report_year=kwargs.pop('year', None),
        active_platforms=kwargs.pop('platforms', []),
        active_localities=kwargs.pop('localities', []),
        active_states=kwargs.pop('states', []),
        active_case_types=kwargs.pop('case_types', []),
        active_main_lobs=kwargs.pop('main_lobs', None),
    )


# ===========================================================================
# Check execution engine
# ===========================================================================

@dataclass
class CheckResult:
    check_desc: str
    passed: bool
    expected: Any
    actual: Any
    note: str = ''


def _resolve_field(result, field: str) -> Any:
    """Pull a value from the PreprocessedMessage for a given field key."""
    e = result.extracted_entities
    i = result.implicit_info
    field_map = {
        'intent':               result.intent,
        'confidence':           result.parsing_confidence,
        'resolved':             result.resolved_message,
        'corrections.count':    len(result.corrections_made),
        'corrections.originals': [c['original'] for c in result.corrections_made],
        'corrections.corrected': [c['corrected'] for c in result.corrections_made],
        'month':                e.get('month'),
        'year':                 e.get('year'),
        'platforms':            e.get('platforms', []),
        'localities':           e.get('localities', []),
        'states':               e.get('states', []),
        'case_types':           e.get('case_types', []),
        'main_lobs':            e.get('main_lobs', []),
        'forecast_months':      e.get('active_forecast_months', []),
        'show_totals_only':     e.get('show_totals_only'),
        'markets_key':          'markets' in e,           # True if markets were extracted (should be False)
        'implicit.uses_context': i.get('uses_previous_context', False),
        'implicit.operation':   i.get('operation'),
        'implicit.reset_filter': i.get('reset_filter', False),

        # ── Modification entities (CPH / numeric changes) ──────────────
        # Not yet extracted — checks fail until feature is implemented.
        'modification.field':     e.get('modification_field'),
        'modification.operation': e.get('modification_operation'),
        'modification.value':     e.get('modification_value'),
        'modification.unit':      e.get('modification_unit'),

        # ── Output format entities (chart / data / totals) ─────────────
        # Not yet extracted — checks fail until feature is implemented.
        # requested_outputs: list containing any of 'data', 'chart', 'totals'
        # chart_type: 'bar' | 'line' | 'pie' | 'area' | None (unspecified)
        'output.requested':       e.get('requested_outputs', []),
        'output.chart_type':      e.get('chart_type'),
    }
    return field_map.get(field, f'<unknown field: {field}>')


def _run_check(result, check: Tuple[str, str, Any]) -> CheckResult:
    """
    Execute one check.  Format: (field, operator, expected)

    Operators:
      ==          exact equality
      !=          not equal
      in          expected value is IN the actual list/string
      not_in      expected value is NOT in the actual list/string
      contains    actual string contains expected substring
      not_contains actual string does NOT contain expected substring
      >=          actual >= expected  (numbers)
      <=          actual <= expected  (numbers)
      is_true     actual is truthy
      is_false    actual is falsy
      is_empty    actual is empty / falsy
      is_not_empty actual is non-empty / truthy
    """
    field, op, expected = check
    actual = _resolve_field(result, field)

    check_desc = f"{field} {op} {expected!r}"

    if op == '==':
        passed = actual == expected
    elif op == '!=':
        passed = actual != expected
    elif op == 'in':
        passed = expected in (actual or [])
    elif op == 'not_in':
        passed = expected not in (actual or [])
    elif op == 'contains':
        passed = expected in str(actual or '')
    elif op == 'not_contains':
        passed = expected not in str(actual or '')
    elif op == '>=':
        passed = (actual or 0) >= expected
    elif op == '<=':
        passed = (actual or 0) <= expected
    elif op == 'is_true':
        passed = bool(actual)
        expected = True
    elif op == 'is_false':
        passed = not bool(actual)
        expected = False
    elif op == 'is_empty':
        passed = not actual
        expected = '(empty)'
    elif op == 'is_not_empty':
        passed = bool(actual)
        expected = '(non-empty)'
    else:
        passed = False
        check_desc += f'  [unknown operator: {op}]'

    return CheckResult(check_desc=check_desc, passed=passed, expected=expected, actual=actual)


# ===========================================================================
# Eval case data
# ===========================================================================

@dataclass
class EvalCase:
    id: str
    category: str
    input: str
    checks: List[Tuple[str, str, Any]]
    context: Optional[ConversationContext] = None


EVAL_CASES: List[EvalCase] = [

    # -----------------------------------------------------------------------
    # MONTH EXTRACTION
    # -----------------------------------------------------------------------
    EvalCase('month-01', 'Month Extraction',
             'Show data for January 2025',
             [('month', '==', ['1']), ('intent', '==', 'query_data')]),

    EvalCase('month-02', 'Month Extraction',
             'February forecast please',
             [('month', '==', ['2'])]),

    EvalCase('month-03', 'Month Extraction',
             'Show may 2025 forecast',
             [('month', '==', ['5'])],
             ),  # 'may' is also a modal verb — tricky

    EvalCase('month-04', 'Month Extraction',
             'Show jan 2025',
             [('month', '==', ['1'])]),

    EvalCase('month-05', 'Month Extraction',
             'Show sept 2025 report',
             [('month', '==', ['9'])]),

    EvalCase('month-06', 'Month Extraction',
             'Show Amisys data',
             [('month', 'is_empty', None)]),   # no month present

    # -----------------------------------------------------------------------
    # YEAR EXTRACTION
    # -----------------------------------------------------------------------
    EvalCase('year-01', 'Year Extraction',
             'January 2025 report',
             [('year', '==', ['2025'])]),

    EvalCase('year-02', 'Year Extraction',
             'Forecast 2026',
             [('year', '==', ['2026'])]),

    EvalCase('year-03', 'Year Extraction',
             'Data from 1999 report',
             [('year', 'is_empty', None)]),    # 1999 outside valid range

    EvalCase('year-04', 'Year Extraction',
             'Record ID 1234 for claims',
             [('year', 'is_empty', None)]),    # 4-digit non-year number

    # -----------------------------------------------------------------------
    # PLATFORM EXTRACTION + SPELL CORRECTION
    # -----------------------------------------------------------------------
    EvalCase('platform-01', 'Platform Extraction',
             'Show Amisys data',
             [('platforms', 'in', 'Amisys')]),

    EvalCase('platform-02', 'Platform Extraction',
             'Facets forecast March 2025',
             [('platforms', 'in', 'Facets')]),

    EvalCase('platform-03', 'Platform Extraction',
             'Xcelys March 2025',
             [('platforms', 'in', 'Xcelys')]),

    EvalCase('platform-04', 'Platform Spell-Correct',
             'amysis data march 2025',
             [('platforms', 'in', 'Amisys'),
              ('corrections.corrected', 'in', 'Amisys')]),

    EvalCase('platform-05', 'Platform Spell-Correct',
             'xcylys march 2025',
             [('platforms', 'in', 'Xcelys'),
              ('corrections.corrected', 'in', 'Xcelys')]),

    EvalCase('platform-06', 'Platform Spell-Correct',
             'fecets forecast',
             [('platforms', 'in', 'Facets')]),

    EvalCase('platform-07', 'Platform Extraction',
             'Compare Amisys Facets and Xcelys for 2025',
             [('platforms', 'in', 'Amisys'),
              ('platforms', 'in', 'Facets'),
              ('platforms', 'in', 'Xcelys')]),

    EvalCase('platform-08', 'Platform Spell-Correct',
             'Amisys Medicaid Domestic march 2025',
             [('corrections.count', '==', 0)]),  # correct spelling = no corrections

    # -----------------------------------------------------------------------
    # MARKETS NOT EXTRACTED (key design constraint)
    # -----------------------------------------------------------------------
    EvalCase('market-01', 'Markets Absent',
             'Show Medicaid data for March 2025',
             [('markets_key', '==', False)]),   # 'markets' key must NOT appear

    EvalCase('market-02', 'Markets Absent',
             'Medicare forecast for CA',
             [('markets_key', '==', False)]),

    EvalCase('market-03', 'Markets Absent',
             'Marketplace Amisys 2025',
             [('markets_key', '==', False)]),

    EvalCase('market-04', 'Markets Absent — main_lob OK',
             'Show Amisys Medicaid Domestic data for March 2025',
             [('markets_key', '==', False),
              ('main_lobs', 'is_not_empty', None)]),  # whole LOB captured

    # -----------------------------------------------------------------------
    # LOCALITY EXTRACTION + ALIASES
    # -----------------------------------------------------------------------
    EvalCase('locality-01', 'Locality Extraction',
             'Domestic workforce',
             [('localities', 'in', 'Domestic')]),

    EvalCase('locality-02', 'Locality Extraction',
             'Global team data',
             [('localities', 'in', 'Global')]),

    EvalCase('locality-03', 'Locality Alias',
             'offshore data',
             [('localities', 'in', 'Global'),
              ('corrections.corrected', 'in', 'Global')]),

    EvalCase('locality-04', 'Locality Alias',
             'onshore staffing',
             [('localities', 'in', 'Domestic')]),

    EvalCase('locality-05', 'Locality Alias',
             'dom team march 2025',
             [('localities', 'in', 'Domestic')]),

    EvalCase('locality-06', 'Locality Alias',
             'gbl workforce march 2025',
             [('localities', 'in', 'Global')]),

    # -----------------------------------------------------------------------
    # STATE EXTRACTION
    # -----------------------------------------------------------------------
    EvalCase('state-01', 'State Full Name',
             'California data march 2025',
             [('states', 'in', 'CA')]),

    EvalCase('state-02', 'State Full Name',
             'Texas forecast march 2025',
             [('states', 'in', 'TX')]),

    EvalCase('state-03', 'State Code',
             'Show CA, TX, and FL claims for March 2025',
             [('states', 'in', 'CA'),
              ('states', 'in', 'TX'),
              ('states', 'in', 'FL')]),

    EvalCase('state-04', 'Ambiguous — OR as conjunction (should NOT match)',
             'Show amisys or facets data',
             [('states', 'not_in', 'OR')]),

    EvalCase('state-05', 'Ambiguous — OR with state context (should match)',
             'Show data for CA and OR',
             [('states', 'in', 'OR')]),

    EvalCase('state-06', 'Ambiguous — IN as preposition (should NOT match)',
             'Data for March in California',
             [('states', 'not_in', 'IN')]),

    EvalCase('state-07', 'Ambiguous — IN with state keyword (should match)',
             'Show data for state IN',
             [('states', 'in', 'IN')]),

    EvalCase('state-08', 'Ambiguous — ME in "show me" (should NOT match)',
             'Show me the Amisys data',
             [('states', 'not_in', 'ME')]),

    EvalCase('state-09', 'Ambiguous — ME in state list (should match)',
             'Show data for CA and ME',
             [('states', 'in', 'ME')]),

    EvalCase('state-10', 'Ambiguous — OK as filler (should NOT match)',
             'OK show me the data for March 2025',
             [('states', 'not_in', 'OK')]),

    # -----------------------------------------------------------------------
    # CASE TYPE EXTRACTION + ALIASES
    # -----------------------------------------------------------------------
    EvalCase('casetype-01', 'Case Type Extraction',
             'Claims Processing data',
             [('case_types', 'in', 'Claims Processing')]),

    EvalCase('casetype-02', 'Case Type Extraction',
             'Enrollment forecast march 2025',
             [('case_types', 'in', 'Enrollment')]),

    EvalCase('casetype-03', 'Case Type Extraction',
             'Appeals for California',
             [('case_types', 'in', 'Appeals')]),

    EvalCase('casetype-04', 'Case Type Extraction',
             'Adjustments data',
             [('case_types', 'in', 'Adjustments')]),

    EvalCase('casetype-05', 'Case Type Alias',
             'Show claims for CA march 2025',
             [('case_types', 'in', 'Claims Processing')]),

    EvalCase('casetype-06', 'Case Type Alias',
             'claims proc data',
             [('case_types', 'in', 'Claims Processing')]),

    EvalCase('casetype-07', 'Case Type Alias',
             'enroll numbers 2025',
             [('case_types', 'in', 'Enrollment')]),

    EvalCase('casetype-08', 'Case Type Alias',
             'appeal data CA',
             [('case_types', 'in', 'Appeals')]),

    EvalCase('casetype-09', 'Case Type — All Four',
             'Show claims processing enrollment appeals adjustments for march 2025',
             [('case_types', 'in', 'Claims Processing'),
              ('case_types', 'in', 'Enrollment'),
              ('case_types', 'in', 'Appeals'),
              ('case_types', 'in', 'Adjustments')]),

    # -----------------------------------------------------------------------
    # INTENT DETECTION
    # -----------------------------------------------------------------------
    EvalCase('intent-01', 'Intent Detection',
             'Show forecast for March 2025',
             [('intent', '==', 'query_data')]),

    EvalCase('intent-02', 'Intent Detection',
             'Get Amisys data for CA',
             [('intent', '==', 'query_data')]),

    EvalCase('intent-03', 'Intent Detection',
             'Also show Facets',
             [('intent', '==', 'extend_filters')]),

    EvalCase('intent-04', 'Intent Detection',
             'Add Texas too',
             [('intent', '==', 'extend_filters')]),

    EvalCase('intent-05', 'Intent Detection',
             'Remove California filter',
             [('intent', '==', 'remove_filters')]),

    EvalCase('intent-06', 'Intent Detection',
             'Show data without Facets',
             [('intent', '==', 'remove_filters')]),

    EvalCase('intent-07', 'Intent Detection',
             'Change to Amisys',
             [('intent', '==', 'replace_filters')]),

    EvalCase('intent-08', 'Intent Detection',
             'Reset all filters',
             [('intent', '==', 'reset_filters')]),

    EvalCase('intent-09', 'Intent Detection',
             'Clear all and show everything',
             [('intent', '==', 'reset_filters')]),

    EvalCase('intent-10', 'Intent Detection',
             'Same as before',
             [('intent', '==', 'use_context')]),

    EvalCase('intent-11', 'Intent Detection',
             'Same filters for 2025',
             [('intent', '==', 'use_context')]),

    EvalCase('intent-12', 'Intent Detection — tricky',
             'Same as before but remove Texas',
             # "remove" should win (higher priority than use_context)
             [('intent', '==', 'remove_filters'),
              ('implicit.uses_context', 'is_true', None)]),

    EvalCase('intent-13', 'Intent Detection — tricky',
             'Also show the same platforms',
             # "also" → extend_filters; "same" → use_context; extend wins
             [('intent', '==', 'extend_filters'),
              ('implicit.uses_context', 'is_true', None)]),

    EvalCase('intent-14', 'Intent Detection — tricky: "show" + "also"',
             'Also show Facets data for march 2025',
             [('intent', '==', 'extend_filters')]),

    # -----------------------------------------------------------------------
    # RESOLVED MESSAGE — no context
    # -----------------------------------------------------------------------
    EvalCase('resolved-01', 'Resolved Message',
             'Show forecast for March 2025',
             [('resolved', 'contains', 'March'),
              ('resolved', 'contains', '2025'),
              ('resolved', 'is_not_empty', None)]),

    EvalCase('resolved-02', 'Resolved Message',
             'Show Amisys data for March 2025',
             [('resolved', 'contains', 'Amisys'),
              ('resolved', 'contains', 'March')]),

    EvalCase('resolved-03', 'Resolved Message',
             'Show CA claims for March 2025',
             [('resolved', 'contains', 'CA'),
              ('resolved', 'contains', 'Claims Processing')]),

    EvalCase('resolved-04', 'Resolved Message — totals preference',
             'Show totals only for Amisys march 2025',
             [('resolved', 'contains', 'Totals Only')]),

    EvalCase('resolved-05', 'Resolved Message — full data preference',
             'Full data for Amisys Domestic march 2025',
             [('resolved', 'contains', 'All Records')]),

    # -----------------------------------------------------------------------
    # RESOLVED MESSAGE — with stored context
    # -----------------------------------------------------------------------
    EvalCase('resolved-ctx-01', 'Resolved + Context: carry month/year',
             'Show Amisys data',
             [('resolved', 'contains', 'March'),
              ('resolved', 'contains', '2025'),
              ('resolved', 'contains', 'Amisys')],
             context=_ctx(month=3, year=2025)),

    EvalCase('resolved-ctx-02', 'Resolved + Context: carry platform',
             'Show claims data for April 2025',
             [('resolved', 'contains', 'Facets'),
              ('resolved', 'contains', 'April')],
             context=_ctx(platforms=['Facets'], month=4, year=2025)),

    EvalCase('resolved-ctx-03', 'Resolved + Context: extend merges states',
             'Also include FL',
             [('resolved', 'contains', 'FL'),
              ('resolved', 'contains', 'CA')],
             context=_ctx(states=['CA', 'TX'], month=3, year=2025)),

    EvalCase('resolved-ctx-04', 'Resolved + Context: remove subtracts state',
             'Remove Texas',
             [('resolved', 'not_contains', 'TX'),
              ('resolved', 'contains', 'CA')],
             context=_ctx(states=['CA', 'TX', 'FL'], month=3, year=2025)),

    EvalCase('resolved-ctx-05', 'Resolved + Context: reset clears filters',
             'Reset all filters',
             [('resolved', 'not_contains', 'Amisys'),
              ('resolved', 'not_contains', 'CA')],
             context=_ctx(platforms=['Amisys'], states=['CA'], month=3, year=2025)),

    EvalCase('resolved-ctx-06', 'Resolved + Context: replace ignores old platform',
             'Change to Amisys',
             [('resolved', 'contains', 'Amisys'),
              ('resolved', 'not_contains', 'Facets')],
             context=_ctx(platforms=['Facets'], states=['TX'], month=3, year=2025)),

    EvalCase('resolved-ctx-07', 'Resolved + Context: use_context carries all filters',
             'Show that again',
             [('resolved', 'contains', 'Amisys'),
              ('resolved', 'contains', 'CA')],
             context=_ctx(platforms=['Amisys'], states=['CA'], month=3, year=2025)),

    # -----------------------------------------------------------------------
    # FORECAST MONTH FILTER (Apr-25 format)
    # -----------------------------------------------------------------------
    EvalCase('fmonth-01', 'Forecast Month Filter',
             'Show Apr-25 data',
             [('forecast_months', 'in', 'Apr-25')]),

    EvalCase('fmonth-02', 'Forecast Month Filter',
             'May-25 and Jun-25 forecast',
             [('forecast_months', 'in', 'May-25'),
              ('forecast_months', 'in', 'Jun-25')]),

    EvalCase('fmonth-03', 'Forecast Month Filter — title-case',
             'Show apr-25 data',
             [('forecast_months', 'in', 'Apr-25')]),

    EvalCase('fmonth-04', 'Forecast Month Filter — not confused with year',
             'Show data for march 2025',
             [('forecast_months', 'is_empty', None)]),

    # -----------------------------------------------------------------------
    # IMPLICIT INFO
    # -----------------------------------------------------------------------
    EvalCase('implicit-01', 'Implicit — uses_previous_context',
             'Same as before',
             [('implicit.uses_context', 'is_true', None)]),

    EvalCase('implicit-02', 'Implicit — uses_previous_context',
             'Keep those filters but show march',
             [('implicit.uses_context', 'is_true', None)]),

    EvalCase('implicit-03', 'Implicit — extend operation',
             'Also show Facets',
             [('implicit.operation', '==', 'extend')]),

    EvalCase('implicit-04', 'Implicit — remove operation',
             'Remove California filter',
             [('implicit.operation', '==', 'remove')]),

    EvalCase('implicit-05', 'Implicit — replace operation',
             'Change to Amisys',
             [('implicit.operation', '==', 'replace')]),

    EvalCase('implicit-06', 'Implicit — reset_filter',
             'Show all months',
             [('implicit.reset_filter', 'is_true', None)]),

    # -----------------------------------------------------------------------
    # CONFIDENCE SCORING
    # -----------------------------------------------------------------------
    EvalCase('conf-01', 'Confidence — month + year + filter',
             'Show Amisys for March 2025',
             [('confidence', '==', 0.95)]),

    EvalCase('conf-02', 'Confidence — month + year, no filter',
             'Show data for March 2025',
             [('confidence', '==', 0.85)]),

    EvalCase('conf-03', 'Confidence — month only',
             'Show March forecast',
             [('confidence', '==', 0.70)]),

    EvalCase('conf-04', 'Confidence — year only',
             'Show 2025 data',
             [('confidence', '==', 0.70)]),

    EvalCase('conf-05', 'Confidence — filter only, no time',
             'Show Amisys Domestic claims',
             [('confidence', '==', 0.60)]),

    EvalCase('conf-06', 'Confidence — no entities',
             'Hello there',
             [('confidence', '==', 0.40)]),

    # -----------------------------------------------------------------------
    # ADVERSARIAL
    # -----------------------------------------------------------------------
    EvalCase('adv-01', 'Adversarial — all entities jumbled',
             '2025 march CA Amisys Domestic claims',
             [('year',       '==', ['2025']),
              ('month',      '==', ['3']),
              ('states',     'in', 'CA'),
              ('platforms',  'in', 'Amisys'),
              ('localities', 'in', 'Domestic'),
              ('case_types', 'in', 'Claims Processing')]),

    EvalCase('adv-02', 'Adversarial — ALL CAPS input',
             'SHOW AMISYS FOR MARCH 2025 IN CALIFORNIA',
             [('month',     '==', ['3']),
              ('year',      '==', ['2025']),
              ('platforms', 'in', 'Amisys'),
              ('states',    'in', 'CA')]),

    EvalCase('adv-03', 'Adversarial — multiple typos together',
             'amysis offshore march 2025 CA enroll',
             [('platforms',  'in', 'Amisys'),
              ('localities', 'in', 'Global'),
              ('month',      '==', ['3']),
              ('states',     'in', 'CA'),
              ('case_types', 'in', 'Enrollment'),
              ('corrections.count', '>=', 2)]),

    EvalCase('adv-04', 'Adversarial — "may" as month vs modal verb',
             'Show may 2025 forecast',
             [('month', '==', ['5'])]),

    EvalCase('adv-05', 'Adversarial — "OK" opener is not Oklahoma',
             'OK show me California data for march 2025',
             [('states', 'not_in', 'OK'),
              ('states', 'in', 'CA')]),

    EvalCase('adv-06', 'Adversarial — "or" conjunction not Oregon',
             'Show amisys or facets data',
             [('states', 'not_in', 'OR')]),

    EvalCase('adv-07', 'Adversarial — minimal input',
             'forecast',
             [('confidence', '==', 0.40)]),

    EvalCase('adv-08', 'Adversarial — original text preserved',
             '  Show   Amisys   2025  ',
             [('resolved', 'is_not_empty', None)]),  # must not crash

    EvalCase('adv-09', 'Adversarial — correct spelling logged as zero corrections',
             'Amisys Domestic march 2025',
             [('corrections.count', '==', 0)]),

    EvalCase('adv-10', 'Adversarial — "show me" does not extract ME as state',
             'Show me the Amisys data',
             [('states', 'not_in', 'ME')]),

    # -----------------------------------------------------------------------
    # COMPLEX SENTENCES — multi-filter, full natural language
    # These mirror realistic user queries containing several filters at once.
    # -----------------------------------------------------------------------

    # ── Basic multi-filter ──────────────────────────────────────────────────

    EvalCase('complex-01', 'Complex — multi-filter with forecast months (proper format)',
             'Get me the March 2025 forecast data for Amisys, showing only '
             'Apr-25, May-25, Jun-25 and Jul-25 months, for California and Texas '
             'claims processing',
             [('month',          '==', ['3']),
              ('year',           '==', ['2025']),
              ('platforms',      'in', 'Amisys'),
              ('states',         'in', 'CA'),
              ('states',         'in', 'TX'),
              ('case_types',     'in', 'Claims Processing'),
              ('forecast_months','in', 'Apr-25'),
              ('forecast_months','in', 'May-25'),
              ('forecast_months','in', 'Jun-25'),
              ('forecast_months','in', 'Jul-25')]),

    EvalCase('complex-02', 'Complex — forecast months written without year suffix (LIMITATION)',
             # Apr, May, Jun without -25 suffix — regex requires the -XX suffix,
             # so these will NOT be picked up as forecast month filters.
             # This case intentionally exposes that gap in the current implementation.
             'Get me data for March 2025 forecast data for forecast months '
             'Apr, May, Jun and Jul only, get me only the Amisys data',
             [('month',          '==', ['3']),
              ('year',           '==', ['2025']),
              ('platforms',      'in', 'Amisys'),
              # months extracted as regular months (first one wins: April = 4)
              ('month',          '==', ['3']),   # March still dominates
              # forecast_months should be EMPTY — pattern requires Apr-25 style
              ('forecast_months','is_empty', None)]),

    EvalCase('complex-03', 'Complex — two platforms, two case types, two states',
             'Show me all Amisys and Facets domestic claims processing and enrollment '
             'data for March 2025 in California and Texas',
             [('month',          '==', ['3']),
              ('year',           '==', ['2025']),
              ('platforms',      'in', 'Amisys'),
              ('platforms',      'in', 'Facets'),
              ('localities',     'in', 'Domestic'),
              ('states',         'in', 'CA'),
              ('states',         'in', 'TX'),
              ('case_types',     'in', 'Claims Processing'),
              ('case_types',     'in', 'Enrollment')]),

    EvalCase('complex-04', 'Complex — totals only with multiple filters',
             'I need to see the April 2025 Facets forecast for appeals and adjustments '
             'in the global workforce across OH, PA and NY states, showing totals only',
             [('month',          '==', ['4']),
              ('year',           '==', ['2025']),
              ('platforms',      'in', 'Facets'),
              ('localities',     'in', 'Global'),
              ('states',         'in', 'OH'),
              ('states',         'in', 'PA'),
              ('states',         'in', 'NY'),
              ('case_types',     'in', 'Appeals'),
              ('case_types',     'in', 'Adjustments'),
              ('show_totals_only','==', [True])]),

    EvalCase('complex-05', 'Complex — main_lob phrase + multiple states',
             'What is the staffing capacity for Amisys Medicaid Domestic in the states '
             'of North Carolina, South Carolina and Virginia for December 2025?',
             [('month',      '==', ['12']),
              ('year',       '==', ['2025']),
              ('main_lobs',  'is_not_empty', None),
              ('states',     'in', 'NC'),
              ('states',     'in', 'SC'),
              ('states',     'in', 'VA')]),

    EvalCase('complex-06', 'Complex — all three platforms, all four case types',
             'I need a comprehensive view — show all domestic and global platforms '
             'Amisys, Facets and Xcelys for claims, enrollment, appeals and adjustments '
             'in New York, Pennsylvania, Ohio, New Jersey and Maryland for April 2025, '
             'just give me the summary totals',
             [('month',          '==', ['4']),
              ('year',           '==', ['2025']),
              ('platforms',      'in', 'Amisys'),
              ('platforms',      'in', 'Facets'),
              ('platforms',      'in', 'Xcelys'),
              ('localities',     'in', 'Domestic'),
              ('localities',     'in', 'Global'),
              ('states',         'in', 'NY'),
              ('states',         'in', 'PA'),
              ('states',         'in', 'OH'),
              ('states',         'in', 'NJ'),
              ('states',         'in', 'MD'),
              ('case_types',     'in', 'Claims Processing'),
              ('case_types',     'in', 'Enrollment'),
              ('case_types',     'in', 'Appeals'),
              ('case_types',     'in', 'Adjustments'),
              ('show_totals_only','==', [True])]),

    EvalCase('complex-07', 'Complex — typos + multiple filters + totals',
             'Can I get the amysis and fecets offshore claims proc data '
             'for states CA, TX and FL in march 2025, just show me totals',
             [('month',          '==', ['3']),
              ('year',           '==', ['2025']),
              ('platforms',      'in', 'Amisys'),
              ('platforms',      'in', 'Facets'),
              ('localities',     'in', 'Global'),
              ('states',         'in', 'CA'),
              ('states',         'in', 'TX'),
              ('states',         'in', 'FL'),
              ('case_types',     'in', 'Claims Processing'),
              ('show_totals_only','==', [True]),
              ('corrections.count', '>=', 2)]),

    EvalCase('complex-08', 'Complex — six southeastern states',
             'Show enrollment and appeals numbers for all domestic platforms '
             'across the southeastern states including Florida, Georgia, Alabama, '
             'Tennessee, Mississippi and South Carolina for March 2025',
             [('month',      '==', ['3']),
              ('year',       '==', ['2025']),
              ('localities', 'in', 'Domestic'),
              ('states',     'in', 'FL'),
              ('states',     'in', 'GA'),
              ('states',     'in', 'AL'),
              ('states',     'in', 'TN'),
              ('states',     'in', 'MS'),
              ('states',     'in', 'SC'),
              ('case_types', 'in', 'Enrollment'),
              ('case_types', 'in', 'Appeals')]),

    EvalCase('complex-09', 'Complex — three forecast months + two platforms + locality',
             'Show me forecast for Apr-25 and May-25 only — Amisys and Facets platforms, '
             'domestic locality, for claims proc in Texas and California',
             [('platforms',      'in', 'Amisys'),
              ('platforms',      'in', 'Facets'),
              ('localities',     'in', 'Domestic'),
              ('states',         'in', 'TX'),
              ('states',         'in', 'CA'),
              ('case_types',     'in', 'Claims Processing'),
              ('forecast_months','in', 'Apr-25'),
              ('forecast_months','in', 'May-25')]),

    EvalCase('complex-10', 'Complex — totals only, three case types, four northeast states',
             'Get me only the totals for the Xcelys global enrollment, adjustments '
             'and appeals data for the northeast states NY, NJ, CT and MA for March 2025',
             [('month',          '==', ['3']),
              ('year',           '==', ['2025']),
              ('platforms',      'in', 'Xcelys'),
              ('localities',     'in', 'Global'),
              ('states',         'in', 'NY'),
              ('states',         'in', 'NJ'),
              ('states',         'in', 'CT'),
              ('states',         'in', 'MA'),
              ('case_types',     'in', 'Enrollment'),
              ('case_types',     'in', 'Adjustments'),
              ('case_types',     'in', 'Appeals'),
              ('show_totals_only','==', [True])]),

    EvalCase('complex-11', 'Complex — three forecast month columns, ambiguous OK state',
             'Give me the breakdown of forecast months Jun-25, Jul-25, Aug-25 for '
             'Facets domestic enrollment and claims processing across TX, OK and LA',
             # OK follows TX in a state list — contextual rule should fire
             [('platforms',      'in', 'Facets'),
              ('localities',     'in', 'Domestic'),
              ('states',         'in', 'TX'),
              ('states',         'in', 'OK'),
              ('states',         'in', 'LA'),
              ('case_types',     'in', 'Enrollment'),
              ('case_types',     'in', 'Claims Processing'),
              ('forecast_months','in', 'Jun-25'),
              ('forecast_months','in', 'Jul-25'),
              ('forecast_months','in', 'Aug-25')]),

    EvalCase('complex-12', 'Complex — full sentence question format',
             'How many FTEs do we need for Amisys domestic claims processing in '
             'California and New York for the April 2025 forecast?',
             [('month',      '==', ['4']),
              ('year',       '==', ['2025']),
              ('platforms',  'in', 'Amisys'),
              ('localities', 'in', 'Domestic'),
              ('states',     'in', 'CA'),
              ('states',     'in', 'NY'),
              ('case_types', 'in', 'Claims Processing'),
              ('intent',     '==', 'query_data')]),

    EvalCase('complex-13', 'Complex — West Coast states with Oregon (OR after CA)',
             'For the previous forecast period show me the Amisys Medicaid Domestic '
             'data for all the West Coast states California, Oregon and Washington',
             # Oregon follows California so OR should be extracted as state
             [('main_lobs',          'is_not_empty', None),
              ('states',             'in', 'CA'),
              ('states',             'in', 'OR'),
              ('states',             'in', 'WA'),
              ('implicit.uses_context', 'is_true', None)]),

    EvalCase('complex-14', 'Complex — extend with context, many new filters',
             'Please also add Facets offshore enrollment and adjustment data for '
             'Ohio and Michigan to the current view',
             [('intent',     '==', 'extend_filters'),
              ('platforms',  'in', 'Facets'),
              ('localities', 'in', 'Global'),
              ('states',     'in', 'OH'),
              ('states',     'in', 'MI'),
              ('case_types', 'in', 'Enrollment'),
              ('case_types', 'in', 'Adjustments')]),

    EvalCase('complex-15', 'Complex — remove multiple states and a case type',
             'Remove California, Texas and Florida from the states filter '
             'and also remove claims processing, keep everything else the same',
             [('intent',     '==', 'remove_filters'),
              ('states',     'in', 'CA'),
              ('states',     'in', 'TX'),
              ('states',     'in', 'FL'),
              ('case_types', 'in', 'Claims Processing'),
              ('implicit.uses_context', 'is_true', None)]),

    # ── Context-driven complex queries ────────────────────────────────────

    EvalCase('complex-ctx-01', 'Complex + Context — use same period, add filters',
             'Using the same month and year show me Amisys domestic claims for '
             'California, Texas and New York only',
             [('intent',     '==', 'use_context'),
              ('platforms',  'in', 'Amisys'),
              ('localities', 'in', 'Domestic'),
              ('states',     'in', 'CA'),
              ('states',     'in', 'TX'),
              ('states',     'in', 'NY'),
              ('case_types', 'in', 'Claims Processing'),
              ('resolved',   'contains', 'April'),   # month from context
              ('resolved',   'contains', '2025')],   # year from context
             context=_ctx(month=4, year=2025)),

    EvalCase('complex-ctx-02', 'Complex + Context — extend with 3 new states',
             'Also include Ohio, Michigan and Pennsylvania to the existing state filters',
             [('intent',   '==', 'extend_filters'),
              ('states',   'in', 'OH'),
              ('states',   'in', 'MI'),
              ('states',   'in', 'PA'),
              # context states should be merged into resolved
              ('resolved', 'contains', 'CA'),
              ('resolved', 'contains', 'OH')],
             context=_ctx(platforms=['Amisys'], states=['CA', 'TX'], month=3, year=2025)),

    EvalCase('complex-ctx-03', 'Complex + Context — replace platform + locality',
             'Actually switch to Xcelys offshore only for the same period and states',
             [('platforms',  'in', 'Xcelys'),
              ('localities', 'in', 'Global'),
              # context states should be in resolved (replace only changes platform/locality)
              ('resolved',   'contains', 'CA'),
              ('resolved',   'contains', 'Xcelys'),
              ('resolved',   'not_contains', 'Amisys')],
             context=_ctx(platforms=['Amisys'], states=['CA', 'TX'],
                          localities=['Domestic'], month=3, year=2025)),

    EvalCase('complex-ctx-04', 'Complex + Context — multi-filter remove',
             'Remove Facets and Xcelys from platforms and remove all global localities',
             [('intent',     '==', 'remove_filters'),
              ('platforms',  'in', 'Facets'),
              ('platforms',  'in', 'Xcelys'),
              ('localities', 'in', 'Global'),
              # Amisys and Domestic should survive in resolved (carried from context)
              ('resolved',   'contains', 'Amisys'),
              ('resolved',   'contains', 'Domestic')],
             context=_ctx(platforms=['Amisys', 'Facets', 'Xcelys'],
                          localities=['Domestic', 'Global'],
                          month=4, year=2025)),

    EvalCase('complex-ctx-05', 'Complex + Context — reset then specific query',
             'Reset all filters and show me only Xcelys global claims for Apr-25',
             # reset_filters wins (highest priority); entities still extracted
             [('intent',          '==', 'reset_filters'),
              ('platforms',       'in', 'Xcelys'),
              ('localities',      'in', 'Global'),
              ('case_types',      'in', 'Claims Processing'),
              ('forecast_months', 'in', 'Apr-25'),
              # After reset, context platforms should NOT appear in resolved
              ('resolved', 'not_contains', 'Amisys')],
             context=_ctx(platforms=['Amisys'], states=['CA'], month=3, year=2025)),

    # ── Tricky phrasing ──────────────────────────────────────────────────

    EvalCase('complex-tricky-01', 'Complex Tricky — "just the totals" + many filters',
             'For the March 2025 forecast please give me just the totals for '
             'Amisys and Facets domestic teams across all of CA, TX, FL, NY and OH '
             'for claims processing and enrollment combined',
             [('month',          '==', ['3']),
              ('year',           '==', ['2025']),
              ('platforms',      'in', 'Amisys'),
              ('platforms',      'in', 'Facets'),
              ('localities',     'in', 'Domestic'),
              ('states',         'in', 'CA'),
              ('states',         'in', 'TX'),
              ('states',         'in', 'FL'),
              ('states',         'in', 'NY'),
              ('states',         'in', 'OH'),
              ('case_types',     'in', 'Claims Processing'),
              ('case_types',     'in', 'Enrollment'),
              ('show_totals_only','==', [True])]),

    EvalCase('complex-tricky-02', 'Complex Tricky — passive / indirect phrasing',
             'What does the April 2025 forecast look like for Xcelys domestic '
             'enrollment across New Jersey, Connecticut and Delaware?',
             [('month',      '==', ['4']),
              ('year',       '==', ['2025']),
              ('platforms',  'in', 'Xcelys'),
              ('localities', 'in', 'Domestic'),
              ('states',     'in', 'NJ'),
              ('states',     'in', 'CT'),
              ('states',     'in', 'DE'),
              ('case_types', 'in', 'Enrollment')]),

    EvalCase('complex-tricky-03', 'Complex Tricky — verbose with filler words',
             'I would really like to see if you could pull up the full detailed data '
             'set for the Facets platform for the month of March in the year 2025, '
             'specifically looking at domestic locality, focusing on the states of '
             'California and Texas and filtering by claims processing work type',
             [('month',      '==', ['3']),
              ('year',       '==', ['2025']),
              ('platforms',  'in', 'Facets'),
              ('localities', 'in', 'Domestic'),
              ('states',     'in', 'CA'),
              ('states',     'in', 'TX'),
              ('case_types', 'in', 'Claims Processing')]),

    EvalCase('complex-tricky-04', 'Complex Tricky — multiple typos across all entity types',
             'Get me amysis and xcylys dom teams claims proc and enroll data '
             'for CA, TX in mar 2025 showing Apr-25 May-25 Jun-25 totals only',
             [('month',          '==', ['3']),
              ('year',           '==', ['2025']),
              ('platforms',      'in', 'Amisys'),
              ('platforms',      'in', 'Xcelys'),
              ('localities',     'in', 'Domestic'),
              ('states',         'in', 'CA'),
              ('states',         'in', 'TX'),
              ('case_types',     'in', 'Claims Processing'),
              ('case_types',     'in', 'Enrollment'),
              ('forecast_months','in', 'Apr-25'),
              ('forecast_months','in', 'May-25'),
              ('forecast_months','in', 'Jun-25'),
              ('show_totals_only','==', [True]),
              ('corrections.count', '>=', 2)]),

    EvalCase('complex-tricky-05', 'Complex Tricky — intent hidden inside long sentence',
             'I know we were looking at Amisys Domestic last time but this time '
             'I would like to also include Facets Global for the same states and period',
             [('intent',     '==', 'extend_filters'),
              ('platforms',  'in', 'Facets'),
              ('localities', 'in', 'Global'),
              ('implicit.uses_context', 'is_true', None)]),

    EvalCase('complex-tricky-06', 'Complex Tricky — "same" period + new complete filter set',
             'For the same period as before give me Xcelys onshore appeals data '
             'for North Carolina, Georgia and Tennessee',
             [('implicit.uses_context', 'is_true', None),
              ('platforms',  'in', 'Xcelys'),
              ('localities', 'in', 'Domestic'),
              ('states',     'in', 'NC'),
              ('states',     'in', 'GA'),
              ('states',     'in', 'TN'),
              ('case_types', 'in', 'Appeals'),
              ('resolved',   'contains', 'March'),
              ('resolved',   'contains', '2025')],
             context=_ctx(month=3, year=2025)),

    EvalCase('complex-tricky-07', 'Complex Tricky — confidence should be max (many entities)',
             'Show Amisys domestic claims for CA in March 2025',
             [('confidence', '==', 0.95),   # month+year+filter → 0.95
              ('month',      '==', ['3']),
              ('year',       '==', ['2025']),
              ('platforms',  'in', 'Amisys'),
              ('localities', 'in', 'Domestic'),
              ('states',     'in', 'CA'),
              ('case_types', 'in', 'Claims Processing')]),

    EvalCase('complex-tricky-08', 'Complex Tricky — six forecast months',
             'Display Apr-25 May-25 Jun-25 Jul-25 Aug-25 Sep-25 data for '
             'Amisys domestic in California march 2025',
             [('forecast_months','in', 'Apr-25'),
              ('forecast_months','in', 'May-25'),
              ('forecast_months','in', 'Jun-25'),
              ('forecast_months','in', 'Jul-25'),
              ('forecast_months','in', 'Aug-25'),
              ('forecast_months','in', 'Sep-25'),
              ('platforms',      'in', 'Amisys'),
              ('localities',     'in', 'Domestic'),
              ('states',         'in', 'CA')]),

    # -----------------------------------------------------------------------
    # CPH / NUMERIC MODIFICATION
    #
    # These cases cover requests to change a specific metric value.
    # The preprocessor currently has NO support for this — all modification.*
    # checks will FAIL, and intent will be wrong.  This section is intentionally
    # written to expose the gap so it appears clearly in the error-analysis report.
    #
    # Expected (desired) behaviour per case is documented inline.
    # intent should be: 'modify_value'  (not yet in INTENT_PATTERNS)
    # entities needed:
    #   modification_field     — which field to change  (cph, fte_available, …)
    #   modification_operation — set_to | increase_to | decrease_to |
    #                            increase_by_pct | decrease_by_pct
    #   modification_value     — the target number or percentage (string)
    #   modification_unit      — 'absolute' | 'percent'
    # -----------------------------------------------------------------------

    # ── "Set to" / "increase to" / "decrease to" (absolute target) ─────────

    EvalCase('cph-01', 'CPH Modification — increase to absolute value',
             'Increase CPH to 14',
             [('intent',                '==', 'modify_value'),   # FAIL — not implemented
              ('modification.field',    '==', 'cph'),            # FAIL
              ('modification.operation','==', 'set_to'),         # FAIL (increase to = set_to)
              ('modification.value',    '==', '14'),             # FAIL
              ('modification.unit',     '==', 'absolute')]),     # FAIL

    EvalCase('cph-02', 'CPH Modification — set to decimal',
             'Set target CPH to 3.5',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'set_to'),
              ('modification.value',    '==', '3.5'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-03', 'CPH Modification — change keyword (closest current match)',
             'Change CPH to 4.0',
             # "change" hits replace_filters — wrong intent, but partially detectable
             [('intent',                '==', 'modify_value'),   # FAIL — detects replace_filters instead
              ('modification.field',    '==', 'cph'),
              ('modification.value',    '==', '4.0'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-04', 'CPH Modification — decrease to absolute value',
             'Decrease target CPH to 2.5',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'set_to'),
              ('modification.value',    '==', '2.5'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-05', 'CPH Modification — update phrasing',
             'Update the CPH value to 12',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'set_to'),
              ('modification.value',    '==', '12'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-06', 'CPH Modification — question phrasing',
             'Can you set the CPH to 5?',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'set_to'),
              ('modification.value',    '==', '5'),
              ('modification.unit',     '==', 'absolute')]),

    # ── "Increase by %" (relative percentage) ───────────────────────────────

    EvalCase('cph-07', 'CPH Modification — increase by percentage',
             'Increase CPH by 10%',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'increase_by_pct'),
              ('modification.value',    '==', '10'),
              ('modification.unit',     '==', 'percent')]),

    EvalCase('cph-08', 'CPH Modification — decrease by percentage',
             'Decrease target CPH by 5%',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'decrease_by_pct'),
              ('modification.value',    '==', '5'),
              ('modification.unit',     '==', 'percent')]),

    EvalCase('cph-09', 'CPH Modification — increase by large percentage',
             'Increase the CPH by 25%',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'increase_by_pct'),
              ('modification.value',    '==', '25'),
              ('modification.unit',     '==', 'percent')]),

    EvalCase('cph-10', 'CPH Modification — raise phrasing',
             'Raise CPH by 15%',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'increase_by_pct'),
              ('modification.value',    '==', '15'),
              ('modification.unit',     '==', 'percent')]),

    EvalCase('cph-11', 'CPH Modification — reduce phrasing',
             'Reduce CPH by 8%',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'decrease_by_pct'),
              ('modification.value',    '==', '8'),
              ('modification.unit',     '==', 'percent')]),

    # ── Other named fields ───────────────────────────────────────────────────

    EvalCase('cph-12', 'CPH Modification — FTE available, absolute',
             'Increase FTE available to 50',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'fte_available'),
              ('modification.operation','==', 'set_to'),
              ('modification.value',    '==', '50'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-13', 'CPH Modification — FTE required, percentage increase',
             'Increase FTE required by 20%',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'fte_required'),
              ('modification.operation','==', 'increase_by_pct'),
              ('modification.value',    '==', '20'),
              ('modification.unit',     '==', 'percent')]),

    EvalCase('cph-14', 'CPH Modification — shrinkage, percentage increase',
             'Increase the shrinkage by 2%',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'shrinkage'),
              ('modification.operation','==', 'increase_by_pct'),
              ('modification.value',    '==', '2'),
              ('modification.unit',     '==', 'percent')]),

    EvalCase('cph-15', 'CPH Modification — capacity, decrease by percent',
             'Decrease capacity by 12%',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'capacity'),
              ('modification.operation','==', 'decrease_by_pct'),
              ('modification.value',    '==', '12'),
              ('modification.unit',     '==', 'percent')]),

    # ── Vague field references ───────────────────────────────────────────────

    EvalCase('cph-16', 'CPH Modification — vague "the value"',
             'Increase the value to 10',
             # field is ambiguous — preprocessor should flag it as unknown field
             [('intent',                '==', 'modify_value'),
              ('modification.value',    '==', '10'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-17', 'CPH Modification — "it" reference (requires context)',
             'Set it to 4.5',
             # field is a pronoun — must be resolved from context
             [('intent',                '==', 'modify_value'),
              ('modification.value',    '==', '4.5'),
              ('implicit.uses_context', 'is_true', None)]),

    # ── Combined: modification + data filters ───────────────────────────────

    EvalCase('cph-18', 'CPH Modification — with row context filters',
             'For this Amisys Domestic row in California increase CPH to 14',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'set_to'),
              ('modification.value',    '==', '14'),
              ('localities',            'in', 'Domestic')]),

    EvalCase('cph-19', 'CPH Modification — with row context, percentage',
             'Decrease the target CPH by 10% for the Facets Global claims row',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'decrease_by_pct'),
              ('modification.value',    '==', '10'),
              ('modification.unit',     '==', 'percent'),
              ('localities',            'in', 'Global'),
              ('case_types',            'in', 'Claims Processing')]),

    EvalCase('cph-20', 'CPH Modification — verbose natural language',
             'Can you please go ahead and change the target cases per hour '
             'value for this row to 6.5?',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'set_to'),
              ('modification.value',    '==', '6.5'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-21', 'CPH Modification — "from X to Y" phrasing',
             'Change target CPH from 3.5 to 5.0',
             # from-to: operation = set_to, value = target (5.0)
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'set_to'),
              ('modification.value',    '==', '5.0'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-22', 'CPH Modification — "bump up" informal phrasing',
             'Bump up the CPH to 11',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'set_to'),
              ('modification.value',    '==', '11'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-23', 'CPH Modification — "bring down" informal phrasing',
             'Bring down the CPH by 3%',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'decrease_by_pct'),
              ('modification.value',    '==', '3'),
              ('modification.unit',     '==', 'percent')]),

    EvalCase('cph-24', 'CPH Modification — combined: same context + change cph',
             'Keep the same filters but increase the CPH to 7',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.value',    '==', '7'),
              ('implicit.uses_context', 'is_true', None)]),

    EvalCase('cph-25', 'CPH Modification — integer CPH check phrasing',
             'What if I increase CPH to 18 for this record?',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'set_to'),
              ('modification.value',    '==', '18'),
              ('modification.unit',     '==', 'absolute')]),

    # -----------------------------------------------------------------------
    # CPH / NUMERIC — ADD TO / SUBTRACT FROM EXISTING VALUE
    #
    # These differ from "set to": the user wants to DELTA the current value,
    # not replace it.  operation = add_to | subtract_from, unit = absolute.
    # -----------------------------------------------------------------------

    EvalCase('cph-add-01', 'CPH Add/Subtract — add absolute value',
             'Add 2 to CPH',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'add_to'),
              ('modification.value',    '==', '2'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-add-02', 'CPH Add/Subtract — add decimal',
             'Add 0.5 to the target CPH',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'add_to'),
              ('modification.value',    '==', '0.5'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-add-03', 'CPH Add/Subtract — subtract absolute',
             'Subtract 1 from CPH',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'subtract_from'),
              ('modification.value',    '==', '1'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-add-04', 'CPH Add/Subtract — subtract decimal',
             'Subtract 0.5 from the current CPH value',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'subtract_from'),
              ('modification.value',    '==', '0.5'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-add-05', 'CPH Add/Subtract — add to FTE available',
             'Add 5 to FTE available',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'fte_available'),
              ('modification.operation','==', 'add_to'),
              ('modification.value',    '==', '5'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-add-06', 'CPH Add/Subtract — subtract from FTE required',
             'Subtract 10 from FTE required',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'fte_required'),
              ('modification.operation','==', 'subtract_from'),
              ('modification.value',    '==', '10'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-add-07', 'CPH Add/Subtract — add to shrinkage',
             'Add 3 to the shrinkage',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'shrinkage'),
              ('modification.operation','==', 'add_to'),
              ('modification.value',    '==', '3'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-add-08', 'CPH Add/Subtract — informal "give an extra"',
             'Give CPH an extra 2',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'add_to'),
              ('modification.value',    '==', '2'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-add-09', 'CPH Add/Subtract — informal "take away"',
             'Take away 1.5 from CPH',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'subtract_from'),
              ('modification.value',    '==', '1.5'),
              ('modification.unit',     '==', 'absolute')]),

    EvalCase('cph-add-10', 'CPH Add/Subtract — combined: add + context filters',
             'For this Amisys Domestic CA row add 2 to the CPH',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'cph'),
              ('modification.operation','==', 'add_to'),
              ('modification.value',    '==', '2'),
              ('localities',            'in', 'Domestic')]),

    EvalCase('cph-add-11', 'CPH Add/Subtract — add percentage to field',
             'Add 5% to the current shrinkage',
             # adding a percentage = increase_by_pct, not add_to
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'shrinkage'),
              ('modification.operation','==', 'increase_by_pct'),
              ('modification.value',    '==', '5'),
              ('modification.unit',     '==', 'percent')]),

    EvalCase('cph-add-12', 'CPH Add/Subtract — subtract percentage from field',
             'Subtract 3% from the capacity',
             [('intent',                '==', 'modify_value'),
              ('modification.field',    '==', 'capacity'),
              ('modification.operation','==', 'decrease_by_pct'),
              ('modification.value',    '==', '3'),
              ('modification.unit',     '==', 'percent')]),

    # -----------------------------------------------------------------------
    # CHART REQUESTS
    #
    # User asks for a visual chart/graph.
    # intent should be 'request_chart' (not yet in INTENT_PATTERNS)
    # entities needed:
    #   requested_outputs = ['chart']
    #   chart_type        = 'bar' | 'line' | 'pie' | 'area' | None
    # -----------------------------------------------------------------------

    EvalCase('chart-01', 'Chart — generic chart request',
             'Show me a chart',
             [('intent',              '==', 'request_chart'),
              ('output.requested',    'in', 'chart'),
              ('output.chart_type',   '==', None)]),

    EvalCase('chart-02', 'Chart — bar chart',
             'Give me a bar chart',
             [('intent',              '==', 'request_chart'),
              ('output.requested',    'in', 'chart'),
              ('output.chart_type',   '==', 'bar')]),

    EvalCase('chart-03', 'Chart — line chart',
             'I want a line chart',
             [('intent',              '==', 'request_chart'),
              ('output.requested',    'in', 'chart'),
              ('output.chart_type',   '==', 'line')]),

    EvalCase('chart-04', 'Chart — pie chart',
             'Display a pie chart for this data',
             [('intent',              '==', 'request_chart'),
              ('output.requested',    'in', 'chart'),
              ('output.chart_type',   '==', 'pie')]),

    EvalCase('chart-05', 'Chart — area chart',
             'Show me an area chart',
             [('intent',              '==', 'request_chart'),
              ('output.requested',    'in', 'chart'),
              ('output.chart_type',   '==', 'area')]),

    EvalCase('chart-06', 'Chart — "visualize" phrasing',
             'Visualize the data',
             [('intent',              '==', 'request_chart'),
              ('output.requested',    'in', 'chart')]),

    EvalCase('chart-07', 'Chart — "plot" phrasing',
             'Can you plot this?',
             [('intent',              '==', 'request_chart'),
              ('output.requested',    'in', 'chart')]),

    EvalCase('chart-08', 'Chart — "graph" phrasing',
             'Graph the results',
             [('intent',              '==', 'request_chart'),
              ('output.requested',    'in', 'chart')]),

    EvalCase('chart-09', 'Chart — with data filters',
             'Show me a bar chart of Amisys data for March 2025',
             [('intent',              '==', 'request_chart'),
              ('output.requested',    'in', 'chart'),
              ('output.chart_type',   '==', 'bar'),
              ('month',               '==', ['3']),
              ('year',                '==', ['2025'])]),

    EvalCase('chart-10', 'Chart — with multiple filters and chart type',
             'Give me a line chart for claims processing in CA and TX for March 2025',
             [('intent',              '==', 'request_chart'),
              ('output.requested',    'in', 'chart'),
              ('output.chart_type',   '==', 'line'),
              ('case_types',          'in', 'Claims Processing'),
              ('month',               '==', ['3']),
              ('year',                '==', ['2025'])]),

    # -----------------------------------------------------------------------
    # MULTI-OUTPUT: DATA + CHART + TOTALS (any combination)
    #
    # User requests multiple output types in one sentence.
    # The preprocessor must recognise ALL requested outputs and their order.
    # intent: 'query_data'  (the base intent is still fetching data)
    # entities needed:
    #   requested_outputs = subset of ['data', 'chart', 'totals']  in any order
    #   chart_type        = specified type if mentioned
    # -----------------------------------------------------------------------

    EvalCase('multi-output-01', 'Multi-output — data + chart',
             'Show me the data and a chart',
             [('intent',           '==', 'query_data'),
              ('output.requested', 'in', 'data'),
              ('output.requested', 'in', 'chart')]),

    EvalCase('multi-output-02', 'Multi-output — data + totals',
             'Give me the full data and the totals',
             [('intent',           '==', 'query_data'),
              ('output.requested', 'in', 'data'),
              ('output.requested', 'in', 'totals')]),

    EvalCase('multi-output-03', 'Multi-output — chart + totals',
             'I want a bar chart and the summary totals',
             [('intent',            '==', 'query_data'),
              ('output.requested',  'in', 'chart'),
              ('output.requested',  'in', 'totals'),
              ('output.chart_type', '==', 'bar')]),

    EvalCase('multi-output-04', 'Multi-output — data + chart + totals (all three)',
             'Give me the data, a chart and the totals',
             [('intent',           '==', 'query_data'),
              ('output.requested', 'in', 'data'),
              ('output.requested', 'in', 'chart'),
              ('output.requested', 'in', 'totals')]),

    EvalCase('multi-output-05', 'Multi-output — all three with filters',
             'For March 2025 Amisys data give me the table, a bar chart and the totals',
             [('intent',            '==', 'query_data'),
              ('month',             '==', ['3']),
              ('year',              '==', ['2025']),
              ('output.requested',  'in', 'data'),
              ('output.requested',  'in', 'chart'),
              ('output.requested',  'in', 'totals'),
              ('output.chart_type', '==', 'bar')]),

    EvalCase('multi-output-06', 'Multi-output — chart only, explicit "no table"',
             'Just a chart please, no table',
             [('output.requested',  'in',     'chart'),
              ('output.requested',  'not_in', 'data'),
              ('output.requested',  'not_in', 'totals')]),

    EvalCase('multi-output-07', 'Multi-output — table + totals, no chart',
             'Show me the table with the summary totals',
             [('output.requested', 'in',     'data'),
              ('output.requested', 'in',     'totals'),
              ('output.requested', 'not_in', 'chart')]),

    EvalCase('multi-output-08', 'Multi-output — totals + chart, no raw data',
             'Show totals and a bar chart for Amisys march 2025',
             [('output.requested',  'in',     'totals'),
              ('output.requested',  'in',     'chart'),
              ('output.requested',  'not_in', 'data'),
              ('output.chart_type', '==',     'bar'),
              ('month',             '==',     ['3']),
              ('year',              '==',     ['2025'])]),

    EvalCase('multi-output-09', 'Multi-output — all three, line chart, full filters',
             'Can I see the full data, a line chart and summary totals '
             'for March 2025 Amisys domestic claims?',
             [('intent',            '==', 'query_data'),
              ('month',             '==', ['3']),
              ('year',              '==', ['2025']),
              ('localities',        'in', 'Domestic'),
              ('case_types',        'in', 'Claims Processing'),
              ('output.requested',  'in', 'data'),
              ('output.requested',  'in', 'chart'),
              ('output.requested',  'in', 'totals'),
              ('output.chart_type', '==', 'line')]),

    EvalCase('multi-output-10', 'Multi-output — all three, complex filters, pie chart',
             'Show Facets data for March 2025, also give me a pie chart '
             'and the summary numbers',
             [('intent',            '==', 'query_data'),
              ('month',             '==', ['3']),
              ('year',              '==', ['2025']),
              ('output.requested',  'in', 'data'),
              ('output.requested',  'in', 'chart'),
              ('output.requested',  'in', 'totals'),
              ('output.chart_type', '==', 'pie')]),

    EvalCase('multi-output-11', 'Multi-output — "visualization" synonym for chart',
             'I want data for April 2025 along with a visualization '
             'and a total summary',
             [('month',            '==', ['4']),
              ('year',             '==', ['2025']),
              ('output.requested', 'in', 'data'),
              ('output.requested', 'in', 'chart'),
              ('output.requested', 'in', 'totals')]),

    EvalCase('multi-output-12', 'Multi-output — "everything": all three implied',
             'Give me everything — full data, chart and total summary '
             'for December 2025 Xcelys global enrollment',
             [('month',             '==', ['12']),
              ('year',              '==', ['2025']),
              ('localities',        'in', 'Global'),
              ('case_types',        'in', 'Enrollment'),
              ('output.requested',  'in', 'data'),
              ('output.requested',  'in', 'chart'),
              ('output.requested',  'in', 'totals')]),

    EvalCase('multi-output-13', 'Multi-output — data + chart, specific month columns',
             'Show the Apr-25 May-25 Jun-25 data for Amisys domestic CA '
             'with a bar chart',
             [('forecast_months',   'in', 'Apr-25'),
              ('forecast_months',   'in', 'May-25'),
              ('forecast_months',   'in', 'Jun-25'),
              ('localities',        'in', 'Domestic'),
              ('output.requested',  'in', 'data'),
              ('output.requested',  'in', 'chart'),
              ('output.chart_type', '==', 'bar')]),

    EvalCase('multi-output-14', 'Multi-output — totals only + chart (no raw rows)',
             'Just show the totals and a line chart for Facets March 2025',
             [('month',             '==', ['3']),
              ('year',              '==', ['2025']),
              ('output.requested',  'in', 'totals'),
              ('output.requested',  'in', 'chart'),
              ('output.requested',  'not_in', 'data'),
              ('output.chart_type', '==', 'line')]),

    EvalCase('multi-output-15', 'Multi-output — vague "show me everything"',
             'Show me everything for Amisys Domestic claims March 2025',
             # "everything" may or may not imply chart — ambiguous;
             # at minimum data + totals should be captured
             [('month',            '==', ['3']),
              ('year',             '==', ['2025']),
              ('localities',       'in', 'Domestic'),
              ('case_types',       'in', 'Claims Processing'),
              ('output.requested', 'in', 'data'),
              ('output.requested', 'in', 'totals')]),
]


# ===========================================================================
# Eval runner + report printer
# ===========================================================================

@dataclass
class CaseResult:
    case: EvalCase
    check_results: List[CheckResult]
    preprocessed: Any = None   # the raw PreprocessedMessage — stored for report detail

    @property
    def passed(self) -> bool:
        return all(cr.passed for cr in self.check_results)

    @property
    def failed_checks(self) -> List[CheckResult]:
        return [cr for cr in self.check_results if not cr.passed]


def run_all_evals() -> List[CaseResult]:
    results: List[CaseResult] = []
    for case in EVAL_CASES:
        output = _run(case.input, context=case.context)
        check_results = [_run_check(output, ch) for ch in case.checks]
        results.append(CaseResult(case=case, check_results=check_results, preprocessed=output))
    return results


def print_report(results: List[CaseResult]) -> int:
    """Print the full error-analysis report.  Returns number of failures."""
    from collections import defaultdict

    # Separate unimplemented-feature cases from the rest
    _unimpl_prefixes = ('cph-', 'chart-', 'multi-output-')
    cph_results   = [r for r in results if any(r.case.id.startswith(p) for p in _unimpl_prefixes)]
    other_results = [r for r in results if not any(r.case.id.startswith(p) for p in _unimpl_prefixes)]

    def _counts(subset):
        total  = len(subset)
        passed = sum(1 for r in subset if r.passed)
        t_chk  = sum(len(r.check_results) for r in subset)
        p_chk  = sum(sum(1 for cr in r.check_results if cr.passed) for r in subset)
        return total, passed, t_chk, p_chk

    ot, op, otc, opc = _counts(other_results)
    ct, cp, ctc, cpc = _counts(cph_results)
    grand_t,  grand_p  = ot + ct,  op + cp
    grand_tc, grand_pc = otc + ctc, opc + cpc

    W    = 72
    SEP  = '═' * W
    SEP2 = '─' * W

    pct = lambda n, d: f'{100*n//d}%' if d else 'n/a'

    print(f'\n{SEP}')
    print(f'  PREPROCESSOR EVALUATION — ERROR ANALYSIS REPORT')
    print(SEP)
    print(f'  {"Section":<38} {"Cases":>8}  {"Checks":>8}')
    print(SEP2)
    print(f'  {"Implemented features":<38} '
          f'{op}/{ot} ({pct(op,ot):>4})'
          f'  {opc}/{otc} ({pct(opc,otc):>4})')
    print(f'  {"CPH / Chart / Multi-output (TODO)":<38} '
          f'{cp}/{ct} ({pct(cp,ct):>4})'
          f'  {cpc}/{ctc} ({pct(cpc,ctc):>4})')
    print(SEP2)
    print(f'  {"TOTAL":<38} '
          f'{grand_p}/{grand_t} ({pct(grand_p,grand_t):>4})'
          f'  {grand_pc}/{grand_tc} ({pct(grand_pc,grand_tc):>4})')
    print(SEP)

    other_fails = [r for r in other_results if not r.passed]
    cph_fails   = [r for r in cph_results   if not r.passed]

    # ── Failures in implemented features ────────────────────────────────
    if other_fails:
        by_cat: Dict[str, List[CaseResult]] = defaultdict(list)
        for r in other_fails:
            by_cat[r.case.category].append(r)

        print(f'\n  FAILURES — IMPLEMENTED FEATURES  ({len(other_fails)} cases)\n')

        for category in sorted(by_cat):
            cat_all    = [r for r in other_results if r.case.category == category]
            cat_fails  = by_cat[category]
            print(SEP2)
            print(f'  [{category}]  {len(cat_fails)}/{len(cat_all)} failed')
            print(SEP2)
            for r in cat_fails:
                print(f'\n  FAIL  [{r.case.id}]  "{r.case.input}"')
                if r.case.context:
                    ctx = r.case.context
                    ctx_parts = [
                        f'platforms={ctx.active_platforms}' if ctx.active_platforms  else '',
                        f'states={ctx.active_states}'       if ctx.active_states      else '',
                        f'month={ctx.forecast_report_month}' if ctx.forecast_report_month else '',
                        f'year={ctx.forecast_report_year}'   if ctx.forecast_report_year  else '',
                    ]
                    print(f'       context: {", ".join(p for p in ctx_parts if p)}')
                for cr in r.failed_checks:
                    print(f'       ✗  {cr.check_desc}')
                    print(f'          expected : {cr.expected!r}')
                    print(f'          actual   : {cr.actual!r}')
    else:
        print(f'\n  ✓ All implemented-feature cases passed.\n')

    # ── CPH / modification failures (known gap) ──────────────────────────
    if cph_fails:
        print(f'\n{SEP}')
        print(f'  CPH / CHART / MULTI-OUTPUT — GAPS TO IMPLEMENT  ({len(cph_fails)} cases)')
        print(f'  These fail because the preprocessor does not yet support these features.')
        print(SEP2)

        by_op: Dict[str, List[CaseResult]] = defaultdict(list)
        for r in cph_fails:
            inp = r.case.input.lower()
            if r.case.id.startswith('chart-'):
                grp = 'chart requests'
            elif r.case.id.startswith('multi-output-'):
                grp = 'multi-output (data + chart + totals)'
            elif '%' in inp or 'percent' in inp:
                grp = 'CPH — relative (by X%)'
            elif 'add ' in inp or 'subtract' in inp or 'take away' in inp:
                grp = 'CPH — add / subtract to existing value'
            elif ' to ' in inp:
                grp = 'CPH — absolute (set to X)'
            else:
                grp = 'CPH — other'
            by_op[grp].append(r)

        for grp in sorted(by_op):
            print(f'\n  — {grp} —')
            for r in by_op[grp]:
                actual_intent   = r.preprocessed.intent   if r.preprocessed else '?'
                actual_resolved = r.preprocessed.resolved_message if r.preprocessed else '?'
                failed_fields   = [cr.check_desc for cr in r.failed_checks]
                print(f'    [{r.case.id}]  "{r.case.input}"')
                print(f'             current intent   : {actual_intent!r}')
                print(f'             current resolved : {actual_resolved!r}')
                print(f'             missing checks   : {", ".join(failed_fields[:3])}')
                if len(failed_fields) > 3:
                    print(f'                      … and {len(failed_fields)-3} more')

    # ── Summary table ────────────────────────────────────────────────────
    print(f'\n{SEP}')
    print(f'  FULL CASE SUMMARY')
    print(SEP2)
    print(f'  {"ID":<20} {"Category":<34} {"Chk":>5}  {"Status"}')
    print(SEP2)
    for r in results:
        ok  = sum(cr.passed for cr in r.check_results)
        tot = len(r.check_results)
        status = '✓' if r.passed else '✗'
        print(f'  {r.case.id:<20} {r.case.category:<34} {ok}/{tot:>3}  {status}')
    print(SEP)
    print()

    return len(other_fails)   # only count non-CPH failures as "real" failures


# ===========================================================================
# Pytest integration
# ===========================================================================

@pytest.fixture(scope='session')
def eval_results():
    return run_all_evals()


def test_print_eval_report(eval_results):
    """
    Runs all eval cases, prints the full error-analysis report,
    then fails the test suite if any case failed.
    """
    failures = print_report(eval_results)
    assert failures == 0, (
        f'{failures} eval case(s) failed — see the report above for details.'
    )


# ===========================================================================
# Standalone execution:  python test_preprocessor_evals.py
# ===========================================================================
if __name__ == '__main__':
    all_results = run_all_evals()
    failures = print_report(all_results)
    sys.exit(0 if failures == 0 else 1)
