## Script (Python) "EnvelopeAddReceiptConfirmationErrors"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Data delivery was not acceptable
##
from DateTime import DateTime
env = context.getMySelf()

def getActorDraft():
    latestDraftWokitem = [wi for wi in env.getListOfWorkitems() if wi.activity_id == 'Draft'][-1]
    return latestDraftWokitem.actor

def getNextEnvelope():
    return [x for x in env.getParentNode().objectValues('Report Envelope') if x.creation_time.greaterThan(env.creation_time) and x.title.startswith(env.title)][-1]

list_of_obligations = []

for obl in list(env.dataflow_uris):
    list_of_obligations.append("""<strong>%s</strong> (<a href="%s">%s</a>)""" % (context.dataflow_lookup(obl)['TITLE'], obl, obl))

obligations_para = "<br/>\n".join(list_of_obligations)

l_ret = """
<p>
European Environment Agency<br />
Kongens Nytorv 6<br />
DK 1050 Copenhagen K
</p>

<br />

<p><strong i18n:translate="">To Whom It May Concern</strong></p>

<p i18n:translate="">This is a confirmation of receipt for data submissions by an undertaking under the European Reporting Obligation:</p>

<p>%s</p>

<p i18n:translate="">The following delivery has been submitted for <strong i18n:name="company-name">%s</strong> and was finalized on <strong i18n:name="release-date">%s</strong>.</p>

<table>
	<tr>
		<th i18n:translate="">Envelope:</th>
		<td>%s</td>
	</tr>
	<tr>
		<th i18n:translate="">Location:</th>
		<td><a href="%s">%s</a></td>
	</tr>
</table>

<p i18n:translate="">List of files:</p>

<ul>""" % (obligations_para, context.aq_parent.title, DateTime().strftime('%d %B %Y'), context.title_or_id(), context.absolute_url(), context.absolute_url())


documents_list = context.objectValues(['Report Document', 'Report Hyperlink'])
documents_list.sort(key=lambda ob: ob.getId().lower())
for f in documents_list:
    l_ret += '<li>%s</li>' % (f.title_or_id())
    if f.meta_type == 'Report Document':
        zip_files = context.getZipInfo(f)
        if zip_files:
            l_ret += '<div class="zip_content">'
            l_ret += '<em i18n:translate="">files contained inside the <span i18n:name="env-title">' + f.title_or_id() + '</span> archive:</em>'
            l_ret += '<ul>'
            for file in zip_files:
                l_ret += '<li>%s</li>' % file
            l_ret += '</ul>'
            l_ret += '</div>'
l_ret += """

</ul>

<p i18n:translate="">The above-mentioned files were submitted by: <em i18n:name="submitter-name">%s</em> (user name: <em i18n:name="submitter-username">%s</em>)</p>

<p style="color: red;" i18n:translate="">The reported data failed to pass some important quality checks and therefore is <strong>not acceptable</strong>. 
A list of errors can be found in the Feedback report of your submitted envelope. You need to make a new delivery after fixing these errors.</p>

<p i18n:translate="">To facilitate your re-submission a new envelope has been created at the following link and all the reported data/submitted files have been copied there:</p>

<p><a href="%s">%s</a>.</p>

<p i18n:translate="">Please use this newly created envelope to correct your data and make a re-submission to DG Clima and EEA.</p>

<p><em i18n:translate="">This confirmation letter is electronically generated by the Reportnet system and therefore not signed.</em></p>

""" % (context.getLDAPUserCanonicalName(context.getLDAPUser(getActorDraft())), getActorDraft(), getNextEnvelope().absolute_url(), getNextEnvelope().absolute_url())

context.manage_addFeedback(title="Data delivery was not acceptable", feedbacktext=l_ret, automatic=1, content_type='text/html')
context.completeWorkitem(workitem_id)