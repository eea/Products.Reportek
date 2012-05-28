return '''<?xml version="1.0" encoding="UTF-8"?>
<form7 xsi:noNamespaceSchemaLocation="http://air-climate.eionet.europa.eu/schemas/AirQualityQuestionnaire/AirQualityQuestionnaire-form7.xsd"
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
		xml:lang="%s">
	<form7-row>
		<method-code>M1</method-code>
		<description>PM10 or PM2.5: Beta-absorption</description>
	</form7-row>

	<form7-row>
		<method-code>M2</method-code>
		<description>PM10 or PM2.5: Gravimetry for PM10 and/or PM2,5 – continuous measurement</description>
	</form7-row>

	<form7-row>
		<method-code>M2dxxx</method-code>
		<description>PM10 or PM2.5: Gravimetry for PM10 and/or PM2,5 – random measurement; xxx should be the number of measured days. Example: random sampling on 180 days of the year is indicated by M2d180.</description>
	</form7-row>

	<form7-row>
		<method-code>M3</method-code>
		<description>PM10 or PM2.5: Oscillating microbalance for PM10 and/or PM2,5</description>
	</form7-row>

	<form7-row>
		<method-code>M3a</method-code>
		<description>PM10 or PM2.5: Oscillating microbalance for PM10 and/or PM2,5 with FDMS</description>
	</form7-row>

	<form7-row>
		<method-code>M4</method-code>
		<description>Lumped sum NMHC: automated, semi-continuous monitoring, NMHC calculated from Total HC minus methane;FID</description>
	</form7-row>

	<form7-row>
		<method-code>M5</method-code>
		<description>Lumped sum NMHC: automated semi-continuous monitoring, after chromatographic separation of NMHC from methane; FID</description>
	</form7-row>

	<form7-row>
		<method-code>M6</method-code>
		<description>Individual VOC: automated sampling and on line analysis; cryogenic sample pre-concentration, GC/FID (MS) detection</description>
	</form7-row>

	<form7-row>
		<method-code>M7</method-code>
		<description>Individual VOC: whole air canister sampling; off line analysis by GC/FID (MS)</description>
	</form7-row>

	<form7-row>
		<method-code>M8</method-code>
		<description>Individual VOC: active solid adsorbent sampling; off line analysis by GC/FID (MS) after solvent or thermal desorption</description>
	</form7-row>

	<form7-row>
		<method-code>M9</method-code>
		<description>Individual VOC: diffusive solid adsorbent sampling; off line analysis by GC/FID(MS) after solvent or thermal desorption</description>
	</form7-row>

	<form7-row>
		<method-code>M10subcode 1)</method-code>
		<description>Formaldehyde: sampling with DNPH; off line analysis of hydrazones by HPLC with UV detection (360 nm).</description>
	</form7-row>

	<form7-row>
		<method-code>M11subcode 1)</method-code>
		<description>Formaldehyde: sampling with HMP; off line analysis of oxazolidine by GC-NPD</description>
	</form7-row>

	<form7-row>
		<method-code>M12subcode 1)</method-code>
		<description>Formaldehyde: sampling withy bisulfite and chromotropic acid; off line analysis by spectrometry (580 nm)</description>
	</form7-row>

	<form7-row>
		<method-code>M13</method-code>
		<description>sampling method: HVS - manual filter change 30 m3/h</description>
	</form7-row>

	<form7-row>
		<method-code>M14</method-code>
		<description>sampling method: HVS -automatic filter change 30 m3/h</description>
	</form7-row>

	<form7-row>
		<method-code>M15</method-code>
		<description>sampling method: MVS - manual filter change 15 m3/h</description>
	</form7-row>

	<form7-row>
		<method-code>M16</method-code>
		<description>sampling method: LVS- manual filter change 2,3 m3/h</description>
	</form7-row>

	<form7-row>
		<method-code>M17</method-code>
		<description>sampling method: LVS - automatic filter change 2,3 m3/h</description>
	</form7-row>

	<form7-row>
		<method-code>M18</method-code>
		<description>GF-AAS - Graphite furnace atomic absorption spectrometry</description>
	</form7-row>

	<form7-row>
		<method-code>M19</method-code>
		<description>ICP-MS - Inductively coupled plasma - mass spectrometry</description>
	</form7-row>

	<form7-row>
		<method-code>M20</method-code>
		<description>ICP-OES - Inductively coupled plasma optical emission spectroscopy</description>
	</form7-row>

	<form7-row>
		<method-code>M21</method-code>
		<description>XRF - X-ray fluorescence spectroscopy</description>
	</form7-row>

	<form7-row>
		<method-code>M22</method-code>
		<description>HG ET AAS - Hydride generation electrothermal-atomic absorption spectrometry</description>
	</form7-row>

	<form7-row>
		<method-code>M23</method-code>
		<description>HPLC-FLD - High performance liquid chromatography - fluorescence detection</description>
	</form7-row>

	<form7-row>
		<method-code>M24</method-code>
		<description>GC-MS - Gas chromatography-mass spectrometry</description>
	</form7-row>

	<form7-row>
		<method-code>M25</method-code>
		<description>sampling method deposition : cylindrical deposition gauge</description>
	</form7-row>

	<form7-row>
		<method-code>M26</method-code>
		<description>sampling method deposition : wet-only</description>
	</form7-row>

	<form7-row>
		<method-code>M27</method-code>
		<description>CVAAS - cold vapour atomic absorption spectrometry</description>
	</form7-row>

	<form7-row>
		<method-code>M28</method-code>
		<description>CVAFS - cold vapour atomic fluorescence spectrometry</description>
	</form7-row>

	<form7-row>
		<method-code>M29</method-code>
		<description>Zeeman AAS - Zeeman atomic absorption spectrometry</description>
	</form7-row>
	<form-comments/>
</form7>''' % languages
