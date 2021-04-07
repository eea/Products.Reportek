# Script (Python) "form9"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>  # noqa: F999
<form9 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form9.xsd"  # noqa: E501
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xml:lang="%s">
    <form9a>
        <form9a-row>
            <zone-code/>
            <thresholds-health>
                <tv/>
                <tv-lto/>
                <lto/>
            </thresholds-health>
            <thresholds-vegetation>
                <tv/>
                <tv-lto/>
                <lto/>
            </thresholds-vegetation>
        </form9a-row>
    </form9a>
    <form9b>
        <form9b-row>
            <zone-code/>
            <arsenic>
                <gt-tv/>
                <lt-tv/>
            </arsenic>
            <cadmium>
                <gt-tv/>
                <lt-tv/>
            </cadmium>
            <nickel>
                <gt-tv/>
                <lt-tv/>
            </nickel>
            <benzo-a-pyrene>
                <gt-tv/>
                <lt-tv/>
            </benzo-a-pyrene>
        </form9b-row>
    </form9b>
    <form9c>
        <form9c-row>
            <zone-code/>
            <target-value>
                <gt-tv/>
                <lt-tv/>
            </target-value>
        </form9c-row>
    </form9c>
    <form-comments/>
</form9>''' % languages
