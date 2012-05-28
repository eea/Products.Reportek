## Script (Python) "form22"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=languages
##title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>
<form22
	xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form22.xsd"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="%s">
	<form22-row>
		<natural-source-code></natural-source-code>
		<description></description>
	</form22-row>
	<form-comments/>
</form22>''' % languages
