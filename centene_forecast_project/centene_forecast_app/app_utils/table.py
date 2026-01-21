
def get_schema():
    schema = [
        {
            'header': {
                'name': 'Platform'
            },
            'key': 'Platform'
        },
        {
            'header': {
                'name': 'Work Type'
            },
            'key': 'Work Type'
        },
        {
            'header': {
                'name': 'State'
            },
            'key': 'State'
        },
        {
            'header': {
                'name': 'Product'
            },
            'key': 'Product'
        },
        {
            'header': {
                'name': 'Location'
            },
            'key': 'Location'
        },
        {
            'header': {
                'name': 'Resource Status'
            },
            'key': 'Resource Status'
        },
        {
            'header': {
                'name': 'Status'
            },
            'key': 'Status'
        },
        {
            'header': {
                'name': 'First Name'
            },
            'key': 'FirstName'
        },
        {
            'header': {
                'name': 'Last Name'
            },
            'key': 'LastName'
        },
        {
            'header': {
                'name': 'Portal Id'
            },
            'key': 'PortalId'
        },
        {
            'header': {
                'name': 'CN#'
            },
            'key': 'CN#'
        },
        {
            'header': {
                'name': 'Hire Date/Amisys Start Date,'
            },
            'key': 'Hire Date/Amisys Start Date'
        },
        {
            'header': {
                'name': 'OPID'
            },
            'key': 'OPID'
        },
        {
            'header': {
                'name': 'Position'
            },
            'key': 'Position'
        },
        {
            'header': {
                'name': 'TL'
            },
            'key': 'TL'
        },
        {
            'header': {
                'name': 'Supervisor'
            },
            'key': 'Supervisor'
        },
        {
            'header': {
                'name': 'Primary Skills'
            },
            'key': 'Primary Skills'
        },
        {
            'header': {
                'name': 'Secondary Skills'
            },
            'key': 'Secondary Skills'
        },
        {
            'header': {
                'name': 'City'
            },
            'key': 'City'
        },
        {
            'header': {
                'name': 'Class Name'
            },
            'key': 'Class Name'
        }
    ]
    return schema

def get_table_schema(data):
    column_names = []
    rows = []
    if len(data)>0:
        for fields in data[0]:
            column_names.append(fields)

        for row in data:
            l=[]
            for col_name in column_names:
                l.append(row[col_name])
            rows.append(l)

    return column_names, rows
