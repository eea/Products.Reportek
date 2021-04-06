# Script (Python) "AA_second_migration_script"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
request = container.REQUEST

for env_cat in container.Catalog(meta_type='Report Envelope'):
    env = container.Catalog.getobject(env_cat.data_record_id_)
    l_count = 0
    for w in env.objectValues('Workitem'):
        if l_count <= int(w.id):
            l_count = int(w.id)
            l_lastworkitem = w

    l_last_date = l_lastworkitem.lastActivityDate()
    if l_last_date.lessThan(DateTime() - 28) and l_lastworkitem.activity_id == 'Released' and l_lastworkitem.status == 'inactive':
        request.set('inspectresult', 'Finish')
        env.activateWorkitem(l_lastworkitem.id, actor='openflow_engine')
        env.completeWorkitem(l_lastworkitem.id)
        print env.absolute_url(0) + ': ' + l_lastworkitem.id

return printed
