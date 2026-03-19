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
