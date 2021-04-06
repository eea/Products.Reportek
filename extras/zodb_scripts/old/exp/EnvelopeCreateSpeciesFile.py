# Script (Python) "EnvelopeCreateSpeciesFile"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=language, author, specie, specie_from, region=[], species=None, confirm=False
# title=Art 17: Creates a new instance file
##
# Notice: Maintain the instancefile under /xmlexports, then cut-and-paste it to here
# when changed

request = context.REQUEST
response = request.RESPONSE
SESSION = request.SESSION
l_found = False

if confirm == 'True':

    if request.has_key('submit_yes'):
        l_found = True
        region = SESSION.get('region')
        language = SESSION.get('language')
        author = SESSION.get('author')
        specie = SESSION.get('specie')
        specie_from = SESSION.get('specie_from')
        species = SESSION.get('species')

        del(SESSION['region'])
        del(SESSION['language'])
        del(SESSION['author'])
        del(SESSION['specie'])
        del(SESSION['specie_from'])
        del(SESSION['species'])

        l_species = specie
    else:
        return context.index_html()

else:
    if specie_from == 'prechoise':
        l_found = True
        l_species = species
        author = ''
    else:
        l_species = specie.strip()
        for i in context.Art17species_queries(3):
            if i[1].lower() == l_species:
                l_found = True
                l_species = i[1]
                break

err_msg = []
if specie_from == 'free_input':
    # check species name
    l_list = specie.split(' ')
    if len(l_list) >= 2:
        for k in l_list:
            if not len(k) > 0:
                err_msg.append(
                    "The field 'Species scientific name' does not contain a valid name!")
                break
    else:
        err_msg.append(
            "The field 'Species scientific name' does not contain a valid name!")
    # chech author
    l_validyear = True
    if len(author) > 5:
        l_start = author.find('(')
        l_end = author.find(')')
        if l_start >= 0 and l_end >= 0:
            l_year = author[l_start+1:l_end]
            try:
                if int(l_year) > 2007 or int(l_year) < 1000:
                    l_validyear = False
            except:
                l_validyear = False
        else:
            l_validyear = False
    else:
        l_validyear = False
    if l_validyear == False:
        err_msg.append(
            "The field 'Author name (year)' does not contain a valid year!")

if len(region) < 1:
    err_msg.append('You have to select at least one region!')

if species == None and specie_from == 'prechoise':
    err_msg.append('You have to select a species!')

if len(err_msg) > 0:
    SESSION.set('err_msg', err_msg)
    SESSION.set('region', region)
    SESSION.set('language', language)
    SESSION.set('author', author)
    SESSION.set('specie', specie)
    SESSION.set('specie_from', specie_from)
    SESSION.set('species', species)
    return response.redirect('EnvelopeCreateSpeciesFileForm')

if l_found == False:

    SESSION.set('region', region)
    SESSION.set('language', language)
    SESSION.set('author', author)
    SESSION.set('specie', specie)
    SESSION.set('specie_from', specie_from)
    SESSION.set('species', species)
    return response.redirect('EnvelopeCreateSpeciesFileConfirm')

