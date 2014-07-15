## Script (Python) "form24"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=languages
##title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>
<form24 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form24.xsd"
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="%s">
	<form24a>
		<form24a-row>
			<zone-code></zone-code>
			<eoi-station-code></eoi-station-code>
			<exceedences-number></exceedences-number>
			<estimated-exceedences></estimated-exceedences>
			<reference-to-justification></reference-to-justification>
		</form24a-row>
	</form24a>
	<form24b>
		<form24b-row>
			<zone-code></zone-code>
			<eoi-station-code></eoi-station-code>
			<mean-concentration-y></mean-concentration-y>
			<estimated-mean-concentration></estimated-mean-concentration>
			<reference-to-justification></reference-to-justification>
		</form24b-row>
	</form24b>
	<form-comments/>
</form24>''' % languages
