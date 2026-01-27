"""
Data Chunking Utilities
Handles chunking of large forecast datasets for LLM processing.
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class ForecastDataChunker:
    """
    Chunks large forecast data for LLM processing.

    Splits records into manageable chunks and creates summaries
    for LLM context understanding.
    """

    def __init__(self, max_records_per_chunk: int = 100):
        """
        Initialize chunker.

        Args:
            max_records_per_chunk: Maximum number of records per chunk
        """
        self.max_records_per_chunk = max_records_per_chunk
        logger.info(f"[Chunker] Initialized with max_records_per_chunk={max_records_per_chunk}")

    def chunk_records(self, records: List[dict]) -> List[List[dict]]:
        """
        Split records into manageable chunks.

        Args:
            records: List of forecast records

        Returns:
            List of record chunks
        """
        chunks = []
        for i in range(0, len(records), self.max_records_per_chunk):
            chunk = records[i:i + self.max_records_per_chunk]
            chunks.append(chunk)

        logger.info(f"[Chunker] Split {len(records)} records into {len(chunks)} chunks")
        return chunks

    def create_summary_for_llm(self, data: dict) -> str:
        """
        Create a concise summary of data for LLM context.

        Args:
            data: Full forecast data response from API

        Returns:
            Summary string for LLM
        """
        month = data.get('month', 'Unknown')
        year = data.get('year', 'Unknown')
        total_records = data.get('total_records', 0)

        months_included = ', '.join(data.get('months', {}).values())
        filters_applied = self._format_filters(data.get('filters_applied', {}))

        # Get business insights
        business_insights = data.get('business_insights', {})
        staffing_status = self._format_staffing_status(
            business_insights.get('staffing_status', {})
        )
        trend_desc = business_insights.get('trend_analysis', {}).get('description', 'N/A')

        # Get totals
        totals_summary = self._format_totals(data.get('totals', {}))

        summary = f"""
Forecast Data Summary:
- Report Period: {month} {year}
- Total Records: {total_records}
- Months Included: {months_included}
- Filters Applied: {filters_applied}

Totals:
{totals_summary}

Business Insights:
- Staffing Status: {staffing_status}
- Trend: {trend_desc}
"""

        logger.info(f"[Chunker] Created summary for {month} {year} ({total_records} records)")
        return summary

    def _format_filters(self, filters: dict) -> str:
        """
        Format filters for summary.

        Args:
            filters: Dictionary of applied filters

        Returns:
            Formatted filter string
        """
        active = []
        for key, value in filters.items():
            if value:  # Only include non-empty filters
                if isinstance(value, list):
                    active.append(f"{key}: {', '.join(value)}")
                else:
                    active.append(f"{key}: {value}")

        return ", ".join(active) if active else "None"

    def _format_totals(self, totals: dict) -> str:
        """
        Format totals for summary.

        Args:
            totals: Dictionary of totals per month

        Returns:
            Formatted totals string
        """
        lines = []
        for month, values in totals.items():
            forecast_total = values.get('forecast_total', 0)
            gap_total = values.get('gap_total', 0)
            lines.append(f"  {month}: Forecast={forecast_total:,.0f}, Gap={gap_total:,.0f}")

        return "\n".join(lines) if lines else "  No totals available"

    def _format_staffing_status(self, staffing_status: dict) -> str:
        """
        Format staffing status for summary.

        Args:
            staffing_status: Dictionary of staffing status per month

        Returns:
            Formatted staffing status string
        """
        statuses = []
        for month, status_info in staffing_status.items():
            status = status_info.get('status', 'unknown')
            gap_pct = status_info.get('gap_percentage', 0)
            statuses.append(f"{month}: {status} ({gap_pct:.1f}%)")

        return ", ".join(statuses) if statuses else "N/A"

    def estimate_chunk_count(self, total_records: int) -> int:
        """
        Estimate number of chunks needed.

        Args:
            total_records: Total number of records

        Returns:
            Estimated number of chunks
        """
        import math
        chunks = math.ceil(total_records / self.max_records_per_chunk)
        logger.debug(f"[Chunker] Estimated {chunks} chunks for {total_records} records")
        return chunks
