"""
Input Sanitizer - Sanitizes user input before LLM processing.

Protects against:
- Prompt injection attacks
- Token abuse (excessive length)
- Control characters
- SQL injection patterns
- HTML/Script injection
- Excessive whitespace

Preserves:
- Numbers, dates, business terms
- Filter values (platform names, market names, etc.)
- Legitimate punctuation and formatting
"""
import re
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class InputSanitizer:
    """Sanitizes user input before LLM processing."""

    # Maximum input length (prevents token abuse)
    MAX_INPUT_LENGTH = 2000

    # Prompt injection patterns to detect/neutralize
    PROMPT_INJECTION_PATTERNS = [
        r'ignore\s+(previous|all|above|prior)\s+instructions?',
        r'disregard\s+(previous|all|above|prior)\s+(instructions?|context)',
        r'forget\s+(everything|all|previous)',
        r'new\s+instructions?:',
        r'system\s*:\s*you\s+are',
        r'you\s+are\s+now\s+a',
        r'pretend\s+(you\s+are|to\s+be)',
        r'roleplay\s+as',
        r'act\s+as\s+(if|a)',
        r'<\s*/?system\s*>',
        r'<\s*/?prompt\s*>',
        r'override\s+(previous|all|system)',
    ]

    # SQL injection patterns (defense in depth, even though we use API)
    SQL_INJECTION_PATTERNS = [
        r"('|\")?\s*(or|and)\s+('|\")?\s*1\s*=\s*1",
        r"('|\")?\s*(or|and)\s+('|\")?\s*\w+\s*=\s*\w+",
        r"union\s+select",
        r"drop\s+(table|database)",
        r"delete\s+from",
        r"insert\s+into",
        r"update\s+\w+\s+set",
        r"--\s*$",
        r"/\*.*?\*/",
        r"xp_cmdshell",
        r"exec(ute)?\s+",
    ]

    # HTML/Script patterns
    HTML_SCRIPT_PATTERNS = [
        r'<\s*script[^>]*>.*?<\s*/\s*script\s*>',
        r'<\s*iframe[^>]*>',
        r'on(load|error|click|mouse\w+)\s*=',
        r'javascript\s*:',
        r'<\s*embed[^>]*>',
        r'<\s*object[^>]*>',
    ]

    def __init__(self):
        """Initialize sanitizer with compiled regex patterns."""
        self.prompt_injection_regex = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL)
            for pattern in self.PROMPT_INJECTION_PATTERNS
        ]
        self.sql_injection_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.SQL_INJECTION_PATTERNS
        ]
        self.html_script_regex = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL)
            for pattern in self.HTML_SCRIPT_PATTERNS
        ]

    def sanitize(self, user_input: str) -> Tuple[str, Dict[str, any]]:
        """
        Sanitize user input.

        Args:
            user_input: Raw user input string

        Returns:
            Tuple of (sanitized_text, metadata) where metadata contains:
                - original_length: Original input length
                - sanitized_length: Sanitized input length
                - truncated: Whether input was truncated
                - threats_detected: List of detected threat types
                - is_safe: Boolean indicating if input passed all checks
        """
        metadata = {
            'original_length': len(user_input),
            'truncated': False,
            'threats_detected': [],
            'is_safe': True
        }

        if not user_input or not isinstance(user_input, str):
            logger.warning("[Input Sanitizer] Empty or invalid input")
            return "", metadata

        # Step 1: Length limit (prevent token abuse)
        if len(user_input) > self.MAX_INPUT_LENGTH:
            user_input = user_input[:self.MAX_INPUT_LENGTH]
            metadata['truncated'] = True
            logger.warning(
                f"[Input Sanitizer] Input truncated from {metadata['original_length']} "
                f"to {self.MAX_INPUT_LENGTH} characters"
            )

        # Step 2: Remove control characters (preserve newlines and tabs)
        user_input = ''.join(
            char for char in user_input
            if char.isprintable() or char in ['\n', '\t', ' ']
        )

        # Step 3: Detect prompt injection attempts
        for pattern in self.prompt_injection_regex:
            if pattern.search(user_input):
                metadata['threats_detected'].append('prompt_injection')
                metadata['is_safe'] = False
                logger.warning(
                    f"[Input Sanitizer] Potential prompt injection detected: {pattern.pattern}"
                )
                # Neutralize by adding quotes around suspicious phrases
                user_input = pattern.sub(lambda m: f'"{m.group()}"', user_input)

        # Step 4: Detect SQL injection patterns
        for pattern in self.sql_injection_regex:
            if pattern.search(user_input):
                metadata['threats_detected'].append('sql_injection')
                metadata['is_safe'] = False
                logger.warning(
                    f"[Input Sanitizer] Potential SQL injection detected: {pattern.pattern}"
                )
                # Remove SQL patterns
                user_input = pattern.sub(' ', user_input)

        # Step 5: Detect HTML/Script injection
        for pattern in self.html_script_regex:
            if pattern.search(user_input):
                metadata['threats_detected'].append('html_script_injection')
                metadata['is_safe'] = False
                logger.warning(
                    f"[Input Sanitizer] Potential HTML/Script injection detected: {pattern.pattern}"
                )
                # Remove HTML/Script tags
                user_input = pattern.sub(' ', user_input)

        # Step 6: Normalize whitespace (preserve single spaces)
        user_input = re.sub(r'\s+', ' ', user_input)
        user_input = user_input.strip()

        # Step 7: Remove excessive special characters (keep business-relevant ones)
        # Allow: letters, numbers, spaces, common punctuation, hyphens, slashes
        # This preserves: "March 2025", "Amisys", "Claims Processing", "N/A", etc.
        user_input = re.sub(r'[^\w\s\-.,;:?!()\'/]+', ' ', user_input)

        # Step 8: Final cleanup
        user_input = re.sub(r'\s+', ' ', user_input).strip()

        metadata['sanitized_length'] = len(user_input)

        if metadata['threats_detected']:
            logger.warning(
                f"[Input Sanitizer] Threats detected and neutralized: "
                f"{', '.join(set(metadata['threats_detected']))}"
            )
        else:
            logger.debug(f"[Input Sanitizer] Input sanitized successfully (no threats)")

        return user_input, metadata

    def format_for_llm(self, sanitized_input: str, context: Dict = None) -> str:
        """
        Format sanitized input into a clear, compact prompt for LLM.

        Creates a structured prompt that:
        - Clearly separates user query from context
        - Preserves all parameter details
        - Is concise but complete
        - Prevents prompt injection by clear role separation

        Args:
            sanitized_input: Sanitized user input
            context: Optional conversation context (previous filters, etc.)

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        # Add context if available
        if context:
            context_lines = []

            if context.get('current_forecast_month'):
                month_name = self._get_month_name(context['current_forecast_month'])
                year = context.get('current_forecast_year', '')
                context_lines.append(f"Current focus: {month_name} {year}")

            if context.get('last_platform'):
                context_lines.append(f"Last platform: {context['last_platform']}")

            if context.get('last_market'):
                context_lines.append(f"Last market: {context['last_market']}")

            if context_lines:
                prompt_parts.append(f"Context: {' | '.join(context_lines)}")

        # Add clear user query marker
        prompt_parts.append(f"User query: {sanitized_input}")

        # Join with newlines for clarity
        formatted_prompt = '\n'.join(prompt_parts)

        logger.debug(f"[Input Sanitizer] Formatted prompt: {formatted_prompt[:100]}...")

        return formatted_prompt

    def _get_month_name(self, month_num: int) -> str:
        """Convert month number to name."""
        months = [
            '', 'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        return months[month_num] if 1 <= month_num <= 12 else ''


# Singleton instance
_sanitizer = InputSanitizer()


def get_sanitizer() -> InputSanitizer:
    """Get singleton sanitizer instance."""
    return _sanitizer
