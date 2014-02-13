## Script (Python) "check_envelope_before_release"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
request = container.REQUEST
RESPONSE =  request.RESPONSE

if len(context.objectIds('Report Document')) == 0 or context.partofyear not in ['April', 'May', 'June', 'July', 'August','September']:
    return 0

return 1
