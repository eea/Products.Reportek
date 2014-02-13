## Script (Python) "send_mails_password"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Send the emails out PASSWORD
##
from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE =  request.RESPONSE

# We can't handle national characters in headers.
def emailComment(s):
    if unicode(s,'utf-8').encode('ascii','ignore') != s:
        return ''
    return ' (' + s.replace('(','[').replace(')',']') + ')'

for row in context.recipients_username():
    recipients = ['BDR.helpdesk@eea.europa.eu','ods.reporting@eea.europa.eu']
    contactline = row[4]

    contactmail = row[5] + emailComment(row[4])
    recipients.append(row[5])
    if row[6] != '':
        contactmail = contactmail + "," + row[6]
        recipients.append(row[6])

    print "Sending to %s: %s" % (row[1] , contactmail)

#   recipients=['soren.roug@eea.europa.eu']

    context.MailHost.send(context.render_message_password(context, context.REQUEST,
                PASSWORD=row[1], COUNTRY=row[2], COMPANY=context.utf8escape(html_quote(row[3])),
                CONTACT=context.utf8escape(html_quote(contactline),1),
                CONTACTEMAIL=contactmail),
        recipients, 
      'BDR.helpdesk@eea.europa.eu (BDR Helpdesk)',
     'ODS reporting: %s / %s - Password information' % (row[3], row[2]))
return printed
