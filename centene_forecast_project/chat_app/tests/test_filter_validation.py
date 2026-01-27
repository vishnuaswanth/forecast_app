"""
Test Suite for Filter Validation and Combination Diagnosis

Tests fuzzy matching, auto-correction, and combination diagnosis features.
"""

import pytest
import asyncio
from chat_app.services.tools.validation_tools import (
    FilterValidator,
    CombinationDiagnostic,
    ConfidenceLevel,
    ValidationResult,
    CombinationDiagnosticResult
)
from chat_app.services.tools.validation import ForecastQueryParams


class TestFuzzyMatching:
    """Test fuzzy matching with different confidence levels."""

    @pytest.fixture
    def validator(self):
        """Create FilterValidator instance."""
        return FilterValidator()

    @pytest.fixture
    def valid_platforms(self):
        """Sample valid platform options."""
        return ["Amisys", "Facets", "Xcelys"]

    @pytest.fixture
    def valid_markets(self):
        """Sample valid market options."""
        return ["Medicaid", "Medicare", "Marketplace"]

    @pytest.fixture
    def valid_states(self):
        """Sample valid state options."""
        return ["CA", "TX", "FL", "NY", "N/A"]

    def test_exact_match(self, validator, valid_platforms):
        """Test exact match returns 100% confidence."""
        result = validator.fuzzy_match("Amisys", valid_platforms)

        assert result.is_valid is True
        assert result.confidence == 1.0
        assert result.confidence_level == ConfidenceLevel.HIGH
        assert result.corrected_value == "Amisys"

    def test_exact_match_case_insensitive(self, validator, valid_platforms):
        """Test exact match is case-insensitive."""
        result = validator.fuzzy_match("amisys", valid_platforms)

        assert result.is_valid is True
        assert result.confidence == 1.0
        assert result.corrected_value == "Amisys"  # Normalized to correct case

    def test_high_confidence_typo(self, validator, valid_platforms):
        """Test high-confidence typo (>90%) is auto-corrected."""
        result = validator.fuzzy_match("Amysis", valid_platforms)

        assert result.is_valid is True
        assert result.confidence >= 0.90
        assert result.confidence_level == ConfidenceLevel.HIGH
        assert result.corrected_value == "Amisys"
        print(f"✅ High confidence match: 'Amysis' → 'Amisys' ({result.confidence:.2%})")

    def test_medium_confidence_typo(self, validator, valid_markets):
        """Test medium-confidence typo (60-90%) requires confirmation."""
        result = validator.fuzzy_match("Medcaid", valid_markets)

        assert result.is_valid is True
        assert 0.60 <= result.confidence < 0.90
        assert result.confidence_level == ConfidenceLevel.MEDIUM
        assert result.corrected_value == "Medicaid"
        assert "Medicaid" in result.suggestions
        print(f"✅ Medium confidence match: 'Medcaid' → 'Medicaid' ({result.confidence:.2%})")

    def test_low_confidence_rejection(self, validator, valid_platforms):
        """Test low-confidence match (<60%) is rejected."""
        result = validator.fuzzy_match("Xylophone", valid_platforms)

        assert result.is_valid is False
        assert result.confidence < 0.60
        assert result.confidence_level == ConfidenceLevel.LOW
        assert result.corrected_value is None
        assert len(result.suggestions) > 0
        print(f"✅ Low confidence rejection: 'Xylophone' (confidence: {result.confidence:.2%})")

    def test_state_normalization(self, validator, valid_states):
        """Test state name normalization (California → CA)."""
        # Test state name to code mapping
        normalized = validator.normalize_state_value("California")
        assert normalized == "CA"

        normalized = validator.normalize_state_value("texas")
        assert normalized == "TX"

        # Test already a code
        normalized = validator.normalize_state_value("FL")
        assert normalized == "FL"

        print("✅ State normalization: California → CA, texas → TX")

    def test_multiple_suggestions(self, validator, valid_platforms):
        """Test that fuzzy match returns multiple suggestions."""
        result = validator.fuzzy_match("Faces", valid_platforms)

        assert len(result.suggestions) >= 1
        assert "Facets" in result.suggestions
        print(f"✅ Multiple suggestions for 'Faces': {result.suggestions}")


