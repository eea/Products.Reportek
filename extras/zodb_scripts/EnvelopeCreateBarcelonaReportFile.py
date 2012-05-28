edit_url = context.getWebQ_MenuEnvelope_URL() + '?language=En&envelope=' + context.getMySelf().absolute_url() + '&schema=' + schema

transmap = string.maketrans(' ','-')

request = context.REQUEST
response = request.RESPONSE
SESSION = request.SESSION

filecontent = []
err_msg = []

barcelona_instances = context.emptyinstances.barcelona

if schema == "http://biodiversity.eionet.europa.eu/schemas/barcelona_convention/barcelona.xsd":
    filename="questionnaire_barcelona-report.xml"
    title="Barcelona Convention report"
    filecontent.append(barcelona_instances.generic(language))
    context.manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

elif schema == "http://biodiversity.eionet.europa.eu/schemas/barcelona_convention/dumping.xsd":
    filename="questionnaire_dumping-report.xml"
    title="Dumping Protocol report"
    filecontent.append(barcelona_instances.dumping(language))
    context.manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

elif schema == "http://biodiversity.eionet.europa.eu/schemas/barcelona_convention/hazardous.xsd":
    filename="questionnaire_hazardous-report.xml"
    title="Hazardous Waste Protocol report"
    filecontent.append(barcelona_instances.hazardous(language))
    context.manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

elif schema == "http://biodiversity.eionet.europa.eu/schemas/barcelona_convention/lbs.xsd":
    filename="questionnaire_lbs-report.xml"
    title="Land Based Sources Protocol report"
    filecontent.append(barcelona_instances.lbs(language))
    context.manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

elif schema == "http://biodiversity.eionet.europa.eu/schemas/barcelona_convention/offshore.xsd":
    filename="questionnaire_offshore-report.xml"
    title="Offshore Protocol report"
    filecontent.append(barcelona_instances.offshore(language))
    context.manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

elif schema == "http://biodiversity.eionet.europa.eu/schemas/barcelona_convention/prevention.xsd":
    filename="questionnaire_prevention-report.xml"
    title="Prevention and Emergency Protocol report"
    filecontent.append(barcelona_instances.prevention(language))
    context.manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

elif schema == "http://biodiversity.eionet.europa.eu/schemas/barcelona_convention/spa-biodiversity.xsd":
    filename="questionnaire_spa-biodiversity-report.xml"
    title="Specially Protected Areas and Biodiversity Protocol report"
    filecontent.append(barcelona_instances.spa(language))
    context.manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

elif len(err_msg) > 0:
    SESSION.set('err_msg', err_msg)
    SESSION.set('language', language)
    return response.redirect('EnvelopeCreateBarcelonaReportFileForm')

return response.redirect(edit_url)
