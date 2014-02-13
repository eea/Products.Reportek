## Script (Python) "get_webforms_for_obl"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=obligation
##title=
##
dm_list = []
for dm_item in context.DataflowMappings.objectValues('Reportek Dataflow Mapping Record'):
    if dm_item.has_webForm == 'on' and dm_item.dataflow_uri == obligation:
        dm_list.append( (dm_item.schema_url, dm_item.title_or_id()) )
return dm_list