class TestFilterValidation:
    """Test full filter validation flow."""

    @pytest.fixture
    def validator(self):
        """Create FilterValidator instance."""
        return FilterValidator()

    @pytest.mark.asyncio
    async def test_validate_all_with_typos(self, validator, monkeypatch):
        """Test validate_all() with typos in multiple fields."""
        # Mock get_filter_options to return test data
        async def mock_get_filter_options(month, year, force_refresh=False):
            return {
                'platforms': ['Amisys', 'Facets', 'Xcelys'],
                'markets': ['Medicaid', 'Medicare'],
                'localities': ['Domestic', 'Global'],
                'states': ['CA', 'TX', 'FL', 'NY'],
                'case_types': ['Claims Processing', 'Enrollment']
            }

        monkeypatch.setattr(validator, 'get_filter_options', mock_get_filter_options)

        # Create params with typos
        params = ForecastQueryParams(
            month=3,
            year=2025,
            platforms=['Amysis'],  # Typo
            markets=['Medcaid'],   # Typo
            states=['California']  # Should normalize to CA
        )

        results = await validator.validate_all(params)

        # Check platforms
        assert 'platforms' in results
        platform_result = results['platforms'][0]
        assert platform_result.confidence >= 0.90  # High confidence
        assert platform_result.corrected_value == 'Amisys'

        # Check markets
        assert 'markets' in results
        market_result = results['markets'][0]
        assert 0.60 <= market_result.confidence < 0.90  # Medium confidence
        assert market_result.corrected_value == 'Medicaid'

        # Check states
        assert 'states' in results
        state_result = results['states'][0]
        assert state_result.is_valid is True
        assert state_result.corrected_value == 'CA'

        print("✅ validate_all() correctly identified and corrected typos")

    @pytest.mark.asyncio
    async def test_validate_all_with_invalid_filter(self, validator, monkeypatch):
        """Test validate_all() with completely invalid filter value."""
        async def mock_get_filter_options(month, year, force_refresh=False):
            return {
                'platforms': ['Amisys', 'Facets', 'Xcelys'],
                'states': ['CA', 'TX', 'FL', 'NY']
            }

        monkeypatch.setattr(validator, 'get_filter_options', mock_get_filter_options)

        params = ForecastQueryParams(
            month=3,
            year=2025,
            platforms=['InvalidPlatform'],
            states=['ZZ']  # Invalid state
        )

        results = await validator.validate_all(params)

        # Check that invalid values are rejected
        platform_result = results['platforms'][0]
        assert platform_result.is_valid is False
        assert len(platform_result.suggestions) > 0

        state_result = results['states'][0]
        assert state_result.is_valid is False
        assert 'CA' in state_result.suggestions or 'TX' in state_result.suggestions

        print("✅ validate_all() correctly rejected invalid filter values")


