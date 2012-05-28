## Script (Python) "EnvelopeAddWasteInstancefiles"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Adds empty instance files for each obligation - currently not used
##
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
