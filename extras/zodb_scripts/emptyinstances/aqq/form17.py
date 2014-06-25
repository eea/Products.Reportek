## Script (Python) "form17"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=languages
##title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>
<form17 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form17.xsd"
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="%s">
	<form17-row>
		<eoi-station-code></eoi-station-code>
		<average-10minute></average-10minute>
		<calendar-day-number></calendar-day-number>
		<previous-column-days></previous-column-days>
		<maximum-concentration></maximum-concentration>
		<date>
			<month></month>
			<month-day></month-day>
		</date>
	</form17-row>
	<form-comments/>
</form17>''' % languages
