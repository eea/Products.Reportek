# flake8: noqa
# Script (Python) "form27"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>  # noqa: F999
<form27 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form27.xsd"  # noqa: E501
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="%s">
    <form27-row>
        <reason-code/>
        <description/>
    </form27-row>
    <form-comments/>
</form27>''' % languages
