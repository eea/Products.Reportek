# Script (Python) "EnvelopeCreateEmptyGMLFile"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
##parameters=filename, title, callcontext
# title=Art17: Creates a new instance file
##
# Notice: Maintain the instancefile in SVN, then cut-and-paste it to here
# when changed

filecontent = """<?xml version="1.0" encoding="UTF-8"?>
<gml:FeatureCollection
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd"
xmlns:gml="http://www.opengis.net/gml"
xmlns:met="http://biodiversity.eionet.europa.eu/schemas/dir9243eec">

<gml:metaDataProperty>
<met:info href="%s">
	<met:mapOwner label="Owner of the map">
		<met:organisationName label="Organisation name"/>
		<met:owncontactPerson label="Contact person"/>
		<met:addressDeliveryPoint label="Address (delivery point)"/>
		<met:addressCity label="Address (City)"/>
		<met:addressPostalCode label="Address (Postal code)"/>
		<met:addressCountry label="Address (Country)"/>
		<met:ownaddressEmail label="Address (email)"/>
		<met:ownaddressWebSite label="Address (web site)"/>
	</met:mapOwner>

	<met:mapNotes label="Map notes">
		<met:title label="Title"/>
		<met:footnote label="Footnote"/>
		<met:briefAbstract label="Brief abstract"/>
		<met:keywords label="Keywords"/>
		<met:referenceDate label="Reference date"/>
	</met:mapNotes>

	<met:copyrights label="Copyrights">
		<met:mapinreports label="Main reports"/>
		<met:maponweb label="Map on web"/>
	</met:copyrights>

	<met:methodology label="Methodology description">
		<met:desc label="Description"/>
	</met:methodology>

	<met:datasetsRetrievedFrom label="Datasets retrieved from">
		<met:name label="Name"/>
		<met:organisation label="Organisation/source name"/>
		<met:contactPerson label="Contact person"/>
		<met:addressEmail label="Address (email)"/>
		<met:addressWebSite label="Address (web site)"/>
		<met:productionYear label="Production year"/>
		<met:url label="URL"/>
		<met:otherRelevantInfo label="Other relevant information"/>
	</met:datasetsRetrievedFrom>
        <met:projection label="ESRI projection metadata">PROJCS["ETRS_1989_LAEA_52N_10E",GEOGCS["GCS_ETRS_1989",DATUM["D_ETRS_1989",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Azimuthal_Equal_Area"],PARAMETER["False_Easting",4321000.0],PARAMETER["False_Northing",3210000.0],PARAMETER["Central_Meridian",10.0],PARAMETER["Latitude_Of_Origin",52.0],UNIT["Meter",1.0]]</met:projection>
</met:info>
</gml:metaDataProperty>

<gml:boundedBy>
<gml:Envelope>
<gml:coord>
<gml:X>4286081.93198079</gml:X>
<gml:Y>2602876.05639994</gml:Y>
</gml:coord>
<gml:coord>
<gml:X>4847506.91606231</gml:X>
<gml:Y>2884111.05853185</gml:Y>
</gml:coord>
</gml:Envelope>
</gml:boundedBy>
</gml:FeatureCollection>
""" % filename

callcontext.manage_addDocument(filename, title, filecontent, 'text/xml', '')
