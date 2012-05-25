import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')
from configurereportek import ConfigureReportek
from fileuploadmock import FileUploadMock
from utils import create_temp_reposit


def setUpModule():
    global cleanup_temp_reposit
    cleanup_temp_reposit = create_temp_reposit()


def tearDownModule():
    cleanup_temp_reposit()


class DocumentTestCase(ZopeTestCase.ZopeTestCase, ConfigureReportek):

    # Currently the physical document is not renamed if the object in ZODB is moved
    # That makes it difficult to work in the file system
    # This variable can be set to true when we start to fix this problem
    physpath_must_track_zodb = False

    def afterSetUp(self):
        self.createStandardDependencies()
        self.createStandardCollection()
        self.assertTrue(hasattr(self.app, 'collection'),'Collection did not get created')
        self.assertNotEqual(self.app.collection, None)
        self.envelope = self.createStandardEnvelope()

    def create_text_document(self):
        """ Supporting method
            Create a text document in the envelope
            Verify the content_type is text/plain
        """
        myfile = FileUploadMock('C:\\TEMP\\testfile.txt','content here')
        self.envelope.manage_addProduct['Reportek'].manage_addDocument('documentid',
          'Title', myfile)
        self.document = self.envelope.documentid
        self.assertEquals('text/plain', self.document.content_type)

    def test_create_xml_document(self):
        """ Create a simple XML document, and then verify the schema got sniffed correctly
        """
        myfile = FileUploadMock('C:\\TEMP\\testfile.xml','''<?xml version="1.0" encoding="UTF-8"?>
        <report xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xml:lang="de"
        xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd">
         </report>''')
        self.envelope.manage_addProduct['Reportek'].manage_addDocument('documentid',
          'Title', myfile)
        self.assertTrue(hasattr(self.envelope, 'documentid'),'Document did not get created')
        document = self.envelope.documentid
        self.assertEquals('text/xml', document.content_type)
        self.assertEquals('http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd', document.xml_schema_location)

    def test_create_gml_document(self):
        """ Verify the application discovers a GML document
        """
        self.create_gml_document('C:\\TEMP\\testfile.gml')

    def test_create_GML_document(self):
        """ Verify the application discovers a GML document even though the
            suffix is capitalised
        """
        self.create_gml_document('C:\\My Documents\\testfile.GML')

    def create_gml_document(self, filename):
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

        myfile = FileUploadMock(filename,content)
        self.envelope.manage_addProduct['Reportek'].manage_addDocument('documentid',
          'Title', myfile)
        document = self.envelope.documentid
        self.assertEquals('text/xml', document.content_type)
        self.assertEquals('http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd',
            document.xml_schema_location)

    def test_creation(self):
        """ Test that the system can create a document """
        self.create_text_document()
        self.assertTrue(hasattr(self.envelope, 'documentid'),'Document did not get created')
        doc = self.envelope.documentid
        if self.physpath_must_track_zodb:
            self.assertEquals(doc.physicalpath()[-len(doc.absolute_url(1)):], doc.absolute_url(1))

    def test_delete(self):
        """ Test that the system can delete a document """
        self.create_text_document()
        self.assertTrue(hasattr(self.envelope, 'documentid'),'Document did not get created')
        doc = self.envelope.documentid
        if self.physpath_must_track_zodb:
            self.assertEquals(doc.physicalpath()[-len(doc.absolute_url(1)):], doc.absolute_url(1))
        self.assertTrue(os.access(doc.physicalpath(), os.W_OK|os.R_OK),'No document in file system')
        self.assertTrue(doc.id, 'documentid')
        self.envelope.manage_delObjects([doc.id])
        self.assertFalse(hasattr(self.envelope, 'documentid'),'Document did not get deleted from ZODB')
        # ZopeTestCase doesn't call the event handlers that are registered in configure.zcml
#       self.assertFalse(os.access(doc.physicalpath(), os.F_OK),
#           'Document %s did not get deleted from file system' % doc.physicalpath())

    def x_test_rename(self):
        """ Test that the system can rename a document
            For unknown reasons ZopeTestCase won't let you do a rename
        """
        from nose import SkipTest; raise SkipTest
        #self.setRoles(['Manager'])
        #self.setPermissions(['Add Envelopes','Copy or Move'],'Manager')
        self.create_text_document()
        self.assertTrue(hasattr(self.envelope, 'documentid'),'Document did not get created')
        doc = self.envelope.documentid
        if self.physpath_must_track_zodb:
            self.assertEquals(doc.physicalpath()[-len(doc.absolute_url(1)):], doc.absolute_url(1))
        docid = doc.id
        self.envelope.manage_renameObject(docid, "newdocumentid")
        self.assertTrue(doc.id, 'newdocumentid')
        if self.physpath_must_track_zodb:
            self.assertEquals(doc.physicalpath()[-len(doc.absolute_url(1)):], doc.absolute_url(1))

    def x_test_clone(self):
        """ Test that the system can clone a document
            For unknown reasons ZopeTestCase won't let you do a clone
        """
        from nose import SkipTest; raise SkipTest
        #self.setRoles(['Manager'])
        #self.setPermissions(['Add Envelopes'],'Manager')
        self.create_text_document()
        self.assertTrue(hasattr(self.envelope, 'documentid'),'Document did not get created')
        doc = self.envelope.documentid
        if self.physpath_must_track_zodb:
            self.assertEquals(doc.physicalpath()[-len(doc.absolute_url(1)):], doc.absolute_url(1))
        self.envelope.manage_clone(doc, "newdocumentid")
        self.assertTrue(doc.id, 'newdocumentid')
        newdoc = self.envelope.newdocumentid
        if self.physpath_must_track_zodb:
            self.assertEquals(newdoc.physicalpath()[-len(newdoc.absolute_url(1)):], newdoc.absolute_url(1))

    def test_restrict_document(self):
        self.create_text_document()
        self.document.manage_restrictDocument()
	assert self.document.acquiredRolesAreUsedBy('View') == ''

        self.document.manage_unrestrictDocument()
        assert self.document.acquiredRolesAreUsedBy('View') == 'CHECKED'

def test_suite():
    import unittest
    suite = unittest.makeSuite(DocumentTestCase,"test")
    return suite

if __name__ == '__main__':
    framework()

