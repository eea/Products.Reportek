# Script (Python) "form3"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>  # noqa: F999
<form3 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form3.xsd"  # noqa: E501
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xi="http://www.w3.org/2001/XInclude"
    xml:lang="%s">
    <form3-row>
        <eoi-station-code/>
        <local-station-code/>
        <zone-code></zone-code>
        <use-directive>
            <so2>false</so2>
            <no2>false</no2>
            <nox>false</nox>
            <lead>false</lead>
            <benzene>false</benzene>
            <co>false</co>
        </use-directive>
        <directive-measuring-meth>
            <pm10></pm10>
            <pm25></pm25>
        </directive-measuring-meth>
        <correction-factor>
            <pm10></pm10>
            <pm25></pm25>
        </correction-factor>
        <directive-measuring-others>
            <arsenic>
                <sampling/>
                <analysis/>
            </arsenic>
            <cadmium>
                <sampling/>
                <analysis/>
            </cadmium>
            <nickel>
                <sampling/>
                <analysis/>
            </nickel>
            <bap>
                <sampling/>
                <analysis/>
            </bap>
        </directive-measuring-others>
        <station-function/>
    </form3-row>
    <form-comments/>
</form3>''' % languages
