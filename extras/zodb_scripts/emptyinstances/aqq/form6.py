# flake8: noqa
# Script (Python) "form6"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>  # noqa: F999
<form6 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form6.xsd"  # noqa: E501
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xml:lang="%s">
    <form6-row>
        <eoi-station-code />
        <local-station-code />
        <ozone-zone-code />
        <substances>
            <substance>
                <name/>
                <measurement-method />
            </substance>
        </substances>
    </form6-row>
    <form-comments/>
</form6>''' % languages
