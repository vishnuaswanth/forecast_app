"""
Message Preprocessor Service

Preprocesses user messages for clarity and entity tagging.
Pipeline: Normalize -> Spell Correct -> Sentence Correct -> XML Entity Tag

This module handles:
1. Text normalization (casing, spacing, punctuation)
2. Spell correction using domain-specific vocabulary
3. XML entity tagging for easy parsing
4. Robust multi-pass entity extraction
"""
import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from difflib import SequenceMatcher

from langchain_core.messages import HumanMessage
from chat_app.services.tools.validation import PreprocessedMessage

logger = logging.getLogger(__name__)


class MessagePreprocessor:
    """
    Preprocesses user messages for clarity and entity tagging.

    Handles normalization, spell correction, and XML entity tagging
    to ensure entities are reliably extracted from user input.
    """

    # Domain-specific vocabulary for spell correction
    # NOTE: Only validate fixed lists. Markets have many values - don't restrict.
    DOMAIN_VOCABULARY = {
        'platforms': {
            'canonical': ['Amisys', 'Facets', 'Xcelys'],
            'aliases': {
                'amysis': 'Amisys',
                'amysys': 'Amisys',
                'amisyss': 'Amisys',
                'fecets': 'Facets',
                'facet': 'Facets',
                'xceles': 'Xcelys',
                'xcelys': 'Xcelys',
                'xcylys': 'Xcelys',
            }
        },
        'markets': {
            'canonical': ['Medicaid', 'Medicare', 'Marketplace'],
            'aliases': {
                'medcaid': 'Medicaid',
                'medicad': 'Medicaid',
                'medicaide': 'Medicaid',
                'medicaire': 'Medicare',
                'medicair': 'Medicare',
                'market place': 'Marketplace',
                'market-place': 'Marketplace',
            }
        },
        'localities': {
            'canonical': ['Domestic', 'Global'],
            'aliases': {
                'domestic': 'Domestic',
                'dom': 'Domestic',
                'global': 'Global',
                'gbl': 'Global',
                'offshore': 'Global',
                'onshore': 'Domestic',
            }
        },
        'case_types': {
            'canonical': ['Claims Processing', 'Enrollment', 'Appeals', 'Adjustments'],
            'aliases': {
                'claims': 'Claims Processing',
                'claim processing': 'Claims Processing',
                'claims proc': 'Claims Processing',
                'enroll': 'Enrollment',
                'enrollments': 'Enrollment',
                'appeal': 'Appeals',
                'adjustment': 'Adjustments',
            }
        }
    }

    # US State codes and names
    US_STATES = {
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
    VALID_STATE_CODES = set(US_STATES.values()) | {'N/A'}

    # Month mappings
    MONTH_NAMES = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9,
        'oct': 10, 'nov': 11, 'dec': 12,
    }

    # Comprehensive entity patterns for fallback parsing
    ENTITY_PATTERNS = {
        'month': [
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b(jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b',
        ],
        'year': [
            r'\b(20\d{2})\b',  # 2020-2099
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
            r'\b([A-Z]{2})\b',  # Two-letter codes
        ],
        'platform': [
            r'\b(amisys|facets|xcelys)\b',
            r'\b(amysis|fecets|xceles)\b',  # Common misspellings
        ],
        'market': [
            r'\b(medicaid|medicare|marketplace)\b',
            r'\b(medcaid|medicad|medicaire)\b',  # Common misspellings
        ],
        'locality': [
            r'\b(domestic|global)\b',
        ],
        'case_type': [
            r'\b(claims?\s*processing|enrollment|appeals?|adjustments?)\b',
        ],
        'main_lob': [
            # Full LOB strings like "Amisys Medicaid Domestic"
            r'\b(amisys|facets|xcelys)\s+(medicaid|medicare|marketplace)\s+(domestic|global)\b',
        ],
        'forecast_month_filter': [
            r'\b(apr|may|jun|jul|aug|sep|oct|nov|dec|jan|feb|mar)-\d{2}\b',  # Apr-25 format
        ],
        'preference': [
            r'\b(totals?\s*only|just\s*totals?|summary\s*only)\b',
            r'\b(full\s*data|all\s*records?|detailed?)\b',
            r'\b(all\s*months?|every\s*month)\b',
        ],
    }

    def __init__(self, llm=None):
        """
        Initialize preprocessor.

        Args:
            llm: Optional LangChain LLM for advanced tagging. If None, uses regex only.
        """
        self.llm = llm
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self.compiled_patterns = {}
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            self.compiled_patterns[entity_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    async def preprocess(self, raw_message: str) -> PreprocessedMessage:
        """
        Full preprocessing pipeline.

        Args:
            raw_message: Raw user input

        Returns:
            PreprocessedMessage with normalized text, tagged text, and extracted entities
        """
        logger.debug(f"[Preprocessor] Starting preprocessing: '{raw_message[:50]}...'")

        # Step 1: Basic normalization
        text = self._normalize(raw_message)

        # Step 2: Spell correction (domain-aware)
        text, corrections = self._spell_correct(text)

        # Step 3: Entity tagging with XML (LLM or regex)
        if self.llm:
            try:
                tagged_text, llm_entities = await self._tag_entities_with_llm(text)
            except Exception as e:
                logger.warning(f"[Preprocessor] LLM tagging failed: {e}, using regex fallback")
                tagged_text = text
                llm_entities = {}
        else:
            tagged_text = text
            llm_entities = {}

        # Step 4: Regex fallback extraction (catches what LLM might miss)
        regex_entities = self._extract_with_regex(text)

        # Step 5: Merge entities (LLM + regex, LLM takes precedence)
        merged_entities = self._merge_entities(llm_entities, regex_entities)

        # Step 6: Validate and normalize entities
        validated_entities = self._validate_entities(merged_entities)

        # Step 7: Detect implicit information
        implicit_info = self._detect_implicit_info(text, validated_entities)

        # Step 8: Calculate confidence
        confidence = self._calculate_confidence(validated_entities)

        result = PreprocessedMessage(
            original=raw_message,
            normalized_text=text,
            tagged_text=tagged_text,
            extracted_entities=validated_entities,
            corrections_made=corrections,
            parsing_confidence=confidence,
            implicit_info=implicit_info
        )

        logger.info(
            f"[Preprocessor] Extracted entities: {list(validated_entities.keys())}, "
            f"confidence: {confidence:.2f}"
        )

        return result

    def _normalize(self, text: str) -> str:
        """
        Basic text normalization.

        - Fix extra whitespace
        - Normalize punctuation
        - Preserve case (will be handled by spell correction)
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Normalize some common punctuation issues
        text = re.sub(r'\s*,\s*', ', ', text)
        text = re.sub(r'\s*\?\s*', '? ', text)

        return text

    def _spell_correct(self, text: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        Domain-aware spell correction.

        Corrects common misspellings of domain vocabulary.
        """
        corrections = []
        words = text.split()
        corrected_words = []

        for word in words:
            word_lower = word.lower().strip('.,?!')
            corrected = word

            # Check each vocabulary category
            for category, vocab in self.DOMAIN_VOCABULARY.items():
                # Check aliases first
                if word_lower in vocab.get('aliases', {}):
                    corrected = vocab['aliases'][word_lower]
                    corrections.append({
                        'original': word,
                        'corrected': corrected,
                        'category': category
                    })
                    break

                # Check for fuzzy match to canonical values
                for canonical in vocab.get('canonical', []):
                    if self._fuzzy_match(word_lower, canonical.lower()) > 0.85:
                        if word_lower != canonical.lower():
                            corrected = canonical
                            corrections.append({
                                'original': word,
                                'corrected': corrected,
                                'category': category,
                                'match_type': 'fuzzy'
                            })
                        break

            corrected_words.append(corrected)

        return ' '.join(corrected_words), corrections

    def _fuzzy_match(self, s1: str, s2: str) -> float:
        """Calculate fuzzy match ratio between two strings."""
        return SequenceMatcher(None, s1, s2).ratio()

    async def _tag_entities_with_llm(self, text: str) -> Tuple[str, Dict[str, List[str]]]:
        """
        Tag entities with XML tags using LLM.

        Uses LLM with structured output to identify and tag:
        - <month>March</month>
        - <year>2025</year>
        - <platform>Amisys</platform>
        - etc.
        """
        tagging_prompt = f'''Tag entities in this message with XML tags:

Message: "{text}"

Entity types to tag:
- <month>: Month names (January-December) or abbreviations (Jan-Dec)
- <year>: Year numbers (2020-2030)
- <platform>: Amisys, Facets, Xcelys
- <market>: Insurance market segments (Medicaid, Medicare, Marketplace, etc.)
- <state>: US state names or codes (California/CA, Texas/TX, etc.)
- <locality>: Domestic, Global
- <main_lob>: Full LOB string like "Amisys Medicaid Domestic" (platform + market + locality combined)
- <case_type>: Claims Processing, Enrollment, Appeals, Adjustments, etc.
- <forecast_month>: Specific month columns like Apr-25, May-25, Jun-25
- <preference>: User preferences like "totals only", "full data", "all months"

IMPORTANT:
- If user mentions "Amisys Medicaid Domestic" as a single phrase, tag as <main_lob>
- If mentioned separately (e.g., "Amisys" and "Medicaid"), tag individually as <platform> and <market>
- <main_lob> takes precedence and overrides individual platform/market/locality

Return the message with XML tags added around identified entities.
Do NOT tag words that are not clear entities.
'''

        response = await self.llm.ainvoke([HumanMessage(content=tagging_prompt)])
        tagged_text = response.content.strip()

        # Parse tagged text to extract entities
        entities = self._parse_xml_tags(tagged_text)

        return tagged_text, entities

    def _parse_xml_tags(self, tagged_text: str) -> Dict[str, List[str]]:
        """Parse XML tags from tagged text to extract entities."""
        entities = {}

        tag_patterns = [
            ('month', r'<month>([^<]+)</month>'),
            ('year', r'<year>([^<]+)</year>'),
            ('platform', r'<platform>([^<]+)</platform>'),
            ('market', r'<market>([^<]+)</market>'),
            ('state', r'<state>([^<]+)</state>'),
            ('locality', r'<locality>([^<]+)</locality>'),
            ('main_lob', r'<main_lob>([^<]+)</main_lob>'),
            ('case_type', r'<case_type>([^<]+)</case_type>'),
            ('forecast_month', r'<forecast_month>([^<]+)</forecast_month>'),
            ('preference', r'<preference>([^<]+)</preference>'),
        ]

        for entity_type, pattern in tag_patterns:
            matches = re.findall(pattern, tagged_text, re.IGNORECASE)
            if matches:
                entities[entity_type] = [m.strip() for m in matches]

        return entities

    def _extract_with_regex(self, text: str) -> Dict[str, List[str]]:
        """
        Fallback regex extraction to catch entities LLM might miss.
        """
        entities = {}
        text_lower = text.lower()

        for entity_type, patterns in self.compiled_patterns.items():
            matches = []
            for pattern in patterns:
                found = pattern.findall(text_lower)
                if isinstance(found, list) and found:
                    matches.extend(found if isinstance(found[0], str) else [f[0] for f in found])
            if matches:
                entities[entity_type] = list(set(matches))

        return entities

    def _merge_entities(
        self,
        llm_entities: Dict[str, List[str]],
        regex_entities: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Merge LLM and regex extracted entities.

        LLM entities take precedence, regex fills gaps.
        """
        merged = dict(llm_entities)

        for entity_type, values in regex_entities.items():
            if entity_type not in merged or not merged[entity_type]:
                merged[entity_type] = values
            else:
                # Add any values from regex not in LLM results
                existing_lower = {v.lower() for v in merged[entity_type]}
                for v in values:
                    if v.lower() not in existing_lower:
                        merged[entity_type].append(v)

        return merged

    def _validate_entities(self, entities: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Validate and normalize extracted entities.
        """
        validated = {}

        # Validate month
        if 'month' in entities and entities['month']:
            month_val = self._normalize_month(entities['month'][0])
            if month_val:
                validated['month'] = [str(month_val)]

        # Validate year
        if 'year' in entities and entities['year']:
            year_val = self._normalize_year(entities['year'][0])
            if year_val:
                validated['year'] = [str(year_val)]

        # Validate platforms against known list
        if 'platform' in entities and entities['platform']:
            validated['platforms'] = self._validate_against_vocabulary(
                entities['platform'],
                'platforms'
            )

        # Validate markets (be more permissive, just capitalize)
        if 'market' in entities and entities['market']:
            validated['markets'] = [m.title() for m in entities['market']]

        # Validate localities
        if 'locality' in entities and entities['locality']:
            validated['localities'] = self._validate_against_vocabulary(
                entities['locality'],
                'localities'
            )

        # Validate states
        if 'state' in entities and entities['state']:
            validated['states'] = self._validate_states(entities['state'])
        if 'state_full' in entities and entities['state_full']:
            state_codes = self._validate_states(entities['state_full'])
            if 'states' in validated:
                validated['states'].extend(state_codes)
            else:
                validated['states'] = state_codes
        if 'state_code' in entities and entities['state_code']:
            state_codes = self._validate_states(entities['state_code'])
            if 'states' in validated:
                validated['states'].extend(state_codes)
            else:
                validated['states'] = state_codes

        # Remove duplicates from states
        if 'states' in validated:
            validated['states'] = list(set(validated['states']))

        # Validate case types
        if 'case_type' in entities and entities['case_type']:
            validated['case_types'] = self._validate_against_vocabulary(
                entities['case_type'],
                'case_types'
            )

        # Validate main LOBs (just title case)
        if 'main_lob' in entities and entities['main_lob']:
            validated['main_lobs'] = [lob.title() for lob in entities['main_lob']]

        # Validate forecast month filters (Apr-25 format)
        if 'forecast_month_filter' in entities and entities['forecast_month_filter']:
            validated['active_forecast_months'] = self._validate_forecast_months(
                entities['forecast_month_filter']
            )
        if 'forecast_month' in entities and entities['forecast_month']:
            forecast_months = self._validate_forecast_months(entities['forecast_month'])
            if 'active_forecast_months' in validated:
                validated['active_forecast_months'].extend(forecast_months)
            else:
                validated['active_forecast_months'] = forecast_months

        # Handle preferences
        if 'preference' in entities and entities['preference']:
            for pref in entities['preference']:
                pref_lower = pref.lower()
                if any(t in pref_lower for t in ['total', 'summary']):
                    validated['show_totals_only'] = [True]
                elif any(t in pref_lower for t in ['full', 'all records', 'detail']):
                    validated['show_totals_only'] = [False]

        return validated

    def _normalize_month(self, month_str: str) -> Optional[int]:
        """Convert month string to number."""
        month_str = month_str.lower().strip()

        # Check month names
        if month_str in self.MONTH_NAMES:
            return self.MONTH_NAMES[month_str]

        # Try parsing as number
        try:
            month_num = int(month_str)
            if 1 <= month_num <= 12:
                return month_num
        except ValueError:
            pass

        return None

    def _normalize_year(self, year_str: str) -> Optional[int]:
        """Validate and normalize year."""
        try:
            year = int(year_str.strip())
            if 2020 <= year <= 2100:
                return year
        except ValueError:
            pass
        return None

    def _validate_against_vocabulary(
        self,
        values: List[str],
        vocabulary_key: str
    ) -> List[str]:
        """Validate values against known vocabulary."""
        vocab = self.DOMAIN_VOCABULARY.get(vocabulary_key, {})
        canonical = vocab.get('canonical', [])
        aliases = vocab.get('aliases', {})

        validated = []
        for v in values:
            v_lower = v.lower().strip()

            # Check aliases
            if v_lower in aliases:
                validated.append(aliases[v_lower])
                continue

            # Check canonical (case-insensitive)
            for c in canonical:
                if v_lower == c.lower():
                    validated.append(c)
                    break
            else:
                # Not found in canonical, use title case
                validated.append(v.title())

        return list(set(validated))

    def _validate_states(self, states: List[str]) -> List[str]:
        """Validate and normalize state names/codes."""
        validated = []

        for state in states:
            state_clean = state.strip()
            state_lower = state_clean.lower()

            # Check if it's a full state name
            if state_lower in self.US_STATES:
                validated.append(self.US_STATES[state_lower])
                continue

            # Check if it's already a valid code
            state_upper = state_clean.upper()
            if state_upper in self.VALID_STATE_CODES:
                validated.append(state_upper)
                continue

        return list(set(validated))

    def _validate_forecast_months(self, months: List[str]) -> List[str]:
        """Validate forecast month format (e.g., 'Apr-25', 'May-25')."""
        validated = []
        pattern = re.compile(r'^([A-Za-z]{3})-(\d{2})$')

        for month in months:
            month_clean = month.strip()
            match = pattern.match(month_clean)
            if match:
                # Capitalize properly: Apr-25
                validated.append(f"{match.group(1).title()}-{match.group(2)}")

        return list(set(validated))

    def _detect_implicit_info(
        self,
        text: str,
        entities: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Detect implicit information that might not be explicit entities.

        Examples:
        - "same as before" -> uses_previous_context = True
        - "also add" -> operation = 'extend'
        - "remove the filter" -> operation = 'remove'
        - "for that report" -> uses_previous_context = True
        """
        implicit = {}
        text_lower = text.lower()

        # Context references
        context_patterns = [
            r'\b(same|that|those|previous|last|again|keep)\b',
            r'\bfor (that|the same)\b',
            r'\blike (before|last time)\b',
        ]
        for pattern in context_patterns:
            if re.search(pattern, text_lower):
                implicit['uses_previous_context'] = True
                break

        # Add/extend operations
        if re.search(r'\b(also|add|include|plus|and also|too)\b', text_lower):
            implicit['operation'] = 'extend'

        # Remove/clear operations
        if re.search(r'\b(remove|clear|reset|without|exclude|except)\b', text_lower):
            implicit['operation'] = 'remove'

        # Replace operations (default)
        if re.search(r'\b(change|switch|use|only|just)\b', text_lower):
            if 'operation' not in implicit:  # Don't override extend/remove
                implicit['operation'] = 'replace'

        # Show all / reset filter
        if re.search(r'\b(all\s*months?|every\s*month|all\s*data|full\s*data|reset)\b', text_lower):
            implicit['reset_filter'] = True

        return implicit

    def _calculate_confidence(self, entities: Dict[str, List[str]]) -> float:
        """
        Calculate parsing confidence based on extracted entities.

        High confidence: month + year + at least one filter
        Medium confidence: month or year
        Low confidence: only filters, no time context
        """
        has_month = 'month' in entities and entities['month']
        has_year = 'year' in entities and entities['year']
        has_filter = any(k in entities and entities[k] for k in
                        ['platforms', 'markets', 'states', 'case_types', 'localities', 'main_lobs'])

        if has_month and has_year:
            return 0.95 if has_filter else 0.85
        elif has_month or has_year:
            return 0.70
        elif has_filter:
            return 0.60
        else:
            return 0.40


# Singleton instance
_preprocessor: Optional[MessagePreprocessor] = None


def get_preprocessor(llm=None) -> MessagePreprocessor:
    """Get or create preprocessor instance."""
    global _preprocessor
    if _preprocessor is None or (llm is not None and _preprocessor.llm is None):
        _preprocessor = MessagePreprocessor(llm=llm)
    return _preprocessor
