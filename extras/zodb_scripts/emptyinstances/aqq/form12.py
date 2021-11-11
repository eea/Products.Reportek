# flake8: noqa
# Script (Python) "form12"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>  # noqa: F999
<form12 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form12.xsd"  # noqa: E501
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="%s">
    <form12-row>
        <reason-code>S1</reason-code>
        <description>Heavily trafficked urban centre</description>
    </form12-row>
    <form12-row>
        <reason-code>S2</reason-code>
        <description>Proximity to a major road</description>
    </form12-row>
    <form12-row>
        <reason-code>S3</reason-code>
        <description>Local industry including power production</description>
    </form12-row>
    <form12-row>
        <reason-code>S4</reason-code>
        <description>Quarrying or mining activities</description>
    </form12-row>
    <form12-row>
        <reason-code>S5</reason-code>
        <description>Domestic heating</description>
    </form12-row>
    <form12-row>
        <reason-code>S5</reason-code>
        <description>Accidental emission from industrial source</description>
    </form12-row>
    <form12-row>
        <reason-code>S6</reason-code>
        <description>Accidental emission from non-industrial source</description>
    </form12-row>
    <form12-row>
        <reason-code>S7</reason-code>
        <description>Natural source(s) or natural event(s</description>
    </form12-row>
    <form12-row>
        <reason-code>S8</reason-code>
        <description>Winter sanding of roads</description>
    </form12-row>
    <form12-row>
        <reason-code>S9</reason-code>
        <description>Transport of air pollution originating from sources outside the Member State</description>
    </form12-row>
    <form12-row>
        <reason-code>S10</reason-code>
        <description>Local petrol station</description>
    </form12-row>
    <form12-row>
        <reason-code>S11</reason-code>
        <description>Parking facility</description>
    </form12-row>
    <form12-row>
        <reason-code>S12</reason-code>
        <description>Benzene storage</description>
    </form12-row>
    <form-comments/>
</form12>''' % languages
