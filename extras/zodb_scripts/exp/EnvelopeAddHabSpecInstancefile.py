## Script (Python) "EnvelopeAddHabSpecInstancefile"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Add an empty instance
##
# Notice: Maintain the instancefile under /xmlexports, then cut-and-paste it to here
# when changed

context.manage_addDocument('habitat001.xml',"Habitat questionnaire",
   """<?xml version="1.0" encoding="UTF-8"?>
<habitat xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://cdrtest.eionet.eu.int/xmlexports/dir9243eec/schema.xsd">
	<national>
		<code label="Habitat Code"/>
		<country label="Member State"/>
		<region label="Biogeographic region concerned within the MS"/>
		<range label="Range"/>
		<map label="Map"/>
	</national>
	<regional>
		<region label="Biogeographic region"/>
		<source label="Published sources"/>
		<range label="Range">
			<surface-area label="Surface area"/>
			<date label="Date"/>
			<quality label="Quality of data"/>
			<trend label="Trend"/>
			<trend-period label="Trend-Period"/>
			<reasons label="Reasons for reported trend"/>
		</range>
		<coverage label="Area covered by habitat">
			<map label="Distribution map"/>
			<surface-area label="Surface area"/>
			<date label="Date"/>
			<method label="Method used"/>
			<quality label="Quality of data"/>
			<trend label="Trend"/>
			<trend-period label="Trend-Period"/>
			<reasons label="Reasons for reported trend"/>
			<justification label="Justification of % thresholds for trends"/>
			<pressures label="Main pressures"/>
			<threats label="Threats"/>
		</coverage>
		<complementary>
			<favourable-range>
				<surface-area label="Surface area"/>
				<map label="Map"/>
				<typical-species label="Typical species"/>
				<other-information label="Other relevant information"/>
			</favourable-range>
		</complementary>
		<conclusion>
			<conclusion-range label="Range"/>
			<conclusion-area label="Area"/>
			<conclusion-specific label="Specific structures and functions (incl. typical species)"/>
			<conclusion-future label="Future prospects"/>
			<conclusion-assessment label="Overall assessment of CS"/>
		</conclusion>
	</regional>
</habitat>
""",'text/xml','')
    
context.completeWorkitem(workitem_id)
