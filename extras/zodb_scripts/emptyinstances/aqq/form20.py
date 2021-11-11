# flake8: noqa
# Script (Python) "form20"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>  # noqa: F999
<form20
    xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form20.xsd"  # noqa: E501
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="%s">
    <form20-row>
        <method></method>
        <full-reference></full-reference>
    </form20-row>
    <form-comments/>
</form20>''' % languages
