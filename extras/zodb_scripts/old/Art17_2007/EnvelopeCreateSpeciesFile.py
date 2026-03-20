# flake8: noqa
# Script (Python) "EnvelopeCreateSpeciesFile"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=language, author, specie, specie_from, region=[], species=None, confirm=False
# title=Art 17: Creates a new instance file
##
# Map accented characters to ascii
asciimap = {
    0x0020: 0x2D,
    0x008A: 0x53,
    0x008E: 0x5A,
    0x009A: 0x73,
    0x009E: 0x5A,
    0x009F: 0x59,
    0x00AA: 0x61,
    0x00B2: 0x32,
    0x00B3: 0x33,
    0x00B5: 0x75,
    0x00BF: 0x3F,
    0x00C0: 0x41,
    0x00C1: 0x41,
    0x00C2: 0x41,
    0x00C3: 0x41,
    0x00C4: 0x41,
    0x00C5: 0x41,
    0x00C6: 0x41,
    0x00C7: 0x43,
    0x00C8: 0x45,
    0x00C9: 0x45,
    0x00CA: 0x45,
    0x00CB: 0x45,
    0x00CC: 0x49,
    0x00CD: 0x49,
    0x00CE: 0x49,
    0x00CF: 0x49,
    0x00D0: 0x44,
    0x00D1: 0x4E,
    0x00D2: 0x4F,
    0x00D3: 0x4F,
    0x00D4: 0x4F,
    0x00D5: 0x4F,
    0x00D6: 0x4F,
    0x00D7: 0x78,
    0x00D8: 0x4F,
    0x00D9: 0x55,
    0x00DA: 0x55,
    0x00DB: 0x55,
    0x00DC: 0x55,
    0x00DD: 0x59,
    0x00DF: 0x42,
    0x00E0: 0x61,
    0x00E1: 0x61,
    0x00E2: 0x61,
    0x00E3: 0x61,
    0x00E4: 0x61,
    0x00E5: 0x61,
    0x00E6: 0x61,
    0x00E7: 0x43,
    0x00E8: 0x65,
    0x00E9: 0x65,
    0x00EA: 0x65,
    0x00EB: 0x65,
    0x00EC: 0x69,
    0x00ED: 0x69,
    0x00EE: 0x69,
    0x00EF: 0x69,
    0x00F1: 0x6E,
    0x00F2: 0x6F,
    0x00F3: 0x6F,
    0x00F4: 0x6F,
    0x00F5: 0x6F,
    0x00F6: 0x6F,
    0x00F7: 0x2D,
    0x00F8: 0x6F,
    0x00F9: 0x75,
    0x00FA: 0x75,
    0x00FB: 0x75,
    0x00FC: 0x75,
    0x00FD: 0x79,
    0x00FE: 0x62,
    0x00FF: 0x79,
    0x0100: 0x41,
    0x0101: 0x61,
    0x0102: 0x41,
    0x0103: 0x61,
    0x0104: 0x41,
    0x0105: 0x61,
    0x0106: 0x43,
    0x0107: 0x63,
    0x0108: 0x43,
    0x0109: 0x63,
    0x010A: 0x43,
    0x010B: 0x63,
    0x010C: 0x43,
    0x010D: 0x63,
    0x010E: 0x44,
    0x010F: 0x64,
    0x0110: 0x44,
    0x0111: 0x64,
    0x0112: 0x45,
    0x0113: 0x65,
    0x0114: 0x45,
    0x0115: 0x65,
    0x0116: 0x45,
    0x0117: 0x65,
    0x0118: 0x45,
    0x0119: 0x65,
    0x011A: 0x45,
    0x011B: 0x65,
    0x011C: 0x47,
    0x011D: 0x67,
    0x011E: 0x47,
    0x011F: 0x67,
    0x0120: 0x47,
    0x0121: 0x67,
    0x0122: 0x47,
    0x0123: 0x67,
    0x0124: 0x48,
    0x0125: 0x68,
    0x0126: 0x48,
    0x0127: 0x68,
    0x0128: 0x49,
    0x0129: 0x69,
    0x012A: 0x49,
    0x012B: 0x69,
    0x012C: 0x49,
    0x012D: 0x69,
    0x012E: 0x49,
    0x012F: 0x69,
    0x0130: 0x49,
    0x0132: 0x49,
    0x0133: 0x69,
    0x0134: 0x6A,
    0x0135: 0x4A,
    0x0136: 0x4B,
    0x0137: 0x6B,
    0x0138: 0x4B,
    0x0139: 0x4C,
    0x013A: 0x6C,
    0x013B: 0x4C,
    0x013C: 0x6C,
    0x013D: 0x4C,
    0x013E: 0x6C,
    0x013F: 0x4C,
    0x0140: 0x6C,
    0x0141: 0x4C,
    0x0142: 0x6C,
    0x0143: 0x4E,
    0x0144: 0x6E,
    0x0145: 0x4E,
    0x0146: 0x6E,
    0x0147: 0x4E,
    0x0148: 0x6E,
    0x0149: 0x6E,
    0x014A: 0x4E,
    0x014B: 0x6E,
    0x014C: 0x4F,
    0x014D: 0x6F,
    0x014E: 0x4F,
    0x014F: 0x6F,
    0x0150: 0x4F,
    0x0151: 0x6F,
    0x0152: 0x43,
    0x0153: 0x63,
    0x0154: 0x52,
    0x0155: 0x72,
    0x0156: 0x52,
    0x0157: 0x72,
    0x0158: 0x52,
    0x0159: 0x72,
    0x015A: 0x53,
    0x015B: 0x73,
    0x015C: 0x53,
    0x015D: 0x73,
    0x015E: 0x53,
    0x015F: 0x73,
    0x0160: 0x53,
    0x0161: 0x73,
    0x0162: 0x54,
    0x0163: 0x74,
    0x0164: 0x54,
    0x0165: 0x74,
    0x0166: 0x54,
    0x0167: 0x74,
    0x0168: 0x55,
    0x0169: 0x75,
    0x016A: 0x55,
    0x016B: 0x75,
    0x016C: 0x55,
    0x016D: 0x75,
    0x016E: 0x55,
    0x016F: 0x75,
    0x0170: 0x55,
    0x0171: 0x75,
    0x0172: 0x55,
    0x0173: 0x75,
    0x0174: 0x57,
    0x0175: 0x77,
    0x0176: 0x59,
    0x0177: 0x79,
    0x0178: 0x59,
    0x0179: 0x5A,
    0x017A: 0x7A,
    0x017B: 0x5A,
    0x017C: 0x7A,
    0x017D: 0x5A,
    0x017E: 0x7A,
    0x017F: 0x66,
    0x0192: 0x66,
}

