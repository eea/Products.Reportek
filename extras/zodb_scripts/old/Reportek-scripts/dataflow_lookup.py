# flake8: noqa
# Script (Python) "dataflow_lookup"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=uri
# title=Lookup a dataflow on URI and return a dictionary of info
##
try:
    return container.dataflow_dict()[uri]
except:
    return {'uri': uri, 'details_url': '',
            'TITLE': 'Unknown/Deleted obligation',
            'SOURCE_TITLE': 'Unknown obligations', 'PK_RA_ID': '0'}
