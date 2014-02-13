## Script (Python) "EnvelopeRetire"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
if context.is_active_for_me(REQUEST=REQUEST):
    context.completeWorkitem(workitem_id)
context.REQUEST.response.redirect('index_html')
