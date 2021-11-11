# flake8: noqa
# Script (Python) "EnvelopeCreateGeneralReportFile"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
##parameters=language, region=[]
# title=Art17: Creates a new instance file
##
#
transmap = string.maketrans(' ', '-')

request = context.REQUEST
response = request.RESPONSE
SESSION = request.SESSION

filename = "general-report.xml"
title = "General report for art 17"
filecontent = []
err_msg = []

bioregions = {
    'ALP': 'Alpine',
    'ATL': 'Atlantic',
    'BOR': 'Boreal',
    'CON': 'Continental',
    'MED': 'Mediterranean',
    'MAC': 'Macaronesian',
    'PAN': 'Pannonian',
    'MATL': 'Atlantic ocean',
    'MBAL': 'Baltic sea',
    'MMED': 'Mediterranean sea',
    'MMAC': 'Macaronesian/Atlantic ocean'
}

if len(region) < 1:
    err_msg.append('You have to select at least one region!')

if len(err_msg) > 0:
    SESSION.set('err_msg', err_msg)
    SESSION.set('language', language)
    SESSION.set('region', region)
    return response.redirect('EnvelopeCreateGeneralReportFileForm')

l_countryname = 'Unspecified'
l_countrycode = ''
for country_obj in container.localities_table():
    if country_obj['uri'] == context.country:
        l_countryname = country_obj['name']
        l_countrycode = country_obj['iso']
        break

