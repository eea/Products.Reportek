## Script (Python) "dataflow_table"
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


def inline_replace(x):
   x['uri'] = x['uri'].replace('eionet.eu.int', 'eionet.europa.eu')
   return x


try:
    return map(inline_replace, container.dataflow_rod())
except Exception:
    raise ServiceTemporarilyUnavailableException, "Reporting Obligations Database is temporarily unavailable, please try again later"
