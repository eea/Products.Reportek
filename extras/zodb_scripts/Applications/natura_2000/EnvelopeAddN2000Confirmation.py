# flake8: noqa
# Script (Python) "EnvelopeAddN2000Confirmation"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=workitem_id, REQUEST
# title=Add a Natura 2000 confirmation of receipt
##
from DateTime import DateTime

for x in context.getMySelf().objectValues('Workitem'):  # noqa: F821
    if x.activity_id == 'Draft':
        luzr = x.actor
ldapusername = context.getMySelf().getLDAPUserCanonicalName(  # noqa: F821
    context.getMySelf().getLDAPUser(luzr))  # noqa: F821
if not ldapusername:
    ldapusername = luzr

l_ret = """
<p>
European Environment Agency<br />
Kongens Nytorv 6<br />
DK 1050 Copenhagen K
</p>

<br />
<p><strong>To Whom It May Concern</strong></p>

<br />
<p>This is a confirmation of receipt for the electronic Natura 2000 national
 data submissions under the Birds Directive (79/409/EEC) and Habitats
  Directive (92/43/EEC)
</p>
<p>Information on Natura 2000 sites (SPAs)</p>
<p>Information on Natura 2000 sites (SCIs)</p>
<p>
The following delivery has been submitted for <strong>%s</strong> to the
 Reportnet Central Data Repository (CDR) and was finalised on
  <strong>%s</strong>.
</p>

<table>
<tr><td>Envelope:</td><td>%s</td></tr>
<tr><td>Location:</td><td><a href="%s">%s</a></td></tr>
</table>

<p>List of files:</p>

<ol>""" % (context.getMySelf().getCountryName(),  # noqa: F821
           DateTime().strftime('%d %B %Y'),
           context.getMySelf().title_or_id(),  # noqa: F821
           context.getMySelf().absolute_url(),  # noqa: F821
           context.getMySelf().absolute_url())  # noqa: F821

documents_list = context.getMySelf().objectValues(  # noqa: F821
    ['Report Document', 'Report Hyperlink'])
documents_list.sort(key=lambda ob: ob.getId().lower())
for f in documents_list:
    l_ret += '<li>%s</li>' % f.title_or_id()

l_ret += """
</ol>

<p>
The above-mentioned files were submitted by user: %s
</p>
<p>
In order to officially confirm this electronic data submission, please append
 this receipt to the communication from your
 Permanent Representation to the European Union to the European Commission.
</p>
<p><em>
This confirmation is electronically generated by the Reportnet system and
 therefore not signed.
</em></p>
""" % ldapusername

context.getMySelf().manage_addFeedback(  # noqa: F821
    title="Natura 2000 electronic data submission",
    feedbacktext=l_ret, automatic=1, content_type='text/html')
context.getMySelf().completeWorkitem(workitem_id)  # noqa: F821
