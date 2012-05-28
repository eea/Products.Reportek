uri = 'http://rod.eionet.eu.int/obligations/%s' % id

for dataflow in context.dataflow_table():
    if dataflow['uri'] == uri:
        return dataflow['TITLE']
