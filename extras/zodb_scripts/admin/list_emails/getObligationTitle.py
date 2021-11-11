# flake8: noqa
# Script (Python) "getObligationTitle"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=id
# title=
##
uri = 'http://rod.eionet.europa.eu/obligations/%s' % id

for dataflow in context.dataflow_table():  # noqa: F821
    if dataflow['uri'] == uri:
        return dataflow['TITLE']  # noqa: F999
