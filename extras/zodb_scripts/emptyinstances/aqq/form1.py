# Script (Python) "form1"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return """<?xml version="1.0" encoding="UTF-8"?>  # noqa: F999
<form1 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form1.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="%s">  # noqa: E501
    <contact-address/>
    <contact-information>
        <contact-body-name/>
        <postal-address/>
        <contact-person-name/>
        <contact-person-telephone/>
        <contact-person-fax/>
        <contact-person-email/>
        <comments/>
    </contact-information>
    <revision-info>
        <revision-row>
            <revision-date></revision-date>
            <updated-forms/>
            <reason/>
        </revision-row>
    </revision-info>
    <zone-boundaries>
        <zone-covers-national-territory>false</zone-covers-national-territory>
        <are-zones-unchanged>false</are-zones-unchanged>
        <clarification-comment/>
    </zone-boundaries>
</form1>""" % languages
