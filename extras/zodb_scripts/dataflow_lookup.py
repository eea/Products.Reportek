top = container.REQUEST.PARENTS[-1]
try:
    return top.dataflow_dict()[uri]
except:
    return {'uri': uri,
 'details_url': '',
 'TITLE': 'Unknown/Deleted obligation',
 'terminated':'1',
 'SOURCE_TITLE': 'Unknown obligations',
 'PK_RA_ID': '0'}