request = context.REQUEST
response = request.RESPONSE
SESSION = request.SESSION
l_found = False

if confirm == "True":
    if "submit_yes" in request:
        l_found = True
        region = SESSION.get("region")
        language = SESSION.get("language")
        author = SESSION.get("author")
        specie = SESSION.get("specie")
        specie_from = SESSION.get("specie_from")
        species = SESSION.get("species")

        del SESSION["region"]
        del SESSION["language"]
        del SESSION["author"]
        del SESSION["specie"]
        del SESSION["specie_from"]
        del SESSION["species"]

        l_species = specie
    else:
        return context.index_html()

else:
    if specie_from == "prechoise":
        l_found = True
        l_species = species
        author = ""
    else:
        l_species = specie.strip()
        for i in context.Art17species_queries(3):
            if i[1].lower() == l_species:
                l_found = True
                l_species = i[1]
                break

err_msg = []
if specie_from == "free_input":
    # check species name
    l_list = specie.split(" ")
    if len(l_list) >= 2:
        for k in l_list:
            if not len(k) > 0:
                err_msg.append(
                    "The field 'Species scientific name' does not contain a valid name!"
                )
                break
    else:
        err_msg.append(
            "The field 'Species scientific name' does not contain a valid name!"
        )

if len(region) < 1:
    err_msg.append("You have to select at least one region!")

