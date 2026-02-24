"""
Message Preprocessor Service

Redesigned pipeline — intent-first approach:

  1. Normalize     — fix whitespace, punctuation
  2. Spell-correct — fix domain typos (platforms, localities, case types)
  3. Detect intent — what does the user want to DO?
  4. Extract entities — specific values mentioned in the message
  5. Validate entities — normalise extracted values
  6. Detect implicit info — context references, extend/remove signals
  7. Craft resolved message — combine intent + entities + stored context
                              into a clear directive for tool-call accuracy
  8. Score confidence

Markets are NOT extracted here — their scope is too broad and they are
passed through only as part of a full main_lob string (Platform Market Locality).
"""
import re
import calendar
import logging
from typing import Dict, List, Tuple, Optional, Any
from difflib import SequenceMatcher

from langchain_core.messages import HumanMessage
from chat_app.services.tools.validation import PreprocessedMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Intent labels (used in crafted message)
# ---------------------------------------------------------------------------
_INTENT_LABELS: Dict[str, str] = {
    'query_data':      'Show forecast data',
    'extend_filters':  'Add to current filters and show data',
    'remove_filters':  'Remove from filters and show data',
    'replace_filters': 'Show data with new filters',
    'reset_filters':   'Show all data (reset filters)',
    'use_context':     'Show data using same filters as before',
    'unknown':         'Show data',
}


