for brain in container.Catalog(meta_type='Report Feedback'):
  feedback = container.Catalog.getobject(brain.data_record_id_)
  #feedback.update06092009()
  #print feedback.absolute_url()
  for comm in feedback.objectValues('Report Feedback Comment'):
     print comm.absolute_url()
print 'done'
return printed
