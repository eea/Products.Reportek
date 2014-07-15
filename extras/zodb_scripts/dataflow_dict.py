## Script (Python) "dataflow_dict"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
class ServiceTemporarilyUnavailableException(Exception):
    pass


top = container.REQUEST.PARENTS[-1]
try:
    res = top.dataflow_rod()
except:
    raise ServiceTemporarilyUnavailableException, "Reporting Obligations Database is temporarily unavailable, please try again later"

dfdict = {}
for item in res:
    if item['uri'][:5] == 'null/':
        item['uri'] = 'http://rod.eionet.eu.int/obligations/' + item['uri'][5:]
    dfdict[item['uri']] = item
return dfdict