filecontent.append("""<?xml version="1.0" encoding="UTF-8"?>
<report xml:lang="%s" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd">
	<member-state label="Member state" countrycode="%s">%s</member-state>
	<legal-framework label="1. Legal Framework">
		<legal-texts label="List of legal texts that transpose the Directive at national and/or regional level (Can be replaced by Internet address where the text is published and a short title)"/>
	</legal-framework>
""" % (language, l_countrycode, l_countryname))
for r in region:
    filecontent.append("""
	<regional label="2. State of designation of Natura 2000">
		<region label="Biogeographic region or marine region" desc="%s">%s</region>
		<community-importance label="Sites of community importance">
			<total label="Total">
				<number label="Number of sites of community importance"/>
				<area label="Area of sites of community importance (km2)"/>
			</total>
			<marine label="Marine">
				<number label="Number of sites of community importance having a marine component"/>
				<area label="Area of sites of community importance having a marine component (km2)"/>
			</marine>
		</community-importance>
		<areas-of-conservation label="Special areas of conservation">
			<total label="Total">
				<number label="Number of special areas of conservation"/>
				<area label="Area of special areas of conservation (km2)"/>
			</total>
			<marine label="Marine">
				<number label="Number of special areas of conservation having a marine component"/>
				<area label="Area of special areas of conservation having a marine component (km2)"/>
			</marine>
		</areas-of-conservation>
  </regional>
""" % (bioregions[r], r))
filecontent.append("""
	<management-tools label="3. Management tools - Art. 6(1)">
		<management-plans label="3.1 Management plans and Management bodies">
			<adopted-number label="Number of sites for which comprehensive management plans have been adopted"/>
			<preparation-number label="Number of sites for which comprehensive management plans are in preparation (optional)"/>
			<created-number label="Number of sites for which management bodies have been established"/>
			<plans-list label="List of sites">
				<sitecode label="Site code"/>
				<sitename label="Site name"/>
				<type-management label="Title of comprehensive management plan and year adopted"/>
				<preparation label="Comprehensive management plan in preparation?"/>
				<type-management-body label="Title of management body and year established"/>
			</plans-list>
		</management-plans>
		<other-planning label="3.2 Other territorial planning instruments">
			<included-number label="Number of sites which do not have a comprehensive management plan but for which nature conservation objectives have been included in the relevant territorial planning instruments"/>
			<other-list label="List of sites">
				<sitecode label="Site code"/>
				<sitename label="Site name"/>
				<type-plan label="Title and year of territorial planning instrument"/>
				<coverage label="% site covered by instrument">100</coverage>
			</other-list>
		</other-planning>
		<non-planning label="3.3 Non-territorial planning instruments">
			<number-non-plan label="Number of sites for which nature conservation objectives are not defined in a territorial planning instrument (nor in a comprehensive management plan) but where other management instruments have been put in place"/>
			<not-plan-list label="List of sites">
				<sitecode label="Site code"/>
				<sitename label="Site name"/>
				<type-instrument label="Title and year of non-territorial planning instrument"/>
				<coverage label="% of site covered by instrument">100</coverage>
			</not-plan-list>
		</non-planning>
	</management-tools>
	<conservation-measures label="4. Conservation measures - Art. 6(1) - and evaluation of their impact on the conservation status - Art. 17(1)">
		<description label="General description of the main conservation measures taken (overview at national level, not detailed descriptions site by site)"/>
		<impact label="Impact of those measures on conservation status -general overview at national level, indicating species or habitat types affected by the measures, impact on conservation status and area concerned. (optional)"/>
		<published label="Published reports and/or websites (optional)"/>
	</conservation-measures>
	<deterioration-measures label="5. Measures to avoid deterioration of habitat types/habitats of species and disturbance of species - Art. 6(2)">
		<description label="General description of the main measures taken (overview at national level, not detailed descriptions site by site)"/>
		<published label="Published reports and/or websites (optional)"/>
	</deterioration-measures>
	<plan-measures label="6. Measures taken in relation to approval of plans and projects - Art. 6(3,4)">
		<necessary-number label="Number of project/plans for which compensation measures were necessary"/>
		<requested-number label="Number of project/plans for which a Commission opinion was requested"/>
		<necessary-list label="List of sites affected by projects/plans for which compensation measures were necessary">
			<sitecode label="Site code"/>
			<sitename label="Site name"/>
			<project-type label="Title and year of project/plan"/>
			<commission-opinion label="Was the Commission opinion requested?"/>
		</necessary-list>
		<impact label="Impact of projects in need of compensation measures on conservation status (general overview at national level indicating species or habitat types affected by the projects, impact of the projects and of the compensation measures, separately if possible, area concerned and whether a followup of the compensation measures was carried out) - optional"/>
	</plan-measures>
	<financing label="7. Financing - Art 8 (optional)">
		<estimated-average-annual-costs year="2001" currency="EUR" label="Estimated total annual costs for managing Natura 2000 sites during the reporting period"/>
		<estimated-average-annual-costs year="2002" currency="EUR" label="Estimated total annual costs for managing Natura 2000 sites during the reporting period"/>
		<estimated-average-annual-costs year="2003" currency="EUR" label="Estimated total annual costs for managing Natura 2000 sites during the reporting period"/>
		<estimated-average-annual-costs year="2004" currency="EUR" label="Estimated total annual costs for managing Natura 2000 sites during the reporting period"/>
		<estimated-average-annual-costs year="2005" currency="EUR" label="Estimated total annual costs for managing Natura 2000 sites during the reporting period"/>
		<estimated-average-annual-costs year="2006" currency="EUR" label="Estimated total annual costs for managing Natura 2000 sites during the reporting period"/>
		<measures label="Measures undertaken for the maintenance or re-establishment at a favourable conservation status of the PRIORITY habitat types and PRIORITY species - Art. 8(2)"/>
		<estimated-annual-costs year="2001" currency="EUR" label="Estimated annual costs for measures covered by Art. 8(2)"/>
		<estimated-annual-costs year="2002" currency="EUR" label="Estimated annual costs for measures covered by Art. 8(2)"/>
		<estimated-annual-costs year="2003" currency="EUR" label="Estimated annual costs for measures covered by Art. 8(2)"/>
		<estimated-annual-costs year="2004" currency="EUR" label="Estimated annual costs for measures covered by Art. 8(2)"/>
		<estimated-annual-costs year="2005" currency="EUR" label="Estimated annual costs for measures covered by Art. 8(2)"/>
		<estimated-annual-costs year="2006" currency="EUR" label="Estimated annual costs for measures covered by Art. 8(2)"/>
		<cofinancing-by-eu currency="EUR" label="Co-financing provided by the EU for measures covered by Art. 8(2)"/>
		<cofinancing-list label="List of co-financed measures concerning priority species and priority habitat types">
			<source label="Co-financing source"/>
			<co-financing label="Amount" currency="EUR"/>
			<measures label="Project title and year"/>
			<published label="Published reports or websites"/>
		</cofinancing-list>
	</financing>
	<coherence-measures label="8. Measures taken to ensure coherence of the Network - Art 10 (optional)">
		<description label="General description of the main measures taken (overview at national level, not detailed descriptions site by site)"/>
		<published label="Published reports or websites"/>
	</coherence-measures>
	<surveillance-system label="9. Measures taken to establish a surveillance system - Art 11">
		<description label="Main measures undertaken to establish a system to monitor the conservation status of natural habitats and species referred to in Art.2 of the directive"/>
		<published label="Published reports or websites (optional)"/>
	</surveillance-system>
	<protection-measures label="10. Measures taken to ensure the protection of species (Arts. 12 to 16)">
		<requisites label="Requisite measures taken to establish a system of strict protection of Annex IV species.">
			<measures label="Protection measures"/>
			<published label="Published reports or websites (optional)"/>
			<species-names label="Species names/groups"/>
		</requisites>
		<control-systems label="Control systems for the incidental capture and killing of species (Art. 12(4))">
			<control-system label="Control system"/>
			<impact label="How does the control system ensure that there will not be a negative impact on the species?"/>
			<species-names label="Species names"/>
		</control-systems>
		<species-taking label="General main measures established to deal with the taking/exploitation in the wild of specimens of wild species of Annex V (Art. 14)">
			<measures label="General main measures"/>
			<species-names label="Species names"/>
		</species-taking>
		<indiscriminate-means label="Types of controls to ensure that indiscriminate means of capture and killing of the species of Annex IVa) and Va) are not used (Art. 15)">
			<type-of-control label="Type of control"/>
			<species-names label="Species names"/>
		</indiscriminate-means>
	</protection-measures>
	<supporting-measures label="11. Supporting measures and additional provisions (optional)">
		<research label="Research (Art. 18)">
			<main-efforts label="General description of the main efforts and results obtained (identify major projects)"/>
			<published label="Published reports or websites"/>
		</research>
		<reintroduction-of-species label="(Re-)introduction of species (Art 22.a)">
			<species-name label="Species name"/>
			<species-author label="Species author (year)"/>
			<period label="Re-introduction period"/>
			<successful label="Was the re-introduction successful?"/>
			<fcs label="Is the species at FCS?"/>
		</reintroduction-of-species>
		<introduction-of-nonnative-species label="Deliberate introduction of non-native species (Art 22.b)">
			<species-name label="Species name"/>
			<species-author label="Species author (year)"/>
			<habitats label="Annex I habitat types concerned by introduction"/>
			<species-concerned label="Annexes II, IV or V species concerned"/>
			<period label="Introduction period"/>
			<measures label="Regulation measures taken to avoid threats/damages"/>
			<description label="General description of the main measures taken"/>
		</introduction-of-nonnative-species>
		<education label="Education and information (Art. 22.c)">
			<measures label="General description of the main measures taken"/>
			<published label="Published reports or websites"/>
		</education>
	</supporting-measures>
</report>
""")
context.manage_addDocument(
    filename, title, ''.join(filecontent), 'text/xml', '')
return context.index_html()
