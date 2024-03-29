# flake8: noqa
# Script (Python) "form8"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>  # noqa: F999
<form8 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form8.xsd"  # noqa: E501
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xml:lang="%s">
    <form8a>
        <form8a-row>
            <zone-code/>
            <lv-health-1>
                <lv-mot/>
                <lv-mot-lv/>
                <lv/>
            </lv-health-1>
            <lv-health-24>
                <gt-lv/>
                <lt-lv/>
            </lv-health-24>
            <lv-health-y>
                <gt-lv/>
                <lt-lv/>
            </lv-health-y>
            <lv-health-w>
                <gt-lv/>
                <lt-lv/>
            </lv-health-w>
        </form8a-row>
    </form8a>
    <form8b>
        <form8b-row>
            <zone-code/>
            <lv-health-1>
                <lv-mot/>
                <lv-mot-lv/>
                <lv/>
            </lv-health-1>
            <lv-health-y>
                <lv-mot/>
                <lv-mot-lv/>
                <lv/>
            </lv-health-y>
            <lv-health-veg>
                <gt-lv/>
                <lt-lv/>
            </lv-health-veg>
        </form8b-row>
    </form8b>
    <form8c>
        <form8c-row>
            <zone-code/>
            <lv-24-stage1>
                <lv-mot/>
                <lv-mot-lv/>
                <lv/>
            </lv-24-stage1>
            <lv-y-stage1>
                <lv-mot/>
                <lv-mot-lv/>
                <lv/>
            </lv-y-stage1>
            <lv-24-stage2>
                <gt-lv/>
                <lt-lv/>
            </lv-24-stage2>
            <lv-y-stage2>
                <lv-mot/>
                <lv-mot-lv/>
                <lv/>
            </lv-y-stage2>
        </form8c-row>
    </form8c>
    <form8d>
        <form8d-row>
            <zone-code/>
            <lv>
                <lv-mot/>
                <lv-mot-lv/>
                <lv/>
                <ss>false</ss>
            </lv>
        </form8d-row>
    </form8d>
    <form8e>
        <form8e-row>
            <zone-code/>
            <lv>
                <lv-mot/>
                <lv-mot-lv/>
                <lv/>
                <art-3-2>false</art-3-2>
            </lv>
        </form8e-row>
    </form8e>
    <form8f>
        <form8f-row>
            <zone-code/>
            <lv>
                <lv-mot/>
                <lv-mot-lv/>
                <lv/>
            </lv>
        </form8f-row>
    </form8f>
    <form-comments/>
</form8>''' % languages
