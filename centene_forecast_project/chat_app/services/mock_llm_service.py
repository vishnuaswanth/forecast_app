"""
Mock LLM Service for Phase 1 Prototyping.
Uses simple keyword matching instead of real LLM API calls.
This allows testing the chat interface without LLM dependencies.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MockLLMService:
    """
    Mock LLM service that uses keyword-based categorization.
    Phase 1: Simple prototype - READ-ONLY operations.
    """

    def __init__(self):
        """Initialize mock LLM service"""
        self.categories = {
            'forecast_query': ['forecast', 'prediction', 'estimate', 'projection'],
            'roster_query': ['roster', 'team', 'members', 'staff', 'resources'],
            'execution_status': ['execution', 'status', 'progress', 'running'],
            'ramp_query': ['ramp', 'onboarding', 'training', 'capacity'],
        }

    def categorize_intent(self, user_text: str) -> Dict[str, Any]:
        """
        Categorize user intent based on keywords.

        Args:
            user_text: User's input message

        Returns:
            Dictionary with category, confidence, and extracted parameters
        """
        user_text_lower = user_text.lower()

        # Check each category for keyword matches
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword in user_text_lower:
                    return {
                        'category': category,
                        'confidence': 0.85,  # Mock confidence score
                        'parameters': self._extract_parameters(user_text_lower, category),
                        'original_text': user_text
                    }

        # Default: unknown intent
        return {
            'category': 'unknown',
            'confidence': 0.0,
            'parameters': {},
            'original_text': user_text
        }

    def _extract_parameters(self, text: str, category: str) -> Dict[str, Any]:
        """
        Extract parameters from user text based on category.

        Args:
            text: Lowercased user text
            category: Detected category

        Returns:
            Dictionary of extracted parameters
        """
        params = {}

        # Extract month
        months = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }

        for month_name, month_num in months.items():
            if month_name in text:
                params['month'] = month_num
                break

        # Extract year (look for 4-digit year)
        import re
        year_match = re.search(r'\b(20\d{2})\b', text)
        if year_match:
            params['year'] = int(year_match.group(1))
        else:
            # Default to current year
            from datetime import datetime
            params['year'] = datetime.now().year

        # Extract platform
        platforms = ['amisys', 'facets', 'xcelys']
        for platform in platforms:
            if platform in text:
                params['platform'] = platform.capitalize()
                break

        # Extract market
        markets = ['medicaid', 'medicare', 'marketplace']
        for market in markets:
            if market in text:
                params['market'] = market.capitalize()
                break

        # Extract worktype
        worktypes = ['claims', 'enrollment', 'customer service', 'authorization']
        for worktype in worktypes:
            if worktype in text:
                params['worktype'] = worktype.title()
                break

        return params

    def get_mock_forecast_data(self, parameters: Dict[str, Any]) -> list:
        """
        Generate mock forecast data for testing.

        Args:
            parameters: Query parameters

        Returns:
            List of mock forecast records
        """
        month = parameters.get('month', 1)
        year = parameters.get('year', 2025)

        # Generate mock data (5 rows for preview)
        mock_data = []
        platforms = ['Amisys Onshore', 'Amisys Offshore', 'Facets Onshore', 'QNXT Onshore', 'QNXT Offshore']
        markets = ['Commercial', 'Medicaid', 'Medicare', 'Marketplace', 'Commercial']
        worktypes = ['Claims', 'Enrollment', 'Claims', 'Authorization', 'Claims']

        for i in range(5):
            row = {
                'platform': platforms[i],
                'market': markets[i],
                'worktype': worktypes[i],
                'month1_forecast': 10000 + (i * 1000),
                'month1_gap': (-250 if i % 2 == 0 else 150) + (i * 20),
                'month2_forecast': 10500 + (i * 1000),
                'month2_gap': (120 if i % 2 == 0 else -80) + (i * 15),
                'month3_forecast': 11000 + (i * 1000),
                'month3_gap': (-100 if i % 2 == 0 else 200) + (i * 10),
                'month4_forecast': 11500 + (i * 1000),
                'month4_gap': (180 if i % 2 == 0 else -120) + (i * 12),
                'month5_forecast': 12000 + (i * 1000),
                'month5_gap': (-90 if i % 2 == 0 else 160) + (i * 8),
                'month6_forecast': 12500 + (i * 1000),
                'month6_gap': (210 if i % 2 == 0 else -140) + (i * 15),
                'cph': 24.5 + (i * 0.5)
            }
            mock_data.append(row)

        logger.info(f"Generated {len(mock_data)} mock forecast records")
        return mock_data

    def get_mock_roster_data(self, parameters: Dict[str, Any]) -> list:
        """
        Generate mock roster data for testing.

        Args:
            parameters: Query parameters

        Returns:
            List of mock roster records
        """
        mock_data = [
            {'name': 'John Doe', 'platform': 'Amisys', 'market': 'Commercial', 'role': 'Analyst', 'fte': 1.0},
            {'name': 'Jane Smith', 'platform': 'Facets', 'market': 'Medicaid', 'role': 'Senior Analyst', 'fte': 1.0},
            {'name': 'Bob Johnson', 'platform': 'QNXT', 'market': 'Medicare', 'role': 'Lead', 'fte': 0.8},
            {'name': 'Alice Williams', 'platform': 'Amisys', 'market': 'Marketplace', 'role': 'Analyst', 'fte': 1.0},
            {'name': 'Charlie Brown', 'platform': 'Facets', 'market': 'Commercial', 'role': 'Manager', 'fte': 1.0},
        ]

        logger.info(f"Generated {len(mock_data)} mock roster records")
        return mock_data

    def get_mock_execution_status(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mock execution status for testing.

        Args:
            parameters: Query parameters

        Returns:
            Dictionary with execution status
        """
        status = {
            'total_tasks': 10,
            'completed': 7,
            'in_progress': 2,
            'failed': 1,
            'status': 'running',
            'progress_percentage': 70
        }

        logger.info("Generated mock execution status")
        return status
