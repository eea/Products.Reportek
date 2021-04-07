# Script (Python) "form2"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages, country
# title=
##
file_ob = getattr(context.zones, 'zones-%s.xml' % country.upper(), '')  # noqa: F821
if file_ob:
    return str(file_ob.data) % languages  # noqa: F999
else:
    return '''<?xml version="1.0" encoding="UTF-8"?>  # noqa: F999
<form2 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form2.xsd"  # noqa: E501
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"  xml:lang="%s">
    <form2-row>
        <full-zone-name></full-zone-name>
        <zone-code></zone-code>
        <pollutants>
            <groups>
                <a>false</a>
                <m>false</m>
                <s>false</s>
                <n>false</n>
            </groups>
            <types>
                <sh>false</sh>
                <se>false</se>
                <nh>false</nh>
                <nv>false</nv>
                <p>false</p>
                <l>false</l>
                <c>false</c>
                <b>false</b>
                <o>false</o>
                <as>false</as>
                <cd>false</cd>
                <ni>false</ni>
                <bap>false</bap>
            </types>
        </pollutants>
        <type>ag</type>
        <area></area>
        <population></population>
        <art22-application></art22-application>
        <source-type></source-type>
        <source-file></source-file>
        <source-codes></source-codes>
    </form2-row>
    <form-comments></form-comments>
</form2>''' % languages
