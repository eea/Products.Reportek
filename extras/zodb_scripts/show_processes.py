## Script (Python) "show_processes"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
for env_cat in container.Catalog(meta_type='Report Envelope'):
    env = container.Catalog.getobject(env_cat.data_record_id_)

    print env.process_path + ' ' + env.absolute_url(1)

return printed
