## Script (Python) "EnvelopeDecideStartActivity"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Decides what activity should start the envelope
##
request = container.REQUEST
user = request['AUTHENTICATED_USER']
ret = ''

if 'Preparer' in user.getRolesInContext(context):
  request.set('role', 'Preparer')
#elif 'Reporter' in user.getRolesInContext(context):
else:
  request.set('role', 'Reporter')
