## Script (Python) "ReceiptConfirmationNegative"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Data delivery is not acceptable
##
from DateTime import DateTime
l_envelope = context.getMySelf()

def getActorDraft():
    latestDraftWokitem = [wi for wi in context.getListOfWorkitems() if wi.activity_id == 'Draft'][-1]
    return latestDraftWokitem.actor

def getFeedbackForEnvelope():
    return [x.absolute_url() for x in l_envelope.objectValues('Report Feedback') if x.title.find('envelope') > -1][0]

def getFeedbackForFiles(ptype):
    if ptype == 'species':
        lschema = 'http://bd.eionet.europa.eu/schemas/Art12Art17_reporting_2013/art17_species.xsd'
    elif ptype == 'birds':
        lschema = 'http://bd.eionet.europa.eu/schemas/Art12Art17_reporting_2013/art12_birds.xsd'
    elif ptype == 'red_lists':
        lschema = 'http://bd.eionet.europa.eu/schemas/Art12Art17_reporting_2013/art12_birds.xsd'
    else:
        lschema = 'http://bd.eionet.europa.eu/schemas/Art12Art17_reporting_2013/art17_habitats.xsd'
    lfiles = [x for x in l_envelope.objectValues('Report Document') if x.xml_schema_location == lschema]
    lret = []
    for x in lfiles:
        lret.extend(['<a href="%s">%s</a>' % (f.absolute_url(), f.title_or_id()) for f in l_envelope.objectValues('Report Feedback') if f.document_id == x.id and f.title.find('XML Schema validation') != -1])
    if not lret:
         return '(no feedback available for the %s report)' % ptype
    return '(see %s)' % ', '.join(lret)

list_of_obligations = []

for obl in context.dataflow_uris:
    list_of_obligations.append("""<strong>%s</strong> (<a href="%s">%s</a>)""" % (context.dataflow_lookup(obl)['TITLE'], obl.replace('eionet.eu.int','eionet.europa.eu'), obl.replace('eionet.eu.int','eionet.europa.eu')))

obligations_para = "<br/>\n".join(list_of_obligations)

l_ret_head = """
<p><strong>Data is refused</strong></p>

<p>Your delivery can not be accepted as one or more of the acceptance conditions were not met:</p>
"""

# Article 17
if l_envelope.dataflow_uris == ['http://rod.eionet.europa.eu/obligations/269']:
    l_ret_body = """
<ul>
<li>not all mandatory files (including projection file for spatial data) have been submitted or are valid (see <a href="%s">AutomaticQA result for envelope</a>)</li>
<li>habitats report does not conform to the data model defined in the XML schema %s</li>
<li>species report does not conform to the data model defined in the XML schema %s</li>
</ul>
""" % (getFeedbackForEnvelope(), getFeedbackForFiles('habitats'), getFeedbackForFiles('species'))
# Article 12
elif l_envelope.dataflow_uris == ['http://rod.eionet.europa.eu/obligations/278']:
    l_ret_body = """
<ul>
<li>not all mandatory files (including projection file for spatial data) have been submitted or are valid (see <a href="%s">AutomaticQA result for envelope</a>)</li>
<li>bird species report does not conform to the data model defined in the XML Schema %s</li>
</ul>
""" % (getFeedbackForEnvelope(), getFeedbackForFiles('birds'))
# Red lists
elif l_envelope.dataflow_uris == ['http://rod.eionet.europa.eu/obligations/690']:
    l_ret_body = """
<ul>
<li>not all mandatory files (birds reports and birds check-list) have been submitted or are valid (see <a href="%s">AutomaticQA result for envelope</a>)</li>
<li>bird species report does not conform to the data model defined in the XML Schema %s</li>
</ul>
""" % (getFeedbackForEnvelope(), getFeedbackForFiles('red_lists'))

# Article 17 or 12
if l_envelope.dataflow_uris in [['http://rod.eionet.europa.eu/obligations/269'], ['http://rod.eionet.europa.eu/obligations/278']]:
    l_ret_foot = """
<p>The conditions for accepting Member State deliveries are outlined in Annex 1 "Rules for the acceptance of Member State deliveries in Reportnet" of the Delivery Manual for Articles 12 and 17.</p>
<p>For additional information contact <a href="mailto:reportingart12art17@mnhn.fr">reportingart12art17@mnhn.fr</a></p>

<p>The delivery was submitted by: <em>%s</em> (user name: <em>%s</em>)</p>

""" % (context.getLDAPUserCanonicalName(context.getLDAPUser(getActorDraft())), getActorDraft())
# Red lists
else:
    l_ret_foot = """
<p>The conditions for accepting deliveries are outlined in Annex 1 "Rules for the acceptance of Red List deliveries in Reportnet" of the Delivery Manual for European Red List of Birds.</p>
<p>For additional information contact <a href="mailto:reportingart12art17@mnhn.fr">reportingart12art17@mnhn.fr</a></p>

<p>The delivery was submitted by: <em>%s</em> (user name: <em>%s</em>)</p>

""" % (context.getLDAPUserCanonicalName(context.getLDAPUser(getActorDraft())), getActorDraft())

l_ret = l_ret_head + l_ret_body + l_ret_foot

context.manage_addFeedback(title="Automatic validation: Data delivery was not acceptable", feedbacktext=l_ret, automatic=1, content_type='text/html')
context.completeWorkitem(workitem_id)
