request = container.REQUEST
RESPONSE =  request.RESPONSE

for x in container.WorkflowEngine.objectValues('Process'):
 for y in x.objectValues('Activity'):
  if y.application == 'EnvelopeRejectOrAccept':
   print y.absolute_url()
return printed
