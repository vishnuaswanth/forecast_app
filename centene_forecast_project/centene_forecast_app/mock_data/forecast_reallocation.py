"""
Forecast Reallocation Mock Data

Mock data for testing the Forecast Reallocation feature until backend endpoints are ready.
Provides filter options, editable data, preview calculations, and update responses.
"""

import uuid
from typing import Dict, List, Optional
from datetime import datetime


def get_reallocation_filter_options(month: str, year: int) -> Dict:
    """
    Get available filter options for forecast reallocation.

    Args:
        month: Month name (e.g., 'April')
        year: Year (e.g., 2025)

    Returns:
        Dictionary with filter options:
        {
            'success': True,
            'main_lobs': ['Medicaid', 'Medicare', ...],
            'states': ['MO', 'TX', 'FL', ...],
            'case_types': ['Appeals', 'Claims', ...]
        }
    """
    return {
        'success': True,
        'main_lobs': [
            'Medicaid',
            'Medicare',
            'Commercial',
            'Exchange',
            'Duals'
        ],
        'states': [
            'MO', 'TX', 'FL', 'GA', 'IL', 'OH', 'MI', 'NC', 'AZ', 'NV',
            'WA', 'OR', 'CA', 'NY', 'PA'
        ],
        'case_types': [
            'Appeals',
            'Claims',
            'Adjustments',
            'Correspondence',
            'OMNI',
            'FTC',
            'Member Services',
            'Provider Services'
        ]
    }


def get_reallocation_data(
    month: str,
    year: int,
    main_lobs: Optional[List[str]] = None,
    case_types: Optional[List[str]] = None,
    states: Optional[List[str]] = None
) -> Dict:
    """
    Get editable forecast records for reallocation.

    Args:
        month: Month name (e.g., 'April')
        year: Year (e.g., 2025)
        main_lobs: Optional list of Main LOBs to filter
        case_types: Optional list of Case Types to filter
        states: Optional list of States to filter

    Returns:
        Dictionary with forecast records
    """
    # Generate month labels based on report month
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    month_abbrev = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }

    start_month = month_map.get(month, 4)  # Default to April
    year_short = str(year)[-2:]

    months_mapping = {}
    month_labels = []
    for i in range(6):
        m = ((start_month - 1 + i) % 12) + 1
        y = year if start_month + i <= 12 else year + 1
        y_short = str(y)[-2:]
        label = f"{month_abbrev[m]}-{y_short}"
        months_mapping[f"month{i+1}"] = label
        month_labels.append(label)

    # Define all possible records
    all_records = _generate_mock_records(month_labels)

    # Apply filters
    filtered_records = all_records

    if main_lobs:
        filtered_records = [r for r in filtered_records if r['main_lob'] in main_lobs]

    if case_types:
        filtered_records = [r for r in filtered_records if r['case_type'] in case_types]

    if states:
        filtered_records = [r for r in filtered_records if r['state'] in states]

    return {
        'success': True,
        'months': months_mapping,
        'data': filtered_records,
        'total': len(filtered_records)
    }


def _generate_mock_records(month_labels: List[str]) -> List[Dict]:
    """Generate mock forecast records."""
    import random
    random.seed(42)  # For consistent mock data

    lobs = ['Medicaid', 'Medicare', 'Commercial', 'Exchange', 'Duals']
    states = ['MO', 'TX', 'FL', 'GA', 'IL', 'OH', 'MI', 'NC', 'AZ', 'NV']
    case_types = ['Appeals', 'Claims', 'Adjustments', 'Correspondence', 'FTC', 'OMNI']

    records = []

    for lob in lobs:
        for state in states[:5]:  # Limit for manageable data
            for case_type in case_types[:4]:  # Limit for manageable data
                # Base values vary by LOB
                base_forecast = random.randint(8000, 25000)
                base_cph = random.randint(80, 150)
                base_fte = random.randint(5, 25)

                months_data = {}
                for label in month_labels:
                    forecast = base_forecast + random.randint(-2000, 3000)
                    fte_req = max(1, int(forecast / base_cph))
                    fte_avail = max(0, fte_req + random.randint(-5, 5))
                    capacity = fte_avail * base_cph

                    months_data[label] = {
                        'forecast': forecast,
                        'fte_req': fte_req,
                        'fte_avail': fte_avail,
                        'capacity': capacity
                    }

                records.append({
                    'case_id': str(uuid.uuid4()),
                    'main_lob': lob,
                    'state': state,
                    'case_type': case_type,
                    'target_cph': float(base_cph),
                    'months': months_data
                })

    return records


def get_reallocation_preview(
    month: str,
    year: int,
    modified_records: List[Dict]
) -> Dict:
    """
    Calculate preview with user-edited values.

    This mock simulates what the backend would calculate:
    - Recalculates FTE Required based on new CPH
    - Recalculates Capacity based on new FTE Available

    Args:
        month: Month name
        year: Year
        modified_records: List of modified record dictionaries

    Returns:
        Dictionary with preview data
    """
    preview_records = []

    for record in modified_records:
        # Clone record for preview
        preview_record = {
            'case_id': record['case_id'],
            'main_lob': record['main_lob'],
            'state': record['state'],
            'case_type': record['case_type'],
            'target_cph': record['target_cph'],
            'target_cph_change': record.get('target_cph_change', 0),
            'modified_fields': record.get('modified_fields', []),
            'months': {}
        }

        # Process each month
        for month_key, month_data in record.get('months', {}).items():
            forecast = month_data.get('forecast', 0)
            target_cph = record['target_cph']
            fte_avail = month_data.get('fte_avail', 0)

            # Recalculate FTE Required based on target CPH
            fte_req = max(1, int(forecast / target_cph)) if target_cph > 0 else 0

            # Recalculate Capacity
            capacity = int(fte_avail * target_cph)

            # Calculate gap
            gap = capacity - forecast

            preview_record['months'][month_key] = {
                'forecast': forecast,
                'fte_req': fte_req,
                'fte_avail': fte_avail,
                'fte_avail_change': month_data.get('fte_avail_change', 0),
                'capacity': capacity,
                'gap': gap
            }

        preview_records.append(preview_record)

    return {
        'success': True,
        'months': {},  # Will be populated from request context
        'modified_records': preview_records,
        'total_modified': len(preview_records),
        'summary': {
            'total_fte_change': sum(
                sum(m.get('fte_avail_change', 0) for m in r.get('months', {}).values())
                for r in modified_records
            ),
            'total_records': len(preview_records)
        }
    }


def submit_reallocation_update(
    month: str,
    year: int,
    months: Dict,
    modified_records: List[Dict],
    user_notes: str
) -> Dict:
    """
    Submit and save reallocation changes (mock).

    Args:
        month: Month name
        year: Year
        months: Month index mapping
        modified_records: List of modified record dictionaries
        user_notes: User-provided description

    Returns:
        Success response
    """
    # Simulate successful update
    return {
        'success': True,
        'message': 'Forecast reallocation updated successfully',
        'records_updated': len(modified_records),
        'history_log_id': str(uuid.uuid4()),
        'timestamp': datetime.now().isoformat()
    }
