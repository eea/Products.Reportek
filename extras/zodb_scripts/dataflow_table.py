## Script (Python) "dataflow_table"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
top = container.REQUEST.PARENTS[-1]
return top.obligations.list_obligations()
