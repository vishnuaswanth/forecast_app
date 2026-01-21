# import json

# with open("actuals.json") as f:
#     data = json.load(f)

# filters = data['122024']['amysis']['medicaid']['domestic']['FTC']

# for i in filters[0]:
#     print(i)

string = "FTC-Basic/Non MMP"
print(string[:3])



# cols=[]
# objects={}
# objects["data-url"] = "url"
# objects["table-id"] = "roster"
# for k ,i in data[5].items():
#     col={}
#     col["data"] = k
#     col["title"] = k.upper()
#     if k in ['Platform']:
#         col["editable"] = 'true'
#     cols.append(col)
# objects["columns"] = cols
# print(objects)







# unique_worktypes = {
#     rec["worktype"]
#     for recs in forecast["data"].values()
#     for rec in recs
# }

# print(len(sorted(unique_worktypes)))

# main_lob = "Amisys Medicaid DOMESTIC"
# worktype = "OMN-Basic/NON MMP"
# filtered = {}
# for month, recs in data.get('data', {}).items():
#     # apply only the two filters
#     out = []
#     for rec in recs:
#         if main_lob and rec.get('main lob') != main_lob:
#             continue
#         if worktype and rec.get('worktype') != worktype:
#             continue
#         out.append(rec)
#     filtered[month] = out
# print(len(filtered["February"]))