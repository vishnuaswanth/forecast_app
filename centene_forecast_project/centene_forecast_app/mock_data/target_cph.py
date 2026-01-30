"""
Mock Data for Target CPH

Provides mock data for target CPH features:
- CPH data for LOB/Case Type combinations
- CPH preview (forecast impact of CPH changes)

Replace with actual FastAPI endpoint calls when backend is ready.
"""

from typing import Dict, List
import logging

logger = logging.getLogger('django')


def get_target_cph_data(month: str, year: int) -> Dict:
    """
    Get target CPH data for all LOB/CaseType combinations.

    Generates 55 records for pagination testing (3 pages at 25 records/page).

    Args:
        month: Month name (e.g., 'April')
        year: Year (e.g., 2025)

    Returns:
        Dictionary with CPH records

    Example:
        {
            'success': True,
            'data': [
                {
                    'id': 'cph_1',
                    'lob': 'Amisys Medicaid DOMESTIC',
                    'case_type': 'Claims Processing',
                    'target_cph': 45.0,
                    'modified_target_cph': 45.0
                }
            ],
            'total': 55
        }
    """
    logger.info(f"[CPH Update] Using mock data for {month} {year}")

    # Generate 55 LOB/CaseType combinations for pagination testing
    lobs = [
        'Amisys Medicaid DOMESTIC', 'Amisys Medicaid OFFSHORE',
        'Amisys Medicare DOMESTIC', 'Amisys Medicare OFFSHORE',
        'Amisys Commercial DOMESTIC', 'Amisys Commercial OFFSHORE',
        'Facets Medicaid DOMESTIC', 'Facets Medicaid OFFSHORE',
        'Facets Medicare DOMESTIC', 'Facets Medicare OFFSHORE',
        'Facets Commercial DOMESTIC', 'Facets Commercial OFFSHORE',
        'QNXT Medicaid DOMESTIC', 'QNXT Medicaid OFFSHORE',
        'QNXT Medicare DOMESTIC', 'QNXT Medicare OFFSHORE',
        'QNXT Commercial DOMESTIC', 'QNXT Commercial OFFSHORE',
        'HealthRules Medicaid DOMESTIC', 'HealthRules Medicare OFFSHORE'
    ]

    case_types = [
        'Claims Processing', 'Enrollment', 'Member Services',
        'Provider Services', 'Appeals', 'Billing Support',
        'Customer Service'
    ]

    mock_records = []
    record_id = 1

    # Generate combinations to create 55+ records
    for lob in lobs:
        for case_type in case_types[:3]:  # Use first 3 case types per LOB
            if record_id > 55:
                break

            # Vary CPH values between 35 and 75
            base_cph = 35 + (record_id % 40)
            mock_records.append({
                'id': f'cph_{record_id}',
                'lob': lob,
                'case_type': case_type,
                'target_cph': float(base_cph),
                'modified_target_cph': float(base_cph)
            })
            record_id += 1

    mock_data = {
        'success': True,
        'data': mock_records,
        'total': len(mock_records)
    }

    logger.info(f"[CPH Update] Retrieved {mock_data['total']} CPH records (MOCK)")
    return mock_data


def get_target_cph_preview(
    month: str,
    year: int,
    modified_records: list
) -> Dict:
    """
    Calculate forecast impact of CPH changes (preview).

    IMPORTANT: Backend MUST follow the SAME standardized format as bench allocation
    (see PREVIEW_RESPONSE_STANDARD.md)

    Standard Response Format (IDENTICAL to bench allocation WITH CPH fields):
    {
        'success': True,
        'months': {                              // Month index mapping at top level
            'month1': 'Jun-25',
            'month2': 'Jul-25',
            'month3': 'Aug-25',
            'month4': 'Sep-25',
            'month5': 'Oct-25',
            'month6': 'Nov-25'
        },
        'total_modified': 15,
        'modified_records': [
            {
                'main_lob': 'Medicaid',
                'state': 'MO',
                'case_type': 'Appeals',
                'case_id': 'CASE-123',           // Include for CPH preview
                'target_cph': 50.0,              // NEW CPH value (FLOAT) - included in CPH preview
                'target_cph_change': 5.0,        // Delta from original (FLOAT) - included in CPH preview
                'modified_fields': ['target_cph', 'Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity'],  // DOT notation, ALL 4 fields when month changes
                'months': {                      // Month data NESTED under 'months' object
                    'Jun-25': {
                        'forecast': 12500,       // Integer values
                        'fte_req': 11,
                        'fte_avail': 8,
                        'capacity': 400,
                        'forecast_change': 0,    // Always included
                        'fte_req_change': 2,
                        'fte_avail_change': 1,
                        'capacity_change': 50
                    }
                }
            }
        ],
        'summary': {'total_fte_change': 45, 'total_capacity_change': 2250},
        'message': None
    }

    Args:
        month: Month name (e.g., 'April')
        year: Year (e.g., 2025)
        modified_records: List of modified CPH records

    Returns:
        Dictionary with forecast impact using SAME structure as bench allocation
    """
    from mock_data.edit_view import get_bench_allocation_preview

    logger.info(
        f"[CPH Preview] Using mock preview for {month} {year} "
        f"({len(modified_records)} CPH changes)"
    )

    # Simulate that CPH changes affect forecast rows
    # Reuse the get_bench_allocation_preview mock data
    mock_preview = get_bench_allocation_preview(month, year)

    # Add CPH-specific fields to each record
    # Simulate CPH changes based on modified_records input
    for idx, record in enumerate(mock_preview.get('modified_records', [])):
        # Calculate simulated CPH values
        # Use different CPH values for variety
        base_cph = 45.0 + (idx * 2.5)
        cph_change = 3.0 + (idx * 0.5)

        # Add target_cph and target_cph_change as FLOATS with 2 decimal places
        record['target_cph'] = round(base_cph + cph_change, 2)
        record['target_cph_change'] = round(cph_change, 2)

        # Update modified_fields to include "target_cph"
        if 'modified_fields' in record:
            if 'target_cph' not in record['modified_fields']:
                record['modified_fields'].insert(0, 'target_cph')

    # Update message to indicate this is CPH-driven
    mock_preview['message'] = f"Preview shows forecast impact of {len(modified_records)} CPH changes"

    logger.info(
        f"[CPH Preview] Preview calculated - {mock_preview['total_modified']} "
        f"forecast rows affected by CPH changes (MOCK)"
    )
    return mock_preview
