# Script (Python) "form16"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=languages
# title=
##
return '''<?xml version="1.0" encoding="UTF-8"?>
<form16 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form16.xsd"
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
		xml:lang="%s">
	<form16a>
		<form16a-row>
			<eoi-station-code/>
			<ethane />
			<ethylene />
			<acetylene />
			<propane />
			<propene />
			<n-butane />
			<i-butane />
			<butene-1 />
			<trans-2butene />
			<cis-2butene />
			<butadiene13 />
			<n-pentane />
			<i-pentane />
			<pentene-1 />
			<pentene-2 />
			<isoprene />
			<n-hexane />
			<i-hexane />
			<n-heptane />
			<n-octane />
			<i-octane />
			<benzene />
			<toluene />
			<ethyl-benzene />
			<mp-xylene />
			<o-xylene />
			<trimeth-benzene-124 />
			<trimeth-benzene-123 />
			<trimeth-benzene-135 />
			<formaldehyde />
			<total-non-methane-hydrocarbons />
		</form16a-row>
	</form16a>
	<form16b>
		<form16b-row>
			<eoi-station-code />
			<compound>
				<name />
				<quantity />
			</compound>
		</form16b-row>
	</form16b>
	<form16c>
		<form16c-row>
			<eoi-station-code />
			<compound>
				<name>benzo(a)anthracene</name>
				<quantity />
			</compound>
			<compound>
				<name>benzo(b)fluoranthene</name>
				<quantity />
			</compound>
			<compound>
				<name>benzo(j)fluoranthene</name>
				<quantity />
			</compound>
			<compound>
				<name>benzo(k)fluoranthene</name>
				<quantity />
			</compound>
			<compound>
				<name>indeno(1,2,3-cd)pyrene</name>
				<quantity />
			</compound>
			<compound>
				<name>dibenz(a,h)anthracene</name>
				<quantity />
			</compound>
			<compound>
				<name>total (gaseous) Mercury</name>
				<quantity />
			</compound>
			<compound>
				<name>particulate divalent mercury</name>
				<quantity />
			</compound>
			<compound>
				<name>gaseous divalent mercury</name>
				<quantity />
			</compound>
		</form16c-row>
	</form16c>
	<form16d>
		<form16d-row>
			<eoi-station-code />
			<compound>
				<name>benzo(a)pyrene</name>
				<quantity />
			</compound>
			<compound>
				<name>benzo(a)anthracene</name>
				<quantity />
			</compound>
			<compound>
				<name>benzo(b)fluoranthene</name>
				<quantity />
			</compound>
			<compound>
				<name>benzo(j)fluoranthene</name>
				<quantity />
			</compound>
			<compound>
				<name>benzo(k)fluoranthene</name>
				<quantity />
			</compound>
			<compound>
				<name>indeno(1,2,3-cd)pyrene</name>
				<quantity />
			</compound>
			<compound>
				<name>dibenz(a,h)anthracene</name>
				<quantity />
			</compound>
			<compound>
				<name>arsenic</name>
				<quantity />
			</compound>
			<compound>
				<name>cadmium</name>
				<quantity />
			</compound>
			<compound>
				<name>nickel</name>
				<quantity />
			</compound>
			<compound>
				<name>mercury</name>
				<quantity />
			</compound>
		</form16d-row>
	</form16d>
	<form-comments/>
</form16>''' % languages
