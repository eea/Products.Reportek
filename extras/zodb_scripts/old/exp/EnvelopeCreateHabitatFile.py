# flake8: noqa
# Script (Python) "EnvelopeCreateHabitatFile"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
##parameters=language, region=[], habitattype=None
# title=Art17: Creates a new instance file
##
# Notice: Maintain the instancefile under /xmlexports, then cut-and-paste it to here
# when changed
request = context.REQUEST
response = request.RESPONSE
SESSION = request.SESSION

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

if habitattype == None:
    err_msg.append('You have to select a habitat type!')

if len(err_msg) > 0:
    SESSION.set('err_msg', err_msg)
    SESSION.set('habitattype', habitattype)
    SESSION.set('language', language)
    SESSION.set('region', region)
    return response.redirect('EnvelopeCreateHabitatFileForm')

filename = "habitattype-%s.xml" % habitattype
title = "Habitat type questionnaire for habitat %s" % habitattype
# Look up the habitat title
for t in container.Art17habitattypes():
    if t[1] == habitattype:
        title = t[2]


def mapelem(elem):
    return """<map href="%s-%s.gml" rel_uri="/%s"/>""" % (elem, habitattype, context.absolute_url(1))


filecontent.append("""<?xml version="1.0" encoding="UTF-8"?>
<habitat xml:lang="%s" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/habitats.xsd" xmlns="">
  <habitatcode label="Habitat code">%s</habitatcode>
  <habitatname label="Habitat name">%s</habitatname>
  <regions label="Biogeographic regions and/or marine regions concerned within the member state">%s</regions>
  <national label="1. National level">
    <map-range label="1.1 Habitat range map">
      %s
    </map-range>
    <map-distribution label="1.2 Habitat distribution map">
      %s
    </map-distribution>
    <map-favourable-range label="1.3 Habitat favourable reference range map (optional)">
      %s
    </map-favourable-range>
    <map-favourable-distribution label="1.4 Habitat favourable reference area map (optional)">
      %s
    </map-favourable-distribution>
  </national>
""" % (language, habitattype, title, ' '.join(region), mapelem('map-range'), mapelem('map-distribution'), mapelem('map-favourable-range'), mapelem('map-favourable-distribution')))
for r in region:
    filecontent.append("""  <regional label="2. Biogeographical or marine level">
    <region label="2.1 Biogeographic region or marine region" desc="%s">%s</region>
    <published label="2.2 Published sources and/or websites"/>
    <range label="2.3 Range of the habitat in the biogeographic region or marine region">
      <surface-area label="2.3.1 Surface area of range in km2"/>
      <date label="2.3.2 Date of range determination"/>
      <quality label="2.3.3 Quality of data concerning range"/>
      <trend label="2.3.4 Range trend"/>
      <trend-magnitude label="2.3.5 Range trend magnitude in km2 (optional)"/>
      <trend-period label="2.3.6 Range trend period"/>
      <reasons label="2.3.7 Reasons for reported trend"/>
      <reasons-specify label="and/or specify"/>
    </range>
    <coverage label="2.4 Area covered by habitat in the biogeographic region or marine region">
      <surface-area label="2.4.1 Surface area of the habitat (km2)"/>
      <date label="2.4.2 Date of area estimation"/>
      <method label="2.4.3 Method used for area estimation"/>
      <quality label="2.4.4 Quality of data on habitat area"/>
      <trend label="2.4.5 Habitat trend"/>
      <trend-magnitude label="2.4.6 Habitat trend magnitude (km2)"/>
      <trend-period label="2.4.7 Habitat trend period"/>
      <reasons label="2.4.8 Reasons for reported trend"/>
      <reasons-specify label="and/or specify"/>
      <justification label="2.4.9 Justification of %% thresholds for trends (optional)"/>
      <pressures label="2.4.10 Main pressures"/>
      <threats label="2.4.11 Threats"/>
    </coverage>
    <complementary label="2.5 Complementary information">
      <favourable-range label="2.5.1 Favourable reference range (km2)"/>
      <favourable-area label="2.5.2 Favourable reference area (km2)"/>
      <typical-species label="2.5.3 Typical species">
          <speciesname label="Species name"/>
          <speciesauthor label="Species author (year)"/>
      </typical-species>
      <species-assessment label="2.5.4 Typical species assessment"/>
      <other-information label="2.5.5 Other relevant information (optional)"/>
    </complementary>
    <conclusion label="Conclusions">
      <conclusion-range label="(2.3) Range"/>
      <conclusion-area label="(2.4) Area"/>
      <conclusion-structure label="(2.5) Structure and function, including typical species"/>
      <conclusion-future label="Future prospects"/>
      <conclusion-assessment label="Overall assessment"/>
    </conclusion>
    <conclusion-n2000 label="Conclusions within Natura 2000 sites (optional)">
      <conclusion-range label="Range"/>
      <conclusion-area label="Area"/>
      <conclusion-structure label="Structure and function, including typical species"/>
      <conclusion-future label="Future prospects"/>
      <conclusion-assessment label="Overall assessment"/>
    </conclusion-n2000>
  </regional>
""" % (bioregions[r], r))
filecontent.append("</habitat>")
context.manage_addDocument(
    filename, title, ''.join(filecontent), 'text/xml', '')
#container.EnvelopeCreateEmptyGMLFile('map-range-%s.gml' % habitattype,'Range map',context)
#container.EnvelopeCreateEmptyGMLFile('map-favourable-range-%s.gml' % habitattype,'Favourable range map',context)
#container.EnvelopeCreateEmptyGMLFile('map-distribution-%s.gml' % habitattype,'Distribution map',context)
#container.EnvelopeCreateEmptyGMLFile('map-favourable-distribution-%s.gml' % habitattype,'Favourable map',context)
return context.index_html()
