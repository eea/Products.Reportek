## Script (Python) "AAA_update_feedback_items"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
for e in container.Catalog(meta_type='Report Envelope', dataflow_uris=['http://rod.eionet.eu.int/obligations/30', 'http://rod.eionet.eu.int/obligations/29', 'http://rod.eionet.eu.int/obligations/14', 'http://rod.eionet.eu.int/obligations/28']):
 eo = e.getObject()
 print eo.dataflow_uris
 print '\n'

return printed
