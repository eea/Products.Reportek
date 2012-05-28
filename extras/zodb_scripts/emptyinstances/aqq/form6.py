return '''<?xml version="1.0" encoding="UTF-8"?>
<form6 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form6.xsd"
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