if species == None and specie_from == "prechoise":
    err_msg.append("You have to select a species!")

if len(err_msg) > 0:
    SESSION.set("err_msg", err_msg)
    SESSION.set("region", region)
    SESSION.set("language", language)
    SESSION.set("author", author)
    SESSION.set("specie", specie)
    SESSION.set("specie_from", specie_from)
    SESSION.set("species", species)
    return response.redirect("EnvelopeCreateSpeciesFileForm")

if l_found == False:
    SESSION.set("region", region)
    SESSION.set("language", language)
    SESSION.set("author", author)
    SESSION.set("specie", specie)
    SESSION.set("specie_from", specie_from)
    SESSION.set("species", species)
    return response.redirect("EnvelopeCreateSpeciesFileConfirm")

if l_found:
    #    transmap = string.maketrans(' ','-')
    spec_filename = str(l_species, "utf-8").translate(asciimap).lower()
    filename = "species-%s.xml" % spec_filename.encode("utf-8")
    title = "Species questionnaire for %s" % l_species
    filecontent = []

    bioregions = {
        "ALP": "Alpine",
        "ATL": "Atlantic",
        "BOR": "Boreal",
        "CON": "Continental",
        "MED": "Mediterranean",
        "MAC": "Macaronesian",
        "PAN": "Pannonian",
        "MATL": "Atlantic ocean",
        "MBAL": "Baltic sea",
        "MMED": "Mediterranean sea",
        "MMAC": "Macaronesian/Atlantic ocean",
    }

    l_countryname = "Unspecified"
    l_countrycode = ""
    for country_obj in container.localities_table():
        if country_obj["uri"] == context.country:
            l_countryname = country_obj["name"]
            l_countrycode = country_obj["iso"]
            break

    filecontent.append(
        """<?xml version="1.0" encoding="UTF-8"?>
    <species xml:lang="%s" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/species.xsd" xmlns="">
      <member-state label="Member state" countrycode="%s">%s</member-state>
      <speciesname label="Species Name">%s</speciesname>
      <speciesauthor label="Species author (year)">%s</speciesauthor>
      <regions label="Biogeographic regions and/or marine regions concerned in the MS">%s</regions>
    """
        % (language, l_countrycode, l_countryname, l_species, author, " ".join(region))
    )

    for r in region:
        filecontent.append(
            """
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
          <reasons-specify label="Other (specify)"/>
        </range>
        <population label="2.4 Population of the species in the biogeographic region or marine region">
          <size label="2.4.1 Population size estimation">
            <minimum-size label="Minimum population"/>
            <maximum-size label="Maximum population"/>
            <size-unit label="Population units"/>
          </size>
          <date label="2.4.2 Date of population estimation"/>
          <method label="2.4.3 Methods used for population estimation"/>
          <quality label="2.4.4 Quality of population data"/>
          <trend label="2.4.5 Population trend"/>
          <trend-magnitude label="2.4.6 Population trend magnitude"/>
          <trend-period label="2.4.7 Population trend period"/>
          <reasons label="2.4.8 Reasons for reported trend"/>
          <reasons-specify label="Other (specify)"/>
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
          <reasons-specify label="Other (specify)"/>
        </habitat>
        <future-prospects label="2.6 Future prospects for the species"/>
        <complementary label="2.7 Complementary information">
          <favourable-range label="2.7.1 Favourable reference range (km2)" qualifier=""/>
          <favourable-population label="2.7.2 Favourable reference population" qualifier=""/>
          <suitable-habitat label="2.7.3 Suitable habitat for the species (km2)"/>
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
    """
            % (bioregions[r], r)
        )
    filecontent.append("</species>")
    context.manage_addDocument(filename, title, "".join(filecontent), "text/xml", "")
    return context.index_html()
