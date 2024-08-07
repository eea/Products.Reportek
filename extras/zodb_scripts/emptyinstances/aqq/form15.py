# flake8: noqa
# Script (Python) "form15"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>  # noqa: F999
<form15 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form15.xsd"  # noqa: E501
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xml:lang="%s">
    <form15a>
        <form15a-row>
            <zone-code/>
            <eoi-station-code/>
            <aot40-veg-protection>
                <value/>
                <valid-data-number/>
            </aot40-veg-protection>
            <aot40-forest-protection>
                <value/>
                <valid-data-number/>
            </aot40-forest-protection>
            <annual-average/>
        </form15a-row>
    </form15a>
    <form15b>
        <form15b-row>
            <zone-code/>
            <eoi-station-code/>
            <arsenic>
                <concentration/>
            </arsenic>
            <cadmium>
                <concentration/>
            </cadmium>
            <nickel>
                <concentration/>
            </nickel>
            <benzo-a-pyrene>
                <concentration/>
            </benzo-a-pyrene>
        </form15b-row>
    </form15b>
    <form-comments/>
</form15>''' % languages
