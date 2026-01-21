import datetime

from core.constants import SUMMARY_TYPES

def get_dropdown_options(years):
    
    data_type=[
        {'value':'prod_team_roster','display':'Roster'},
        {'value':'forecast','display':'Forecast'},
        {'value':'summary', 'display':'Summary'}
        # {'value':'actuals','display':'Actuals'}
    ]
    month_name_to_num = {
        'January': '1', 'February': '2', 'March': '3', 'April': '4',
        'May': '5', 'June': '6', 'July': '7', 'August': '8',
        'September': '9', 'October': '10', 'November': '11', 'December': '12'
    }
    month_options = [{'value': 'select', 'display': 'Select Month'}]
    
    # month_options += [
    #     {'value': month_name_to_num[m], 'display': m}
    #     for m in months if m in month_name_to_num
    # ]
    year_options = [{'value': 'select', 'display': 'Select Year'}]
    year_options += years['years']
    # boc = [
    #     {'value': 'select', 'display': 'Select'},
    #     {'value': 'Amisys', 'display': 'Amysis'},
    #     {'value': 'Xcelys', 'display': 'Xcelys'},
    # ]
    boc = []
    # insurance = [
    #     {'value': 'select', 'display': 'Select'},
    #     {'value': 'Medicaid', 'display': 'Medicaid'},
    #     {'value': 'Medicare', 'display': 'Medicare'},
    # ]
    insurance = []
    # locality = [
    #     {'value': 'select', 'display': 'Select'},
    #     {'value': 'GLOBAL', 'display': 'Global'},
    #     {'value': 'DOMESTIC', 'display': 'Domestic'},
    #     {'value': 'state', 'display': 'State'},
    # ]
    locality = []
    process = [
        {'value': 'select', 'display': 'Select'},
        {'value': 'ADJ-Basic/NON MMP', 'display':'ADJ-Basic NON MMP'},
        {'value': 'ADJ-COB NON MMP', 'display': 'ADJ-COB NON MMP'},
        {'value': 'APP-BASIC/NON MMP', 'display':'APP-BASIC NON MMP'},
        {'value': 'APP-COB NON MMP', 'display': 'APP-COB NON MMP'},
        {'value': 'COR-Basic/NON MMP', 'display':'COR-Basic NON MMP'},
        {'value': 'COR-COB NON MMP', 'display': 'COR-COB NON MMP'},
        {'value': 'FTC-Basic/Non MMP', 'display':'FTC-Basic Non MMP'},
        {'value': 'FTC-COB NON MMP', 'display':'FTC-COB NON MMP'},
        {'value': 'OMN-Basic/NON MMP', 'display':'OMN-Basic NON MMP'},
        {'value': 'OMN-COB NON MMP', 'display': 'OMN-COB NON MMP'},
    ]
    summary_types = [
        {'value': 'select', 'display': 'Select'},
    ]
    summary_types.extend(
        {'value': item, 'display': item} for item in SUMMARY_TYPES
    )

    return {
        'data_type_options': data_type,
        'month_options': month_options,
        'year_options': year_options,
        'platform_options': boc,
        'market_options': insurance,
        'locality_options': locality,
        'worktype_options': process,
        'summary_types': summary_types
    }