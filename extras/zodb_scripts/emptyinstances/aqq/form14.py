# Script (Python) "form14"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>
<form14 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form14.xsd"
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="%s">
<form14a>
		<form14a-row>
			<zone-code></zone-code>
			<eoi-station-code></eoi-station-code>
			<exceedence-number></exceedence-number>
			<calendar-years></calendar-years>
		</form14a-row>
	</form14a>
	<form14b>
		<form14b-row>
			<zone-code></zone-code>
			<eoi-station-code></eoi-station-code>
			<aot40-average></aot40-average>
			<calendar-years></calendar-years>
		</form14b-row>
	</form14b>
	<form14c>
		<form14c-row>
			<zone-code></zone-code>
			<eoi-station-code></eoi-station-code>
			<arsenic>
				<concentration></concentration>
				<area>
					<km2></km2>
					<method></method>
				</area>
				<population>
					<number></number>
					<method></method>
				</population>
				<reason-code></reason-code>
			</arsenic>
			<cadmium>
				<concentration></concentration>
				<area>
					<km2></km2>
					<method></method>
				</area>
				<population>
					<number></number>
					<method></method>
				</population>
				<reason-code></reason-code>
			</cadmium>
			<nickel>
				<concentration></concentration>
				<area>
					<km2></km2>
					<method></method>
				</area>
				<population>
					<number></number>
					<method></method>
				</population>
				<reason-code></reason-code>
			</nickel>
			<benzo-a-pyrene>
				<concentration></concentration>
				<area>
					<km2></km2>
					<method></method>
				</area>
				<population>
					<number></number>
					<method></method>
				</population>
				<reason-code></reason-code>
			</benzo-a-pyrene>
		</form14c-row>
	</form14c>
	<form14d>
		<form14d-row>
			<zone-code></zone-code>
			<eoi-station-code></eoi-station-code>
			<concentration></concentration>
			<reason-code></reason-code>
		</form14d-row>
	</form14d>
	<form-comments/>
</form14>''' % languages
