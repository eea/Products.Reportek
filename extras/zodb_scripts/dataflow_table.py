## Script (Python) "dataflow_table"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
def inline_replace(x):
   x['uri'] = x['uri'].replace('eionet.europa.eu','eionet.eu.int')
   return x

return map(inline_replace, container.dataflow_rod())
