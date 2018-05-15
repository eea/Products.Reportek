# The contents of this file are subject to the Mozilla Public
# License Version 1.1 (the "License"); you may not use this file
# except in compliance with the License. You may obtain a copy of
# the License at http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS
# IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
# implied. See the License for the specific language governing
# rights and limitations under the License.
#
# The Original Code is Reportek version 2.0.
#
# The Initial Developer of the Original Code is European Environment
# Agency (EEA).  Portions created by Finsiel are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):
# Soren Roug, EEA
# Cornel Nitu, Finsiel Romania

NAMESPACES = ['xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
              'xsi:noNamespaceSchemaLocation="http://cdr.eionet.europa.eu/schemas/envelope-metadata.xsd"',
            ]

from cStringIO import StringIO
from xml.sax import make_parser, SAXParseException
from xml.sax.saxutils import XMLGenerator
from AccessControl import ClassSecurityInfo, getSecurityManager
from AccessControl.Permissions import view
from Globals import InitializeClass

BADATTRS=[ "xsi:noNamespaceSchemaLocation", "xsi:schemaLocation" ]

class StripSchema(XMLGenerator):

    def __init__(self,out,encoding='utf-8'):
        XMLGenerator.__init__(self, out, encoding)

    def startElement(self,name, attrs):
        newattrs = {}
        for key, val in attrs.items():
            if key in BADATTRS:
                continue
            newattrs[key] = val
        XMLGenerator.startElement(self,name, newattrs)

    def processingInstruction(self, target, data):
        pass
    def startDocument(self):
        pass

class XMLMetadata:
    """ Implements a method in the envelope that returns the envelope metadata. The
        metadata must include the list of files, where for each file is reported;
        filename, content-type, title, access permissions, and if the file is an XML
        file the schema identifier.
    """

    security = ClassSecurityInfo()

    def __init__(self, envelope):
        """ """
        self.envelope = envelope
        self._namespaces = NAMESPACES

    security.declarePrivate('_get_namespaces')
    def _get_namespaces(self):
        return ' '.join(map(lambda x: str(x), self._namespaces))

    security.declarePrivate('_xml_encode')
    def _xml_encode(self, s):
        """Encode some special chars"""
        if isinstance(s, unicode): tmp = s.encode('utf-8')
        else: tmp = str(s)
        tmp = tmp.replace('&', '&amp;')
        tmp = tmp.replace('<', '&lt;')
        tmp = tmp.replace('"', '&quot;')
        tmp = tmp.replace('\'', '&apos;')
        tmp = tmp.replace('>', '&gt;')
        return tmp

    def _xml_datetime(self, date):
        """date is a DateTime object. This function returns a string 'dd month_name yyyy hh:mm:ss'"""
        try: return date.strftime('%Y-%m-%dT%H:%M:%SZ')
        except: return ''

    def _document_data(self, document, inline):
        """ return the document metadata """
        restricted = 'no'
        if document.isRestricted():
            restricted = 'yes'
        if inline == 'true' and document.content_type == 'text/xml':
            #FIXME: Only if the user has permission to get the content
            return self._document_instance(document,restricted)
        else:
            return self._document_metadata(document,restricted)

    def _document_metadata(self, document, restricted):
        return '<file name="%s" type="%s" schema="%s" title="%s" restricted="%s" link="%s" uploaded="%s"/>' % \
                                            (self._xml_encode(document.id),
                                            self._xml_encode(document.content_type),
                                            self._xml_encode(document.xml_schema_location),
                                            self._xml_encode(document.title),
                                            restricted,
                                            document.absolute_url(),
                                            document.upload_time().HTML4())

    def _document_instance(self, document, restricted):
        """ return the documents cleaned up content (only XML) """
        xml = []
        xml_a = xml.append  #optimisation
        if getSecurityManager().checkPermission(view, document):
            restricted = 'no'
        else:
            restricted = 'yes'
        xml_a('<instance name="%s" type="%s" schema="%s" title="%s" restricted="%s" link="%s">' % \
                                            (self._xml_encode(document.id),
                                            self._xml_encode(document.content_type),
                                            self._xml_encode(document.xml_schema_location),
                                            self._xml_encode(document.title),
                                            restricted,
                                            document.absolute_url()) )
        outf = StringIO()
        handler = StripSchema(outf)
        parser = make_parser()
        # In case it is more correct to use namespaces
        #parser.setFeature( "http://xml.org/sax/features/namespaces", 1 )
        parser.setContentHandler( handler )
        parser.parse(document.data_file.open())
        outf.seek(0)
        xml_a(outf.read())
        outf.close()
        xml_a('</instance>')
        return ''.join(xml)

    security.declarePrivate('_envelope_metadata')
    def _envelope_metadata(self, envelope, documents):
        """ returns the envelope metadata """
        xml = []
        xml_a = xml.append  #optimisation
        xml_a('<title>%s</title>' % self._xml_encode(envelope.title))
        xml_a('<description>%s</description>' % self._xml_encode(envelope.descr))
        xml_a('<date>%s</date>' % self._xml_datetime(envelope.reportingdate))
        xml_a('<coverage>%s</coverage>' % self._xml_encode(envelope.country))
        xml_a('<countrycode>%s</countrycode>' % self._xml_encode(envelope.getCountryCode()))
        if envelope.dataflow_uris:
            for df in envelope.dataflow_uris:
                xml_a('<obligation>%s</obligation>' % df)
        xml_a('<link>%s</link>' % envelope.absolute_url())
        xml_a('<year>%s</year>' % envelope.year)
        xml_a('<endyear>%s</endyear>' % envelope.endyear)
        xml_a('<partofyear>%s</partofyear>' % self._xml_encode(envelope.partofyear))
        return ''.join(xml)

    security.declareProtected(view, 'envelopeMetadata')
    def envelopeMetadata(self, inline="false"):
        """ """
        tf = { 0:'false', 1:'true'}
        xml = []
        xml_a = xml.append  #optimisation
        doc_objs = [ doc for doc in self.envelope.objectValues('Report Document') ]

        xml_a('<?xml version="1.0" encoding="utf-8"?>')
        p_coll = self.envelope.getParentNode()
        company_id = getattr(p_coll, '_company_id', None)
        old_company_id = getattr(p_coll, 'old_company_id', None)
        a_mapping = {
            None: 'unknown',
            True: 'true',
            False: 'false'
        }
        acceptable = a_mapping.get(self.envelope.is_acceptable())
        if company_id:
            if old_company_id:
                r_env = '<envelope released="%s" company_id="%s" old_company_id="%s" acceptable="%s" %s>' % (tf[self.envelope.released],
                                                                                                             company_id,
                                                                                                             old_company_id,
                                                                                                             acceptable,
                                                                                                             self._get_namespaces())
            else:
                r_env = '<envelope released="%s" company_id="%s" acceptable="%s" %s>' % (tf[self.envelope.released],
                                                                                         company_id,
                                                                                         acceptable,
                                                                                         self._get_namespaces())
        else:
            r_env = '<envelope released="%s" acceptable="%s" %s>' % (tf[self.envelope.released], acceptable, self._get_namespaces())
        xml_a(r_env)
        xml_a(self._envelope_metadata(self.envelope, doc_objs))
        if not self.envelope.canViewContent():
            inline = "false"
        for doc in doc_objs:
            xml_a(self._document_data(doc,inline))
        xml_a("</envelope>")
        return ''.join(xml)

InitializeClass(XMLMetadata)
