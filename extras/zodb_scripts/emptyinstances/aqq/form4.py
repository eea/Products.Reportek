# Script (Python) "form4"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>  # noqa: F999
<form4 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form4.xsd"  # noqa: E501
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xml:lang="%s">
    <form4-row>
        <eoi-station-code/>
        <local-station-code/>
        <zone-code/>
        <station-type/>
        <directive-relation>
            <o3>false</o3>
            <no2>false</no2>
            <nox>false</nox>
        </directive-relation>
    </form4-row>
    <form-comments/>
</form4>''' % languages