if l_found:
    transmap = string.maketrans(' ', '-')
    spec_filename = l_species.translate(transmap).lower()
    filename = "species-%s.xml" % spec_filename
    title = "Species questionnaire for %s" % l_species
    filecontent = []

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

    def mapelem(elem):
        return """<map href="%s-spec-%s.gml" rel_uri="/%s"/>""" % (elem, spec_filename, context.absolute_url(1))

    filecontent.append("""<?xml version="1.0" encoding="UTF-8"?>
    <species xml:lang="%s" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/species.xsd" xmlns="">
      <speciesname label="Species Name">%s</speciesname>
      <speciesauthor label="Species author (year)">%s</speciesauthor>
      <regions label="Biogeographic regions and/or marine regions concerned in the MS">%s</regions>
      <national label="1. National level">
        <map-range label="1.1 Species range map">
          %s
        </map-range>
        <map-distribution label="1.2 Species distribution map">
          %s
        </map-distribution>
        <map-favourable-range label="1.3 Species favourable reference range map (optional)">
          %s
        </map-favourable-range>
      </national>
    """ % (language, l_species, author, ' '.join(region), mapelem('map-range'), mapelem('map-distribution'), mapelem('map-favourable-range')))

    for r in region:
        filecontent.append("""
      <regional label="2. Biogeographical or marine level">
        <region label="2.1 Biogeographical region or marine region" desc="%s">%s</region>
        <published label="2.2 Published sources and/or websites"/>
        <range label="2.3 Range of species in the biogeographic region or marine region">
          <surface-area label="2.3.1 Surface range of the species in km2"/>
          <date label="2.3.2 Date of range determination"/>
          <quality label="2.3.3 Quality of data concerning range"/>
          <trend label="2.3.4 Range trend"/>
          <trend-magnitude label="2.3.5 Range trend magnitude (km2) - optional"/>
          <trend-period label="2.3.6 Range trend period"/>
          <reasons label="2.3.7 Reasons for reported trend"/>
          <reasons-specify label="and/or specify"/>
        </range>
        <population label="2.4 Population of the species in the biogeographic region or marine region">
          <size label="2.4.1 Population size estimation">
            <minimum-size label="Minimum population"/>
            <maximum-size label="Maximum population"/>
            <size-unit label="Population units"/>
          </size>
          <date label="2.4.2 Date of population estimation"/>
          <method label="2.4.3 Method used for population estimation"/>
          <quality label="2.4.4 Quality of population data"/>
          <trend label="2.4.5 Population trend"/>
          <trend-magnitude label="2.4.6 Population trend magnitude"/>
          <trend-period label="2.4.7 Population trend period"/>
          <reasons label="2.4.8 Reasons for reported trend"/>
          <reasons-specify label="and/or specify"/>
          <justification label="2.4.9 Justification of %% thresholds for trends (optional)"/>
          <pressures label="2.4.10 Main pressures"/>
          <threats label="2.4.11 Threats"/>
        </population>
        <habitat label="2.5 Habitat for the species in the biogeographic region or marine region">
          <habitatcodes label="2.5.1 Habitats for the species"/>
          <surface-area label="2.5.2 Area estimation (km2)"/>
          <date label="2.5.3 Date of estimation"/>
          <quality label="2.5.4 Quality of the data"/>
          <trend label="2.5.5 Trend of the habitat"/>
          <trend-period label="2.5.6 Trend period"/>
          <reasons label="2.5.7 Reasons for reported trend"/>
          <reasons-specify label="and/or specify"/>
        </habitat>
        <future-prospects label="2.6 Future prospects for the species"/>
        <complementary label="2.7 Complementary information">
          <favourable-range label="2.7.1 Favourable reference range (km2)"/>
          <favourable-population label="2.7.2 Favourable reference population"/>
          <suitable-habitat label="2.7.3 Suitable habitat for the species"/>
          <other-information label="2.7.4 Other relevant information"/>
        </complementary>
        <conclusion label="Conclusions">
          <conclusion-range label="(2.3) Range"/>
          <conclusion-population label="(2.4) Population"/>
          <conclusion-habitat label="(2.5) Habitat for the species"/>
          <conclusion-future label="(2.6) Future prospects"/>
          <conclusion-assessment label="Overall assessment"/>
        </conclusion>
        <conclusion-n2000 label="Conclusions within Natura 2000 sites (optional)">
          <conclusion-range label="Range"/>
          <conclusion-population label="Population"/>
          <conclusion-habitat label="Habitat for the species"/>
          <conclusion-future label="Future prospects"/>
          <conclusion-assessment label="Overall assessment"/>
        </conclusion-n2000>
      </regional>
    """ % (bioregions[r], r))
    filecontent.append("</species>")
    context.manage_addDocument(
        filename, title, ''.join(filecontent), 'text/xml', '')
    #container.EnvelopeCreateEmptyGMLFile('map-range-spec-%s.gml' % spec_filename,'Range map',context)
    #container.EnvelopeCreateEmptyGMLFile('map-distribution-spec-%s.gml' % spec_filename,'Distribution map',context)
    #container.EnvelopeCreateEmptyGMLFile('map-favourable-range-spec-%s.gml' % spec_filename,'Favourable range map',context)
    return context.index_html()
