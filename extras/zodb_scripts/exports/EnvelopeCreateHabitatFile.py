## Script (Python) "EnvelopeCreateHabitatFile"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=habitattype
##title=Creates a new instance file
##
# Notice: Maintain the instancefile under /xmlexports, then cut-and-paste it to here
# when changed
filename="habitattype-%s.xml" % habitattype
title="Habitat type questionnaire for habitat %s" % habitattype
context.manage_addDocument(filename, title,
   """<?xml version="1.0" encoding="UTF-8"?>
<habitat xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://cdrtest.eionet.eu.int/xmlexports/dir9243eec/schema.xsd">
	<national>
		<code label="Habitat Code">%s</code>
		<country label="Member State"/>
		<region label="Biogeographic region concerned within the MS"/>
		<surface-range label="Range of the habitat in km2"/>
		<map-range label="Range map">
                        <map/>
                </map-range>
                <map-favourable-range label="Favourable Range map">
                        <map/>
                </map-favourable-range>
                <distribution-area label="Habitat distribution in km2"/>
                <map-distribution label="Distribution map">
                        <map/>
                </map-distribution>
                <map-favourable label="Favourable distribution area map">
                        <map/>
                </map-favourable>
	</national>
	<regional>
		<region label="Biogeographic region"/>
		<source label="Published sources"/>
		<range label="Range">
			<surface-area label="Surface area in km2"/>
			<date label="Date"/>
			<quality label="Quality of data"/>
			<trend label="Trend"/>
                        <magnitude label="Range trend magnitude (km2)"/>
			<trend-period label="Trend-Period"/>
			<reasons label="Reasons for reported trend"/>
		</range>
		<coverage label="Area covered by habitat">
			<surface-area label="Habitat area in km2"/>
			<date label="Date of estimation"/>
			<method label="Method used"/>
			<quality label="Quality of data"/>
			<trend label="Habitate Trend"/>
                        <magnitude label="Range trend magnitude (km2)"/>
			<trend-period label="Trend-Period"/>
			<reasons label="Reasons for reported trend"/>
			<trend-comments label="Possible comments on thresholds for trends"/>
			<pressures label="Main pressures"/>
			<threats label="Threats"/>
		</coverage>
		<complementary>
			<surface-range label="Favourable range in km2"/>
			<surface-area label="Favourable reference area in km2"/>
                        <structure label="Structure and Function"/>
			<typical-species label="Typical species"/>
			<other-information label="Other relevant information"/>
		</complementary>
		<conclusion>
			<conclusion-range label="Range"/>
			<conclusion-area label="Area"/>
			<conclusion-structure label="Specific structures and functions (incl. typical species)"/>
			<conclusion-future label="Future prospects"/>
			<conclusion-assessment label="Overall assessment of CS"/>
		</conclusion>
	</regional>
</habitat>
""" % habitattype,'text/xml','')
return context.index_html()
