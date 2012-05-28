# Notice: Maintain the instancefile under /xmlexports

for du in context.dataflow_uris:
  dn = du.split('/')[-1]
  dt = context.dataflow_lookup(du)['TITLE']
  instance_parent = context.restrictedTraverse('emptyinstances/%s' % dn, None)
  if instance_parent and hasattr(instance_parent, 'instanceFile'):
    data_instance = instance_parent.instanceFile()
    if data_instance:
      context.manage_addDocument(id='questionnaire_%s.xml' % dn, title='%s questionnaire' % dt, file=data_instance.data, content_type='text/xml')

context.completeWorkitem(workitem_id)
