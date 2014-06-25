## Script (Python) "update_workitems_for_QA"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Copies description of QA workitems into the workitem log
##
for c in container.objectValues('Report Collection'):
 for e in container.Catalog(meta_type='Report Envelope', path=c.absolute_url(1)):
  env = e.getObject()
  for w in [x for x in env.objectValues('Workitem') if x.activity_id == 'AutomaticQA']:
   try:
    before_time = [x['time'] for x in w.event_log if x['event'] == 'assigned to openflow_engine'][0]
    w.addEventOnTime(container.EnvelopeQAApplication.decodeAppData(w, 'Automatic QA'), before_time)
    print w.event_log
   except:
    print 'skipped workitem ' + w.absolute_url() + '<br />'
return printed
