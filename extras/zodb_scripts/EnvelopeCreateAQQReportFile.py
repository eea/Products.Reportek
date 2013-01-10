## Script (Python) "EnvelopeCreateAQQReportFile"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=language='en', schema='',filename=''
##title=Air Quality: Creates a new instance file
##
# This script seems to cause a corruption of the reposit folder.
raise "This script has been blocked by administrator"

request = context.REQUEST
response = request.RESPONSE
SESSION = request.SESSION

err_msg = []

if not language: err_msg.append('Missing language parameter')
if not schema: err_msg.append('No schema given')

if len(err_msg) > 0:
    SESSION.set('err_msg', err_msg)
    return response.redirect(context.absolute_url())

filecontent = []
aqq_instances = context.emptyinstances.aqq

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form1.xsd":
    filename="aqq_form1.xml"
    title="Contact body, zone boundaries and revision information"
    filecontent.append(aqq_instances.form1(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form2.xsd":
    if not filename:
        filename="aqq_form2.xml"
    title="Delimination of zones and agglomerations"
    filecontent.append(aqq_instances.form2(language, context.getCountryCode()))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form3.xsd":
    filename="aqq_form3.xml"
    title="Stations and measuring methods"
    filecontent.append(aqq_instances.form3(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form4.xsd":
    filename="aqq_form4.xml"
    title="Stations used for assessment of ozone, including nitrogen dioxide and nitrogen oxides in relation to ozone"
    filecontent.append(aqq_instances.form4(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form5.xsd":
    filename="aqq_form5.xml"
    title="Stations and measurement methods used for the assessment of recommended volatile organic compounds, concentration and deposition of arsenic, cadmium, mercury , nickel, B(a)P and other relevant PAH at background locations and other relevant PAH  in ambient ai"
    filecontent.append(aqq_instances.form5(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form6.xsd":
    filename="aqq_form6.xml"
    title="Stations and measurement methods used for the assessment of other ozone precursor substances"
    filecontent.append(aqq_instances.form6(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form7.xsd":
    filename="aqq_form7.xml"
    title="Methods used to measure, sample and analyse PM10, PM2,5  ozone precursor substances, arsenic, cadmium, nickel, mercury, PAH: optional additional codes to be defined by the Member State"
    filecontent.append(aqq_instances.form7(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form8.xsd":
    filename="aqq_form8.xml"
    title="List of zones and agglomerations where levels exceed or do not exceed limit values"
    filecontent.append(aqq_instances.form8(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form9.xsd":
    filename="aqq_form9.xml"
    title="List of zones and agglomerations where levels exceed or do not exceed target values"
    filecontent.append(aqq_instances.form9(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form10.xsd":
    filename="aqq_form10.xml"
    title="List of zones in relation to assessment threshold exceedences and supplementary assessment"
    filecontent.append(aqq_instances.form10(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form11.xsd":
    filename="aqq_form11.xml"
    title="Individual exceedences of limit values and limit values plus margin of tolerance (MOT)"
    filecontent.append(aqq_instances.form11(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form12.xsd":
    filename="aqq_form12.xml"
    title="Reasons for individual exceedences: optional additional codes to be defined by the Member State"
    filecontent.append(aqq_instances.form12(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form13.xsd":
    filename="aqq_form13.xml"
    title="Individual exceedences of ozone thresholds"
    filecontent.append(aqq_instances.form13(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form14.xsd":
    filename="aqq_form14.xml"
    title="Exceedence of  target values"
    filecontent.append(aqq_instances.form14(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form15.xsd":
    filename="aqq_form15.xml"
    title="Annual statistics of ozone, arsenic, nickel, cadmium and benzo(a)pyrene"
    filecontent.append(aqq_instances.form15(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form16.xsd":
    filename="aqq_form16.xml"
    title="Annual average concentrations of ozone precursor substances, annual average concentrations of mercury and PAH compounds other than B(a)P, and total deposition of arsenic, cadmium, nickel, mercury and PAH compounds"
    filecontent.append(aqq_instances.form16(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form17.xsd":
    filename="aqq_form17.xml"
    title="Monitoring data on 10 minutes mean SO2 levels"
    filecontent.append(aqq_instances.form17(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form18.xsd":
    filename="aqq_form18.xml"
    title="Monitoring data on 24hr mean PM2,5 levels"
    filecontent.append(aqq_instances.form18(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form19.xsd":
    filename="aqq_form19.xml"
    title="Tabular results of and methods used for supplementary assessment"
    filecontent.append(aqq_instances.form19(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form20.xsd":
    filename="aqq_form20.xml"
    title="List of references to supplementary assessment methods referred to in Form 19"
    filecontent.append(aqq_instances.form20(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form21.xsd":
    filename="aqq_form21.xml"
    title="Exceedence of limit values of SO2 due to natural sources"
    filecontent.append(aqq_instances.form21(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form22.xsd":
    filename="aqq_form22.xml"
    title="Natural SO2 sources: optional additional codes to be defined by Member State"
    filecontent.append(aqq_instances.form22(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form23.xsd":
    filename="aqq_form23.xml"
    title="Exceedence of limit values of PM10 due to natural events"
    filecontent.append(aqq_instances.form23(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form24.xsd":
    filename="aqq_form24.xml"
    title="Exceedence of limit values of PM10 due to winter sanding"
    filecontent.append(aqq_instances.form24(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form25.xsd":
    filename="aqq_form25.xml"
    title="Consultations on transboundary pollution"
    filecontent.append(aqq_instances.form25(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form26.xsd":
    filename="aqq_form26.xml"
    title="Exceedences of limit values laid down in Directives 80/779/EEC, 82/884/EEC and 85/203/EEC to be reported under 1999/30/EC Article 9(6))"
    filecontent.append(aqq_instances.form26(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

if schema == "http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form27.xsd":
    filename="aqq_form27.xml"
    title="Reasons for exceedences of limit values laid down in Directives 80/779/EEC, 82/884/EEC and 85/203/EEC: optional additional codes to be defined by the Member State (1999/30/EC Article 9(6))"
    filecontent.append(aqq_instances.form27(language))
    context.getMySelf().manage_addDocument(filename, title, ''.join(filecontent), 'text/xml','')

edit_url = context.getWebQ_MenuEnvelope_URL() + '?language=En&envelope=' + context.getMySelf().absolute_url() + '&schema=' + schema
return response.redirect(edit_url)
