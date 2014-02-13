## Script (Python) "EnvelopeCreateNewDelivery"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=In case of errors, create new envelope and copy the files there
##
col = context.getMySelf().getParentNode()
current_env = context.getMySelf()
new_env = col.manage_addEnvelope(title='%s - Redelivery' % current_env.title, descr='', year=current_env.year, endyear=current_env.endyear, partofyear=current_env.partofyear, locality=current_env.locality, REQUEST=None, previous_delivery=current_env.absolute_url(1))
