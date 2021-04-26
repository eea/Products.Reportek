# flake8: noqa
# Script (Python) "form23"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>  # noqa: F999
<form23 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form23.xsd"  # noqa: E501
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="%s">
    <form23a>
        <form23a-row>
            <zone-code></zone-code>
            <eoi-station-code></eoi-station-code>
            <exceedences-number></exceedences-number>
            <natural-event-code></natural-event-code>
            <estimated-exceedences></estimated-exceedences>
            <reference-to-justification></reference-to-justification>
        </form23a-row>
    </form23a>
    <form23b>
        <form23b-row>
            <zone-code></zone-code>
            <eoi-station-code></eoi-station-code>
            <mean-concentration-y></mean-concentration-y>
            <natural-event-code></natural-event-code>
            <estimated-mean-concentration></estimated-mean-concentration>
            <reference-to-justification></reference-to-justification>
        </form23b-row>
    </form23b>
    <form-comments/>
</form23>''' % languages