class TestCombinationDiagnosis:
    """Test filter combination diagnosis."""

    @pytest.fixture
    def diagnostic(self):
        """Create CombinationDiagnostic instance."""
        return CombinationDiagnostic()

    @pytest.mark.asyncio
    async def test_diagnose_no_data_uploaded(self, diagnostic, monkeypatch):
        """Test diagnosis when no data exists for month/year."""
        # Mock validator to return None (no filter options)
        async def mock_get_filter_options(month, year, force_refresh=False):
            return None

        monkeypatch.setattr(diagnostic.validator, 'get_filter_options', mock_get_filter_options)

        params = ForecastQueryParams(month=12, year=2026)
        api_response = {'records': [], 'total_records': 0}

        result = await diagnostic.diagnose(params, api_response)

        assert result.is_data_issue is True
        assert result.is_combination_issue is False
        assert result.total_records_available == 0
        assert "No forecast data has been uploaded" in result.diagnosis_message
        print("✅ Correctly diagnosed: No data uploaded for December 2026")

    @pytest.mark.asyncio
    async def test_diagnose_combination_issue(self, diagnostic, monkeypatch):
        """Test diagnosis of filter combination issue."""
        # Mock get_filter_options
        async def mock_get_filter_options(month, year, force_refresh=False):
            return {
                'platforms': ['Amisys', 'Facets'],
                'markets': ['Medicaid', 'Medicare'],
                'states': ['CA', 'TX', 'FL'],
                'case_types': ['Claims Processing'],
                'record_count': 1250
            }

        # Mock _query_without_filters to return records
        async def mock_query_without_filters(month, year):
            return {'total_records': 1250, 'records': [{'id': 1}]}

        # Mock client.get_forecast_data to simulate filter testing
        call_count = [0]

        def mock_get_forecast_data(month, year, **filters):
            call_count[0] += 1
            # If state filter is removed, return records
            if 'state' not in filters:
                return {'total_records': 150, 'records': [{'id': 1}]}
            # Otherwise, return 0 records
            return {'total_records': 0, 'records': []}

        monkeypatch.setattr(diagnostic.validator, 'get_filter_options', mock_get_filter_options)
        monkeypatch.setattr(diagnostic, '_query_without_filters', mock_query_without_filters)
        monkeypatch.setattr(diagnostic.client, 'get_forecast_data', mock_get_forecast_data)

        params = ForecastQueryParams(
            month=3,
            year=2025,
            platforms=['Amisys'],
            markets=['Medicaid'],
            states=['ZZ']  # Problematic filter
        )
        api_response = {'records': [], 'total_records': 0}

        result = await diagnostic.diagnose(params, api_response)

        assert result.is_data_issue is False
        assert result.is_combination_issue is True
        assert 'state' in result.problematic_filters
        assert result.total_records_available == 1250
        print(f"✅ Correctly diagnosed problematic filter: {result.problematic_filters}")

    @pytest.mark.asyncio
    async def test_generate_diagnosis_message(self, diagnostic):
        """Test diagnosis message generation."""
        params = ForecastQueryParams(
            month=3,
            year=2025,
            platforms=['Amisys'],
            states=['ZZ']
        )

        problematic_filters = ['state']
        working_combinations = {
            'state': ['CA', 'TX', 'FL', 'NY', 'GA']
        }
        total_available = 1250

        message = diagnostic._generate_diagnosis_message(
            params,
            problematic_filters,
            working_combinations,
            total_available
        )

        assert 'state' in message.lower()
        assert '1250' in message
        assert 'CA' in message or 'TX' in message
        print(f"✅ Generated diagnosis message:\n{message[:200]}...")


class TestEndToEndValidation:
    """Test end-to-end validation scenarios."""

    @pytest.mark.asyncio
    async def test_auto_correction_flow(self):
        """Test that high-confidence typos are auto-corrected."""
        from chat_app.services.tools.validation import FilterValidationSummary

        validator = FilterValidator()

        # Mock get_filter_options
        async def mock_get_filter_options(month, year, force_refresh=False):
            return {
                'platforms': ['Amisys', 'Facets', 'Xcelys']
            }

        validator.get_filter_options = mock_get_filter_options

        params = ForecastQueryParams(
            month=3,
            year=2025,
            platforms=['Amysis']  # High-confidence typo
        )

        results = await validator.validate_all(params)

        # Simulate processing in LLM service
        summary = FilterValidationSummary()

        for field_name, field_results in results.items():
            for result in field_results:
                if result.confidence >= FilterValidator.HIGH_CONFIDENCE and result.corrected_value:
                    summary.auto_corrected.setdefault(field_name, []).append(result.corrected_value)
                    # In real service, params would be updated here
                    assert result.corrected_value == 'Amisys'

        assert summary.get_correction_count() == 1
        assert not summary.has_issues()  # No user action needed
        print("✅ Auto-correction flow: 'Amysis' → 'Amisys' (no user action needed)")

    @pytest.mark.asyncio
    async def test_confirmation_required_flow(self):
        """Test that medium-confidence typos require confirmation."""
        from chat_app.services.tools.validation import FilterValidationSummary

        validator = FilterValidator()

        async def mock_get_filter_options(month, year, force_refresh=False):
            return {
                'markets': ['Medicaid', 'Medicare']
            }

        validator.get_filter_options = mock_get_filter_options

        params = ForecastQueryParams(
            month=3,
            year=2025,
            markets=['Medcaid']  # Medium-confidence typo
        )

        results = await validator.validate_all(params)

        summary = FilterValidationSummary()

        for field_name, field_results in results.items():
            for result in field_results:
                if result.confidence_level == ConfidenceLevel.MEDIUM:
                    summary.needs_confirmation.setdefault(field_name, []).append(
                        (result.original_value, result.corrected_value, result.confidence)
                    )

        assert summary.get_confirmation_count() == 1
        assert summary.has_issues()  # User action required
        print("✅ Confirmation flow: 'Medcaid' → 'Medicaid' (user confirmation required)")


# Pytest configuration
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
