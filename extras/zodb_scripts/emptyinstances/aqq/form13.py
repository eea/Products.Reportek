## Script (Python) "form13"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=languages
##title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>
<form13 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form13.xsd"
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
		xml:lang="%s">
	<form13a>
		<form13a-row>
			<zone-code/>
			<eoi-station-code/>
			<month></month>
			<day-of-month></day-of-month>
			<ozone-concentration/>
			<reason-code/>
			<starting-time></starting-time>
			<exceedence-hours></exceedence-hours>
			<maximum-ozone></maximum-ozone>
		</form13a-row>
	</form13a>
	<form13b>
		<form13b-row>
			<zone-code/>
			<eoi-station-code/>
			<month></month>
			<day-of-month></day-of-month>
			<ozone-concentration/>
			<reason-code/>
			<starting-time></starting-time>
			<exceedence-hours></exceedence-hours>
			<maximum-ozone></maximum-ozone>
		</form13b-row>
	</form13b>
	<form13c>
		<form13c-row>
			<zone-code/>
			<eoi-station-code/>
			<month></month>
			<day-of-month></day-of-month>
			<concentration></concentration>
			<reason-code/>
		</form13c-row>
	</form13c>
	<form-comments/>
</form13>''' % languages
