# flake8: noqa
# Script (Python) "EnvelopeAdd_Art17_GR_Instancefile"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
# title=Add an empty instance
##
# Notice: Maintain the instancefile under /xmlexports, then cut-and-paste it to here
# when changed
transmap = string.maketrans(' ', '-')

filename = "general-report.xml"
title = "General report for Art 17"
filecontent = []

bioregions = {
    'ALP': 'Alpine',
    'ATL': 'Atlantic',
    'BOR': 'Boreal',
    'CON': 'Continental',
    'MED': 'Mediterranean',
    'MAC': 'Macaronesian',
    'PAN': 'Pannonian',
    'ATS': 'Atlantic sea',
    'BLT': 'Baltic',
    'MDS': 'Mediterranean Sea'
}


filecontent.append("""<?xml version="1.0" encoding="UTF-8"?>
<report xml:lang="en" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd">
  <legal-framework label="1. Legal Framework">
    <legal-texts label="List of legal texts that transpose the Directive at national and/or regional level (Can be replaced by Internet address)"/>
  </legal-framework>
""")
for r in ['ALP', 'ATL', 'BOR']:
    filecontent.append("""
   <regional label="2. State of designation of Natura 2000">
        <region label="Biogeographic region" desc="%s">%s</region>
    <terrestrial label="Terrestrial">
      <community-importance>
        <number label="Number of sites of community importance"/>
        <area label="Area of sites of community importance (km2)"/>
      </community-importance>
      <areas-of-conservation>
        <number label="Number of special areas of conservation"/>
        <area label="Area of special areas of conservation (km2)"/>
      </areas-of-conservation>
    </terrestrial>
    <marine label="Marine">
      <community-importance>
        <number label="Number of sites of community importance"/>
        <area label="Area of sites of community importance (km2)"/>
      </community-importance>
      <areas-of-conservation>
        <number label="Number of special areas of conservation"/>
        <area label="Area of special areas of conservation (km2)"/>
      </areas-of-conservation>
    </marine>
  </regional>
""" % (bioregions[r], r))
filecontent.append("""
  <management-tools label="3. Management tools - Art. 6(1)">
    <management-plans label="3.1 Management plans &amp; management Bodies">
      <adopted-number label="Number of sites for which comprehensive management plans have been adopted"/>
      <created-number label="Number of sites for which management bodies have been established"/>
      <preparation-number label="Number of sites for which comprehensive management plans are in preparation (optional)"/>
      <plans-list label="List of sites for which comprehensive management plans have been adopted the management bodies created and the type of management.">
        <sitecode label="Site code"/>
        <sitename label="Site name"/>
        <type-management label="Type of management"/>
        <type-management-body label="Title of management body and year established"/>
        <preparation label="Management plans in preparation?"/>
      </plans-list>
    </management-plans>
    <other-planning label="3.2 Other planning instruments">
      <included-number label="Number of sites which do not have a dedicated management plan but for which nature conservation objectives have been included in the relevant territorial planning instruments"/>
      <other-list label="List of sites having other relevant territorial planning instruments">
        <sitecode label="Site code"/>
        <sitename label="Site name"/>
        <type-plan label="Type of plan"/>
        <coverage label="% site covered by planning instruments"/>
      </other-list>
    </other-planning>
    <non-planning label="3.3 Non-planning instruments">
      <number-non-plan label="Number of sites for which nature conservation objectives are not defined in a territorial planning instrument (dedicated management plan or other) but where other management instruments have been put in place"/>
      <not-plan-list label="List of sites, having other management instruments, that are not territorial planning">
        <sitecode label="Site code"/>
        <sitename label="Site name"/>
        <type-instrument label="Type of instrument"/>
        <coverage label="% of site covered by non-planning instruments"/>
      </not-plan-list>
    </non-planning>
  </management-tools>
  <conservation-measures label="4. Conservation measures - Art. 6(1) - and evaluation of their impact on the conservation status - Art. 17(1)">
    <description label="General description of the main conservation measures taken (overview at national level, not detailed descriptions site by site)"/>
    <impact label="Impact of those measures on conservation status -general overview at national level, indicating species or habitats affected by the measures, impact on conservation status and area concerned. (optional)"/>
    <published label="Published reports and/or websites (optional)"/>
  </conservation-measures>
  <deterioration-measures label="5. Measures to avoid deterioration of habitats/habitats of species &amp; disturbance of species - Art. 6(2)">
    <description label="General description of the main measures taken (overview at national level, not detailed descriptions site by site)"/>
    <published label="Published reports and/or websites (optional)"/>
  </deterioration-measures>
  <plan-measures label="6. Measures taken in relation to approval of plans &amp; projects - Art. 6(3,4)">
    <necessary-number label="Number of project/plans for which compensation measures were necessary"/>
    <requested-number label="Number of project/plans for which a Commission opinion was requested"/>
    <necessary-list label="List of sites affected by projects/plans for which compensation measures were necessary">
      <sitecode label="Sitecode"/>
      <sitename label="Site name"/>
      <project-type label="Type of project/plan"/>
      <commission-opinion label="Was the Commission opinion requested?"/>
    </necessary-list>
    <impact label="Impact of projects in need of compensation measures on conservation status (general overview at national level indicating species or habitats affected by the projects, impact of the projects and of the compensations measures, separately if possible, area concerned and whether a followup of the compensation measures was carried out) - optional"/>
  </plan-measures>
  <financing label="7. Financing - Art 8 (optional)">
    <estimated-total-annual-costs currency="EUR" label="Estimated total annual costs for managing Natura 2000 sites"/>
    <maintenance-measures label="Measures essential for the maintenance or re-establishment at a favourable conservation status of the priority natural habitat types and priority species (overview at national level) - Art. 8(2)"/>
    <estimated-annual-costs currency="EUR" label="Estimated annual costs for measures covered by Art. 8(2)"/>
    <cofinancing-by-eu currency="EUR" label="Co-financing provided by the EU for measures covered by Art. 8(2)"/>
    <specieslist label="List of Co-financing per priority species and priority natural habitats">
      <speciescode label="Species code"/>
      <speciesname label="Species name"/>
      <habitatcode label="Habitat code"/>
      <co-financing label="Co-financing" currency="EUR"/>
      <measures label="Measure(s)"/>
      <published label="Published reports or websites"/>
    </specieslist>
  </financing>
  <coherence-measures label="8. Measures taken to ensure coherence of the Network - Art 10 (optional)">
    <description label="General description of the main measures taken (overview at Memo national level, not detailed descriptions site by site)"/>
    <published label="Published reports or websites"/>
  </coherence-measures>
  <surveillance-system label="9. Measures taken to establish a surveillance system - Art 11">
    <description label="Main measures undertaken to establish a system to monitor the conservation status of natural habitats and species referred to in Art.2 of the directive"/>
    <published label="Published reports or websites (optional)"/>
  </surveillance-system>
  <protection-measures label="10. Measures taken to ensure the protection of species (Arts. 12 to 16)">
    <requisites label="Requisite measures taken to establish a system of strict protection of Annex IV species? List them by group of species or by species if appropriate">
      <description label="Protection measures"/>
      <published label="Published reports or websites (optional)"/>
      <speciescode label="Species code"/>
      <speciesname label="Species name/group"/>
    </requisites>
    <control-systems label="Does a control system exist for the incidental capture and killing of species (Article 12(4)), which species are concerned and how is it ensured that there will not be a significant negative impact on those species?">
      <speciescode label="Species code"/>
      <speciesname label="Species name"/>
      <control-system label="Control system"/>
      <impact label="Impact of capture or killing"/>
    </control-systems>
    <taking-measures label="What are the general main measures established to deal with the taking/exploitation in the wild of specimens of wild species of Annex V?"/>
    <species-taking label="Which species are concerned taking/exploitation">
      <speciescode label="Species code"/>
      <speciesname label="Species name"/>
    </species-taking>
    <indiscriminate-means label="What type of control exists to ensure that indiscriminate means (see Article 15) of capture and killing of the species of Annex IVa) and Va) are not used?"/>
  </protection-measures>
  <supporting-measures label="11. Supporting measures and additional provisions (optional)">
    <main-efforts label="Research (Art. 18) general description of the main efforts and results obtained (identify major projects)"/>
    <reintroduction-of-species label="(Re-)introduction of species (Art 22.a,)">
      <speciescode label="Species code"/>
      <speciesname label="Species name"/>
      <period label="Re-introduction period"/>
      <successful label="Was the re-introduction successful?"/>
      <fcs label="Is the species at FCS?"/>
    </reintroduction-of-species>
    <introduction-of-nonnative-species label="Deliberate introduction of non-native species (Art 22.b):">
      <speciesname label="Species name"/>
      <speciestaxo label="Taxonomic reference"/>
      <habitats label="Annex I habitats concerned by introduction"/>
      <annexes label="Annexes II, IV or V species concerned"/>
      <period label="Introduction period"/>
      <measures label="Regulation measures taken to avoid threats/damages"/>
      <description label="Education &amp; information (Art. 22 c) general description of the main measures taken"/>
    </introduction-of-nonnative-species>
  </supporting-measures>
</report>
""")
context.manage_addDocument(
    filename, title, ''.join(filecontent), 'text/xml', '')

context.completeWorkitem(workitem_id)
