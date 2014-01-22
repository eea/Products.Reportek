import unittest
from StringIO import StringIO
from Products.Reportek.XMLInfoParser import detect_schema, detect_single_schema


def setUpModule():
    pass


class XmlDetectionTest(unittest.TestCase):

    def test_create_xml_document(self):
        """ Create a simple XML document, and then verify the schema got sniffed correctly
        """
        content ='''<?xml version="1.0" encoding="UTF-8"?>
        <report xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xml:lang="de"
        xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd">
         </report>'''
        schema_location = detect_schema(StringIO(content))
        self.assertEqual(schema_location, 'http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd')

    def test_create_xml_document2(self):
        """ Create a simple XML document but with an unusual NS identifier,
            and then verify the schema got sniffed correctly
        """
        content = '''<?xml version="1.0" encoding="UTF-8"?>
        <report xmlns:NS0="http://www.w3.org/2001/XMLSchema-instance"
        xml:lang="de"
        NS0:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd">
         </report>'''
        schema_location = detect_schema(StringIO(content))
        self.assertEqual(schema_location, 'http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd')

    def test_create_xml_document_single_schema(self):
        """ Create a XML document with single xsi schema """
        content = '''<?xml version="1.0" encoding="UTF-8"?>
        <report xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://schema.eu/schema.xsd">
         </report>'''
        schema_location = detect_schema(StringIO(content))
        self.assertEqual(schema_location, 'http://schema.eu/schema.xsd')

    def test_create_xml_document_ns1(self):
        """ Create a XML document with namespaces but with an unusual XSI NS identifier,
            and then verify the schema got sniffed correctly
        """
        content = '''<?xml version="1.0" encoding="UTF-8"?>
        <NS1:report xmlns:NS0="http://www.w3.org/2001/XMLSchema-instance" xmlns:NS1="http://ns.org/namespace1"
        NS0:schemaLocation="http://ns.org/namespace1 http://schema.eu/schema.xsd">
         </NS1:report>'''
        schema_location = detect_schema(StringIO(content))
        self.assertEqual(schema_location, 'http://schema.eu/schema.xsd')

    def test_create_xml_document_ns2(self):
        """ Create a XML document with namespaces but with an unusual XSI NS identifier,
            and bad namespace for the schema
            and then verify the schema did not get sniffed
        """
        content = '''<?xml version="1.0" encoding="UTF-8"?>
        <NS1:report xmlns:NS0="http://www.w3.org/2001/WRONG-XMLSchema-instance" xmlns:NS1="http://ns.org/namespace1"
        NS0:schemaLocation="http://ns.org/namespace1 http://schema.eu/schema.xsd">
         </NS1:report>'''
        schema_location = detect_schema(StringIO(content))
        self.assertEqual(schema_location, '')

    def test_create_xml_document_wrong_ns(self):
        """ Create a simple XML document but with a bad namespace for the schema
            and then verify the schema did not get sniffed
        """
        content = '''<?xml version="1.0" encoding="UTF-8"?>
        <report xmlns:xsi="http://www.w3.org/2001/WRONG-XMLSchema-instance"
        xml:lang="de"
        xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd">
         </report>'''
        schema_location = detect_schema(StringIO(content))
        self.assertEqual(schema_location, '')

    def test_bad_xml_document(self):
        """ Create a simple XML document that isn't wellformed
            Verify that the sniffer doesn't abort
        """
        content = '''<?xml version="1.0" encoding="UTF-8"?>
        <report attribute="unclosed
        </report>'''
        schema_location = detect_schema(StringIO(content))
        self.assertEqual(schema_location, '')

    def test_gml_document(self):
        """ Create a GML file in the envelope
            Verify the content_type is text/xml
        """
        content = '''<?xml version="1.0" encoding="UTF-8"?>
    <gml:FeatureCollection
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd"
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:met="http://biodiversity.eionet.europa.eu/schemas/dir9243eec">
    </gml:FeatureCollection>'''

        schema_location = detect_schema(StringIO(content))
        self.assertEqual(schema_location, 'http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd')

    def test_create_dd_document(self):
        """ Create a DD xml file in the envelope
            Verify the content_type is text/xml
            DD files have namespaces
        """
        content = '''<?xml version="1.0" encoding="UTF-8"?>
    <dd207:Station xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:dd207="http://dd.eionet.europa.eu/namespace.jsp?ns_id=207"
    xmlns:dd208="http://dd.eionet.europa.eu/namespace.jsp?ns_id=208"
    xsi:schemaLocation="http://dd.eionet.europa.eu/namespace.jsp?ns_id=207 http://dd.eionet.europa.eu/GetSchema?id=TBL1927">
    <dd207:Row status="new">
        <dd208:Zone_code></dd208:Zone_code>
        <dd208:EoI_station_code>CY0003A</dd208:EoI_station_code>
        <dd208:Local_station_code>NGHosp</dd208:Local_station_code>
        <dd208:Station_name>Nicosia General Hospital</dd208:Station_name>
        <dd208:Longitude_decimal>33.355</dd208:Longitude_decimal>
        <dd208:Latitude_decimal>35.1725</dd208:Latitude_decimal>
        <dd208:Longitude_DDMMSS>+033.21.18</dd208:Longitude_DDMMSS>
        <dd208:Latitude_DDMMSS>+035.10.21</dd208:Latitude_DDMMSS>
        <dd208:Altitude>152</dd208:Altitude>
        <dd208:Station_type_O3>U</dd208:Station_type_O3>
        <dd208:Station_type_EoI>T</dd208:Station_type_EoI>
        <dd208:Area_type_EoI>U</dd208:Area_type_EoI>
    </dd207:Row>
    <dd207:Row status="new">
        <dd208:Zone_code></dd208:Zone_code>
        <dd208:EoI_station_code>CY0002R</dd208:EoI_station_code>
        <dd208:Local_station_code>EMEP</dd208:Local_station_code>
        <dd208:Station_name>Emep-Ayia Marina</dd208:Station_name>
        <dd208:Longitude_decimal>33.0581</dd208:Longitude_decimal>
        <dd208:Latitude_decimal>35.0392</dd208:Latitude_decimal>
        <dd208:Longitude_DDMMSS>+033.03.29</dd208:Longitude_DDMMSS>
        <dd208:Latitude_DDMMSS>+035.02.21</dd208:Latitude_DDMMSS>
        <dd208:Altitude>532</dd208:Altitude>
        <dd208:Station_type_O3>RB</dd208:Station_type_O3>
        <dd208:Station_type_EoI>B</dd208:Station_type_EoI>
        <dd208:Area_type_EoI>RREG</dd208:Area_type_EoI>
    </dd207:Row>
    </dd207:Station>
    '''
        schema_location = detect_schema(StringIO(content))
        self.assertEqual(schema_location, 'http://dd.eionet.europa.eu/GetSchema?id=TBL1927')

    def test_dual_schema_document(self):
        """ Verify that the content sniffer can understand a schemaLocation with
            two namespaces and two schema identifiers
        """
        content = '''<?xml version="1.0" encoding="UTF-8"?>
    <dd207:Station
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:dd207="http://dd.eionet.europa.eu/namespace.jsp?ns_id=207"
    xmlns:dd208="http://dd.eionet.europa.eu/namespace.jsp?ns_id=208"
    xsi:schemaLocation="http://dd.eionet.europa.eu/namespace.jsp?ns_id=207 http://dd.eionet.europa.eu/GetSchema?id=TBL1927
      http://dd.eionet.europa.eu/namespace.jsp?ns_id=208 http://dd.eionet.europa.eu/GetSchema?id=TBL2000">
    </dd207:Station>
    '''
        schema_location = detect_schema(StringIO(content))
        self.assertEqual(schema_location, 'http://dd.eionet.europa.eu/GetSchema?id=TBL1927 http://dd.eionet.europa.eu/GetSchema?id=TBL2000')

    def test_dtd_public_id(self):
        content = ('<!DOCTYPE zz PUBLIC "-//some//public//doctype" '
                   '"http://example.com/my.dtd">\r\n'
                   '<r></r>')
        schema_location = detect_schema(StringIO(content))
        self.assertEqual(schema_location, 'http://example.com/my.dtd')


class XmlSingleSchemaDetectionTest(unittest.TestCase):

    def test_single_schema_no_ns(self):
        content = ('<r xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
                   'xsi:noNamespaceSchemaLocation="http://a.eu/schema1">\n'
                   '</r>')
        schema_location = detect_single_schema(StringIO(content))
        self.assertEqual(schema_location, 'http://a.eu/schema1')

    def test_single_schema(self):
        content = ('<r xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
                   'xsi:schemaLocation="http://a.eu/ns1 http://a.eu/schema1">\n'
                   '</r>')
        schema_location = detect_single_schema(StringIO(content))
        self.assertEqual(schema_location, 'http://a.eu/schema1')

    def test_multiple_schemas(self):
        content = ('<r xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
                   'xsi:schemaLocation="http://a.eu/ns1 http://a.eu/schema1\n'
                   '                    http://a.eu/ns2 http://a.eu/schema2">\n'
                   '</r>')
        schema_location = detect_single_schema(StringIO(content))
        self.assertEqual(schema_location, 'http://a.eu/schema2')
