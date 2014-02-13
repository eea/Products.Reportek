## Script (Python) "copyFilesFromPreviousDelivery"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=previous_delivery
##title=
##
request = container.REQUEST
response =  request.RESPONSE

env_current = context.getMySelf()

prev_env = context.restrictedTraverse(previous_delivery)

if prev_env.objectIds('Report Document'):
  env_current.manage_copyDelivery(previous_delivery)
  request.SESSION.set('note_text', 'The file(s) were copied to this envelope successfully')
else:
  request.SESSION.set('note_text', 'No files available in the chosen envelope! Nothing copied.')

request.SESSION.set('note_content_type', 'text/html')
request.SESSION.set('note_title', 'Note')
response.redirect('note')