class MessagePreprocessor:
    """
    Preprocesses user messages using an intent-first pipeline.

    If an LLM is provided, intent classification and entity extraction
    are performed via a single structured LLM call.  Without an LLM,
    both steps fall back to deterministic regex rules.
    """

    # ------------------------------------------------------------------
    # Domain vocabulary (markets removed — scope too large)
    # ------------------------------------------------------------------
    DOMAIN_VOCABULARY: Dict[str, Any] = {
        'platforms': {
            'canonical': ['Amisys', 'Facets', 'Xcelys'],
            'aliases': {
                'amysis':   'Amisys',
                'amysys':   'Amisys',
                'amisyss':  'Amisys',
                'fecets':   'Facets',
                'facet':    'Facets',
                'xceles':   'Xcelys',
                'xcelys':   'Xcelys',
                'xcylys':   'Xcelys',
            },
        },
        'localities': {
            'canonical': ['Domestic', 'Global'],
            'aliases': {
                'domestic': 'Domestic',
                'dom':      'Domestic',
                'onshore':  'Domestic',
                'global':   'Global',
                'gbl':      'Global',
                'offshore': 'Global',
            },
        },
        'case_types': {
            'canonical': ['Claims Processing', 'Enrollment', 'Appeals', 'Adjustments'],
            'aliases': {
                'claims':            'Claims Processing',
                'claim processing':  'Claims Processing',
                'claims proc':       'Claims Processing',
                'enroll':            'Enrollment',
                'enrollments':       'Enrollment',
                'appeal':            'Appeals',
                'adjustment':        'Adjustments',
            },
        },
    }

    # ------------------------------------------------------------------
    # US state reference data
    # ------------------------------------------------------------------
    US_STATES: Dict[str, str] = {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
        'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
        'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
        'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
        'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
        'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
        'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
        'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
        'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
        'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
        'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC',
    }
    VALID_STATE_CODES: set = set(US_STATES.values()) | {'N/A'}
    # ME, IN, OR, OK are common English words — require state-context to match
    AMBIGUOUS_STATE_CODES: set = {'ME', 'IN', 'OR', 'OK'}

    # ------------------------------------------------------------------
    # Month reference
    # ------------------------------------------------------------------
    MONTH_NAMES: Dict[str, int] = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9,
        'oct': 10, 'nov': 11, 'dec': 12,
    }

    # ------------------------------------------------------------------
    # Regex entity patterns (markets removed)
    # ------------------------------------------------------------------
    ENTITY_PATTERNS: Dict[str, List[str]] = {
        'month': [
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b(jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b',
        ],
        'year': [
            r'\b(20\d{2})\b',
        ],
        'state_full': [
            r'\b(california|texas|florida|new york|ohio|illinois|pennsylvania|'
            r'georgia|north carolina|michigan|new jersey|virginia|washington|'
            r'arizona|massachusetts|tennessee|indiana|missouri|maryland|wisconsin|'
            r'colorado|minnesota|south carolina|alabama|louisiana|kentucky|oregon|'
            r'oklahoma|connecticut|utah|iowa|nevada|arkansas|mississippi|kansas|'
            r'new mexico|nebraska|idaho|west virginia|hawaii|new hampshire|maine|'
            r'montana|rhode island|delaware|south dakota|north dakota|alaska|'
            r'vermont|wyoming|district of columbia)\b',
        ],
        'state_code': [
            # Non-ambiguous codes (excludes ME, IN, OR, OK)
            r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IA|KS|KY|LA|MD|MA|MI|MN|MS|'
            r'MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b',
        ],
        'state_code_contextual': [
            # Ambiguous codes only when a state-related preposition or keyword precedes them
            r'\b(?:for|from|in|state[s]?)\s+(ME|IN|OR|OK)\b',
            # After another unambiguous state code in a list
            r'\b(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IA|KS|KY|LA|MD|MA|MI|MN|MS|'
            r'MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)'
            r'[,\s]+(?:and\s+)?(ME|IN|OR|OK)\b',
            # Before another unambiguous state code
            r'\b(ME|IN|OR|OK)[,\s]+(?:and\s+)?(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IA|'
            r'KS|KY|LA|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|PA|RI|SC|SD|TN|TX|'
            r'UT|VT|VA|WA|WV|WI|WY|DC)\b',
        ],
        'platform': [
            r'\b(amisys|facets|xcelys)\b',
            r'\b(amysis|fecets|xceles)\b',   # common misspellings caught pre-correction
        ],
        'locality': [
            r'\b(domestic|global)\b',
        ],
        'case_type': [
            r'\b(claims?\s*processing|enrollment|appeals?|adjustments?)\b',
        ],
        'main_lob': [
            # Full three-part LOB string: Platform Market Locality
            r'\b(amisys|facets|xcelys)\s+\w+\s+(domestic|global)\b',
        ],
        'forecast_month_filter': [
            r'\b(apr|may|jun|jul|aug|sep|oct|nov|dec|jan|feb|mar)-\d{2}\b',
        ],
        'preference': [
            r'\b(totals?\s*only|just\s*totals?|summary\s*only)\b',
            r'\b(full\s*data|all\s*records?|detailed?)\b',
            r'\b(all\s*months?|every\s*month)\b',
        ],
    }

    # ------------------------------------------------------------------
    # Intent patterns (regex-based fallback)
    # ------------------------------------------------------------------
    INTENT_PATTERNS: Dict[str, List[str]] = {
        'reset_filters': [
            r'\b(reset|clear all|remove all|no filters|start fresh|forget everything|'
            r'show everything|show all data|full data reset)\b',
        ],
        'extend_filters': [
            r'\b(also|add|include|plus\b|and also)\b',
        ],
        'remove_filters': [
            r'\b(remove|exclude|without|except)\b',
        ],
        'replace_filters': [
            r'\b(change|switch|use only|just show|only show)\b',
        ],
        'use_context': [
            r'\b(same|that|those|previous|last time|again|keep|like before)\b',
            r'\bfor (that|the same)\b',
        ],
        'query_data': [
            r'\b(show|get|display|fetch|give me|what|how many|list)\b',
        ],
    }

    # Priority order for intent resolution (higher index = higher priority)
    INTENT_PRIORITY: List[str] = [
        'query_data', 'use_context', 'replace_filters',
        'remove_filters', 'extend_filters', 'reset_filters',
    ]

    def __init__(self, llm=None) -> None:
        self.llm = llm
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        self._entity_compiled: Dict[str, List[re.Pattern]] = {
            etype: [re.compile(p, re.IGNORECASE) for p in plist]
            for etype, plist in self.ENTITY_PATTERNS.items()
        }
        self._intent_compiled: Dict[str, List[re.Pattern]] = {
            intent: [re.compile(p, re.IGNORECASE) for p in plist]
            for intent, plist in self.INTENT_PATTERNS.items()
        }

    # ==================================================================
    # PUBLIC API
    # ==================================================================

    async def preprocess(self, raw_message: str, context=None) -> PreprocessedMessage:
        """
        Full preprocessing pipeline.

        Args:
            raw_message: Raw user input (after sanitization).
            context:     Optional ConversationContext with stored entities
                         used to craft the resolved message.

        Returns:
            PreprocessedMessage with intent, entities, and resolved_message.
        """
        logger.debug(f"[Preprocessor] Input: '{raw_message[:80]}'")

        # Step 1 — Normalize
        text = self._normalize(raw_message)

        # Step 2 — Spell-correct (no market corrections)
        text, corrections = self._spell_correct(text)

        # Step 3 — Detect intent  (LLM-assisted or regex)
        # Step 4 — Extract entities  (LLM-assisted or regex)
        if self.llm:
            try:
                intent, tagged_text, llm_entities = await self._llm_intent_and_entities(text)
            except Exception as exc:
                logger.warning(f"[Preprocessor] LLM call failed ({exc}), using regex fallback")
                intent = self._detect_intent_regex(text)
                tagged_text = text
                llm_entities = {}
        else:
            intent = self._detect_intent_regex(text)
            tagged_text = text
            llm_entities = {}

        # Regex extraction (fills gaps left by LLM or provides all results without LLM)
        regex_entities = self._extract_with_regex(text)

        # Step 5 — Merge (LLM takes precedence) + validate
        merged = self._merge_entities(llm_entities, regex_entities)
        validated_entities = self._validate_entities(merged)

        # Step 6 — Detect implicit info (context references, operation hints)
        implicit_info = self._detect_implicit_info(text, validated_entities)

        # Step 7 — Craft resolved message
        resolved_message = self._craft_resolved_message(intent, validated_entities, context)

        # Step 8 — Confidence score
        confidence = self._calculate_confidence(validated_entities)

        logger.info(
            f"[Preprocessor] intent={intent}, entities={list(validated_entities.keys())}, "
            f"confidence={confidence:.2f}"
        )

        return PreprocessedMessage(
            original=raw_message,
            normalized_text=text,
            tagged_text=tagged_text,
            intent=intent,
            resolved_message=resolved_message,
            extracted_entities=validated_entities,
            corrections_made=corrections,
            parsing_confidence=confidence,
            implicit_info=implicit_info,
        )

    # ==================================================================
    # STEP 1 — NORMALIZE
    # ==================================================================

    def _normalize(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\s*,\s*', ', ', text)
        text = re.sub(r'\s*\?\s*$', '?', text)
        return text

    # ==================================================================
    # STEP 2 — SPELL CORRECT (platforms, localities, case types only)
    # ==================================================================

    def _spell_correct(self, text: str) -> Tuple[str, List[Dict[str, str]]]:
        corrections: List[Dict[str, str]] = []
        corrected_words: List[str] = []

        for word in text.split():
            word_lower = word.lower().strip('.,?!')
            corrected = word

            for category, vocab in self.DOMAIN_VOCABULARY.items():
                # Exact alias match
                if word_lower in vocab.get('aliases', {}):
                    corrected = vocab['aliases'][word_lower]
                    corrections.append({'original': word, 'corrected': corrected, 'category': category})
                    break

                # Fuzzy match against canonical values
                for canonical in vocab.get('canonical', []):
                    if self._fuzzy_match(word_lower, canonical.lower()) > 0.85:
                        if word_lower != canonical.lower():
                            corrected = canonical
                            corrections.append({
                                'original': word, 'corrected': corrected,
                                'category': category, 'match_type': 'fuzzy',
                            })
                        break

            corrected_words.append(corrected)

        return ' '.join(corrected_words), corrections

    def _fuzzy_match(self, s1: str, s2: str) -> float:
        return SequenceMatcher(None, s1, s2).ratio()

    # ==================================================================
    # STEP 3+4 — LLM: combined intent + entity tagging (one call)
    # ==================================================================

    async def _llm_intent_and_entities(
        self, text: str
    ) -> Tuple[str, str, Dict[str, List[str]]]:
        """
        Single LLM call that returns:
          - the primary user intent
          - the message with XML entity tags
        """
        prompt = f'''Analyze this message in two steps.

Message: "{text}"

STEP 1 — INTENT
Choose the single best intent:
  query_data      — user wants to fetch / view forecast data
  extend_filters  — user wants to ADD filters (keywords: also, add, include, plus)
  remove_filters  — user wants to REMOVE filters (keywords: remove, without, exclude)
  replace_filters — user wants to CHANGE existing filters (keywords: change, switch, only, just)
  reset_filters   — user wants to clear all filters (keywords: reset, clear all, show everything)
  use_context     — user refers to a previous query (keywords: same, that, again, previous)
  unknown         — intent is unclear

STEP 2 — TAG ENTITIES
Wrap recognised values with XML tags.  DO NOT tag market names individually.

Available tags:
  <platform>   Amisys | Facets | Xcelys
  <year>       4-digit year (2020-2030)
  <month>      Month name or abbreviation
  <state>      US state name or 2-letter code
  <locality>   Domestic | Global
  <case_type>  Claims Processing | Enrollment | Appeals | Adjustments
  <main_lob>   Full LOB phrase e.g. "Amisys Medicaid Domestic"
  <forecast_month>  Column label e.g. Apr-25, May-25
  <preference> Display preference e.g. "totals only", "full data"

IMPORTANT:
- Do NOT tag market names (Medicaid, Medicare, Marketplace) on their own.
- If a full LOB phrase is present (Platform + Market + Locality), tag it as <main_lob>.
- Only tag clear, unambiguous values.

Return exactly two lines:
INTENT: <intent_keyword>
TAGGED: <message with XML tags>
'''
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        intent = 'unknown'
        tagged_text = text
        for line in raw.splitlines():
            if line.startswith('INTENT:'):
                intent = line.split(':', 1)[1].strip().lower()
            elif line.startswith('TAGGED:'):
                tagged_text = line.split(':', 1)[1].strip()

        # Validate extracted intent
        valid_intents = set(_INTENT_LABELS.keys())
        if intent not in valid_intents:
            intent = 'unknown'

        entities = self._parse_xml_tags(tagged_text)
        return intent, tagged_text, entities

    def _parse_xml_tags(self, tagged_text: str) -> Dict[str, List[str]]:
        tag_patterns = [
            ('month',            r'<month>([^<]+)</month>'),
            ('year',             r'<year>([^<]+)</year>'),
            ('platform',         r'<platform>([^<]+)</platform>'),
            ('state',            r'<state>([^<]+)</state>'),
            ('locality',         r'<locality>([^<]+)</locality>'),
            ('main_lob',         r'<main_lob>([^<]+)</main_lob>'),
            ('case_type',        r'<case_type>([^<]+)</case_type>'),
            ('forecast_month',   r'<forecast_month>([^<]+)</forecast_month>'),
            ('preference',       r'<preference>([^<]+)</preference>'),
        ]
        entities: Dict[str, List[str]] = {}
        for etype, pattern in tag_patterns:
            matches = re.findall(pattern, tagged_text, re.IGNORECASE)
            if matches:
                entities[etype] = [m.strip() for m in matches]
        return entities

    # ==================================================================
    # STEP 3 (regex fallback) — DETECT INTENT
    # ==================================================================

    def _detect_intent_regex(self, text: str) -> str:
        """
        Rule-based intent detection.
        Higher-priority intents in INTENT_PRIORITY override lower ones.
        """
        detected = 'unknown'
        for intent in self.INTENT_PRIORITY:
            patterns = self._intent_compiled.get(intent, [])
            if any(p.search(text) for p in patterns):
                detected = intent
        return detected

    # ==================================================================
    # STEP 4 (regex fallback) — EXTRACT ENTITIES
    # ==================================================================

    def _extract_with_regex(self, text: str) -> Dict[str, List[str]]:
        entities: Dict[str, List[str]] = {}
        text_lower = text.lower()

        for etype, patterns in self._entity_compiled.items():
            matches: List[str] = []
            for pattern in patterns:
                found = pattern.findall(text_lower)
                if found:
                    matches.extend(found if isinstance(found[0], str) else [f[0] for f in found])
            if matches:
                entities[etype] = list(set(matches))
        return entities

    # ==================================================================
    # STEP 5 — MERGE + VALIDATE
    # ==================================================================

    def _merge_entities(
        self,
        llm_entities: Dict[str, List[str]],
        regex_entities: Dict[str, List[str]],
    ) -> Dict[str, List[str]]:
        merged = dict(llm_entities)
        for etype, values in regex_entities.items():
            if etype not in merged or not merged[etype]:
                merged[etype] = values
            else:
                existing_lower = {v.lower() for v in merged[etype]}
                for v in values:
                    if v.lower() not in existing_lower:
                        merged[etype].append(v)
        return merged

    def _validate_entities(self, entities: Dict[str, List[str]]) -> Dict[str, List[str]]:
        validated: Dict[str, List[str]] = {}

        # Month → integer string
        if entities.get('month'):
            month_val = self._normalise_month(entities['month'][0])
            if month_val:
                validated['month'] = [str(month_val)]

        # Year
        if entities.get('year'):
            year_val = self._normalise_year(entities['year'][0])
            if year_val:
                validated['year'] = [str(year_val)]

        # Platforms
        if entities.get('platform'):
            validated['platforms'] = self._validate_against_vocab(entities['platform'], 'platforms')

        # Localities
        if entities.get('locality'):
            validated['localities'] = self._validate_against_vocab(entities['locality'], 'localities')

        # States (merge all state-related keys)
        state_pool: List[str] = []
        for key in ('state', 'state_full', 'state_code', 'state_code_contextual'):
            if entities.get(key):
                state_pool.extend(entities[key])
        if state_pool:
            validated['states'] = list(set(self._validate_states(state_pool)))

        # Case types
        if entities.get('case_type'):
            validated['case_types'] = self._validate_against_vocab(entities['case_type'], 'case_types')

        # Main LOBs
        if entities.get('main_lob'):
            validated['main_lobs'] = [lob.title() for lob in entities['main_lob']]

        # Forecast month filters (Apr-25 format)
        forecast_month_pool: List[str] = []
        for key in ('forecast_month_filter', 'forecast_month'):
            if entities.get(key):
                forecast_month_pool.extend(entities[key])
        if forecast_month_pool:
            validated['active_forecast_months'] = self._validate_forecast_months(forecast_month_pool)

        # Preferences
        if entities.get('preference'):
            for pref in entities['preference']:
                pref_lower = pref.lower()
                if any(t in pref_lower for t in ['total', 'summary']):
                    validated['show_totals_only'] = [True]
                elif any(t in pref_lower for t in ['full', 'all records', 'detail']):
                    validated['show_totals_only'] = [False]

        return validated

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _normalise_month(self, month_str: str) -> Optional[int]:
        month_str = month_str.lower().strip()
        if month_str in self.MONTH_NAMES:
            return self.MONTH_NAMES[month_str]
        try:
            v = int(month_str)
            if 1 <= v <= 12:
                return v
        except ValueError:
            pass
        return None

    def _normalise_year(self, year_str: str) -> Optional[int]:
        try:
            y = int(year_str.strip())
            if 2020 <= y <= 2100:
                return y
        except ValueError:
            pass
        return None

    def _validate_against_vocab(self, values: List[str], vocab_key: str) -> List[str]:
        vocab = self.DOMAIN_VOCABULARY.get(vocab_key, {})
        canonical = vocab.get('canonical', [])
        aliases = vocab.get('aliases', {})
        out: List[str] = []
        for v in values:
            v_lower = v.lower().strip()
            if v_lower in aliases:
                out.append(aliases[v_lower])
                continue
            for c in canonical:
                if v_lower == c.lower():
                    out.append(c)
                    break
            else:
                out.append(v.title())
        return list(set(out))

    def _validate_states(self, states: List[str]) -> List[str]:
        validated: List[str] = []
        for s in states:
            s_clean = s.strip()
            s_lower = s_clean.lower()
            if s_lower in self.US_STATES:
                validated.append(self.US_STATES[s_lower])
            elif s_clean.upper() in self.VALID_STATE_CODES:
                validated.append(s_clean.upper())
        return list(set(validated))

    def _validate_forecast_months(self, months: List[str]) -> List[str]:
        pattern = re.compile(r'^([A-Za-z]{3})-(\d{2})$')
        validated: List[str] = []
        for m in months:
            match = pattern.match(m.strip())
            if match:
                validated.append(f"{match.group(1).title()}-{match.group(2)}")
        return list(set(validated))

    # ==================================================================
    # STEP 6 — DETECT IMPLICIT INFO
    # ==================================================================

    def _detect_implicit_info(
        self, text: str, entities: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        implicit: Dict[str, Any] = {}
        text_lower = text.lower()

        context_patterns = [
            r'\b(same|that|those|previous|last|again|keep)\b',
            r'\bfor (that|the same)\b',
            r'\blike (before|last time)\b',
        ]
        if any(re.search(p, text_lower) for p in context_patterns):
            implicit['uses_previous_context'] = True

        if re.search(r'\b(also|add|include|plus|and also|too)\b', text_lower):
            implicit['operation'] = 'extend'

        if re.search(r'\b(remove|clear|reset|without|exclude|except)\b', text_lower):
            implicit['operation'] = 'remove'

        if re.search(r'\b(change|switch|use|only|just)\b', text_lower):
            if 'operation' not in implicit:
                implicit['operation'] = 'replace'

        if re.search(r'\b(all\s*months?|every\s*month|all\s*data|full\s*data|reset)\b', text_lower):
            implicit['reset_filter'] = True

        return implicit

    # ==================================================================
    # STEP 7 — CRAFT RESOLVED MESSAGE
    # ==================================================================

    def _craft_resolved_message(
        self,
        intent: str,
        entities: Dict[str, List[str]],
        context=None,
    ) -> str:
        """
        Combine intent + entities from message + stored context entities
        into one clear, unambiguous directive.

        This replaces the raw user message as input to LLM tool classification.
        """
        # --- Effective time period (message entities take precedence over context) ---
        month_num = entities.get('month', [None])[0]
        year_num  = entities.get('year',  [None])[0]

        if not month_num and context:
            ctx_month = getattr(context, 'forecast_report_month', None)
            if ctx_month:
                month_num = str(ctx_month)
        if not year_num and context:
            ctx_year = getattr(context, 'forecast_report_year', None)
            if ctx_year:
                year_num = str(ctx_year)

        # --- Effective filters ---
        msg_platforms  = entities.get('platforms', [])
        msg_localities = entities.get('localities', [])
        msg_states     = entities.get('states', [])
        msg_case_types = entities.get('case_types', [])
        msg_main_lobs  = entities.get('main_lobs', [])
        msg_f_months   = entities.get('active_forecast_months')
        totals_only    = (entities.get('show_totals_only') or [None])[0]

        ctx_platforms  = list(getattr(context, 'active_platforms',  []) or []) if context else []
        ctx_localities = list(getattr(context, 'active_localities', []) or []) if context else []
        ctx_states     = list(getattr(context, 'active_states',     []) or []) if context else []
        ctx_case_types = list(getattr(context, 'active_case_types', []) or []) if context else []
        ctx_main_lobs  = list(getattr(context, 'active_main_lobs',  []) or []) if context else []

        if intent == 'extend_filters':
            platforms  = list(set(ctx_platforms  + msg_platforms))
            localities = list(set(ctx_localities + msg_localities))
            states     = list(set(ctx_states     + msg_states))
            case_types = list(set(ctx_case_types + msg_case_types))
            main_lobs  = list(set(ctx_main_lobs  + msg_main_lobs))

        elif intent == 'remove_filters':
            platforms  = [p for p in ctx_platforms  if p not in msg_platforms]
            localities = [l for l in ctx_localities if l not in msg_localities]
            states     = [s for s in ctx_states     if s not in msg_states]
            case_types = [c for c in ctx_case_types if c not in msg_case_types]
            main_lobs  = [l for l in ctx_main_lobs  if l not in msg_main_lobs]

        elif intent == 'reset_filters':
            platforms = localities = states = case_types = main_lobs = []

        elif intent in ('query_data', 'use_context'):
            # Message entities override; fall back to context for anything not mentioned
            platforms  = msg_platforms  or ctx_platforms
            localities = msg_localities or ctx_localities
            states     = msg_states     or ctx_states
            case_types = msg_case_types or ctx_case_types
            main_lobs  = msg_main_lobs  or ctx_main_lobs

        else:
            # replace_filters / unknown — use only what the message says
            platforms  = msg_platforms
            localities = msg_localities
            states     = msg_states
            case_types = msg_case_types
            main_lobs  = msg_main_lobs

        # --- Assemble the directive ---
        intent_phrase = _INTENT_LABELS.get(intent, 'Show data')
        parts = [intent_phrase]

        if month_num and year_num:
            parts.append(f"for {calendar.month_name[int(month_num)]} {year_num}")
        elif month_num:
            parts.append(f"for {calendar.month_name[int(month_num)]}")
        elif year_num:
            parts.append(f"for year {year_num}")

        filter_parts: List[str] = []
        if main_lobs:
            filter_parts.append(f"LOB: {', '.join(main_lobs)}")
        else:
            if platforms:
                filter_parts.append(f"Platform: {', '.join(platforms)}")
            if localities:
                filter_parts.append(f"Locality: {', '.join(localities)}")
        if states:
            filter_parts.append(f"States: {', '.join(states[:10])}")
        if case_types:
            filter_parts.append(f"Case Type: {', '.join(case_types)}")
        if msg_f_months:
            filter_parts.append(f"Forecast Months: {', '.join(msg_f_months)}")
        if totals_only is True:
            filter_parts.append("Display: Totals Only")
        elif totals_only is False:
            filter_parts.append("Display: All Records")

        if filter_parts:
            parts.append("| " + " | ".join(filter_parts))

        return " ".join(parts)

    # ==================================================================
    # STEP 8 — CONFIDENCE SCORE
    # ==================================================================

    def _calculate_confidence(self, entities: Dict[str, List[str]]) -> float:
        has_month  = bool(entities.get('month'))
        has_year   = bool(entities.get('year'))
        has_filter = any(
            entities.get(k)
            for k in ('platforms', 'localities', 'states', 'case_types', 'main_lobs')
        )

        if has_month and has_year:
            return 0.95 if has_filter else 0.85
        if has_month or has_year:
            return 0.70
        if has_filter:
            return 0.60
        return 0.40


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_preprocessor: Optional[MessagePreprocessor] = None


def get_preprocessor(llm=None) -> MessagePreprocessor:
    global _preprocessor
    if _preprocessor is None or (llm is not None and _preprocessor.llm is None):
        _preprocessor = MessagePreprocessor(llm=llm)
    return _preprocessor
