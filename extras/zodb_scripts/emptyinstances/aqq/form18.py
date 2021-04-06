# Script (Python) "form18"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>
<form18 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form18.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="%s">
	<form18-row>
		<eoi-station-code></eoi-station-code>
		<arithmetic-mean></arithmetic-mean>
		<median></median>
		<percentile-98></percentile-98>
		<maximum-concentration></maximum-concentration>
	</form18-row>
	<form-comments/>
</form18>''' % languages
