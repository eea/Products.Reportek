request = container.REQUEST
user = request['AUTHENTICATED_USER']
ret = ''

if 'Preparer' in user.getRolesInContext(context):
  request.set('role', 'Preparer')
#elif 'Reporter' in user.getRolesInContext(context):
else:
  request.set('role', 'Reporter')
