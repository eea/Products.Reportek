# Script (Python) "EnvelopeDecideStartActivity"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=workitem_id, REQUEST
# title=Decides what activity should start the envelope
##
request = container.REQUEST  # noqa: F821
user = request['AUTHENTICATED_USER']
ret = ''

if 'Preparer' in user.getRolesInContext(context.getMySelf()):  # noqa: F821
    request.set('role', 'Preparer')
# elif 'Reporter' in user.getRolesInContext(context.getMySelf()):
else:
    request.set('role', 'Reporter')
