## Script (Python) "qa_resultsdataflow_feedbacks"
##bind container=container
##bind context=context
##bind namespace=_
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Support function - determines if the envelope is accepted
##
#from Products.PythonScripts.standard import html_quote


numFeedbacks= 0
for fileObj in context.objectValues('Report Feedback'):
    if fileObj.id[:12] == "AutomaticQA_":
        numFeedbacks += 1

#print '''<td>%d</td>''' % numFeedbacks
return numFeedbacks
