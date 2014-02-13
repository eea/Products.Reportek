## Script (Python) "resultsdataflow_accepted"
##bind container=container
##bind context=context
##bind namespace=_
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Support function - determines if the envelope is accepted
##
#from Products.PythonScripts.standard import html_quote


notAccepted = 0
for fileObj in context.objectValues('Report Feedback'):
    if fileObj.title in ("Data delivery was not acceptable", "Non-acceptance of F-gas report"):
        notAccepted = 1

if context.released:
    if notAccepted > 0:
        print '''<td style="background-color:#ff8080">No</td>'''
    else:
        print '''<td>Yes</td>'''
else:
    print '''<td>Not released</td>'''
return printed
