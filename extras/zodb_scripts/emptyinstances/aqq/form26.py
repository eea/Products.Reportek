# Script (Python) "form26"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>
<form26
	xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form26.xsd"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="%s">
	<form26-row>
		<pollutant></pollutant>
		<limit-value-exceeded></limit-value-exceeded>
		<monitoring-method-used></monitoring-method-used>
		<eoi-station-code></eoi-station-code>
		<measured-value></measured-value>
		<reason-code></reason-code>
		<measures-taken></measures-taken>
	</form26-row>
	<form-comments/>
</form26>''' % languages
