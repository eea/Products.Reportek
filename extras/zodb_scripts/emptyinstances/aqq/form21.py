# Script (Python) "form21"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>
<form21 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form21.xsd"
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="%s">
	<form21a>
		<form21a-row>
			<zone-code></zone-code>
			<eoi-station-code></eoi-station-code>
			<exceedences-number></exceedences-number>
			<natural-source-code></natural-source-code>
			<estimated-exceedences></estimated-exceedences>
			<reference-to-justification></reference-to-justification>
		</form21a-row>
	</form21a>
	<form21b>
		<form21b-row>
			<zone-code></zone-code>
			<eoi-station-code></eoi-station-code>
			<exceedences-number></exceedences-number>
			<natural-source-code></natural-source-code>
			<estimated-exceedences></estimated-exceedences>
			<reference-to-justification></reference-to-justification>
		</form21b-row>
	</form21b>
	<form21c>
		<form21c-row>
			<zone-code></zone-code>
			<eoi-station-code></eoi-station-code>
			<mean-concentration-y></mean-concentration-y>
			<natural-source-code></natural-source-code>
			<estimated-mean-concentration></estimated-mean-concentration>
			<reference-to-justification></reference-to-justification>
		</form21c-row>
	</form21c>
	<form21d>
		<form21d-row>
			<zone-code></zone-code>
			<eoi-station-code></eoi-station-code>
			<mean-concentration-w></mean-concentration-w>
			<natural-source-code></natural-source-code>
			<estimated-mean-concentration></estimated-mean-concentration>
			<reference-to-justification></reference-to-justification>
		</form21d-row>
	</form21d>
	<form-comments/>
</form21>''' % languages
