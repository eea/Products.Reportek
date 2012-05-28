try:
    return container.dataflow_dict()[uri]
except:
    return {'uri': uri, 'details_url': '',
 'TITLE': 'Unknown/Deleted obligation',
 'SOURCE_TITLE': 'Unknown obligations', 'PK_RA_ID': '0'}
