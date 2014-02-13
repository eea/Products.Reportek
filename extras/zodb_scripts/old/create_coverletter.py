## Script (Python) "create_coverletter"
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
context.manage_delObjects(context.objectIds('Report Feedback'))
context.EnvelopeNECCoverLetter(workitem_id='3', REQUEST=request)
RESPONSE.redirect('index_html')
