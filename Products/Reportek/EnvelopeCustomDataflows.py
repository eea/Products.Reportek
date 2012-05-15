# -*- coding: utf-8 -*-
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
# The Original Code is Reportek version 1.0.
#
# The Initial Developer of the Original Code is European Environment
# Agency (EEA).  Portions created by Finsiel are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):
# Soren Roug, EEA
# Miruna Badescu, Eau de Web
# Cristian Romanescu, Eau de Web


"""EnvelopeCustomDataflows

This class which Envelope subclasses from contains functions specific to one or more dataflows.
When writing in this class, specify the name of the dataflow as comment first

"""

# Zope imports
from Globals import DTMLFile, MessageDialog, InitializeClass
try: from zope.contenttype import guess_content_type # Zope 2.10 and newer
except: from zope.app.content_types import guess_content_type # Zope 2.9 and older
from AccessControl import ClassSecurityInfo
from DateTime import DateTime
import xmlrpclib
import string
import transaction
from xml.dom.minidom import parseString

# Product specific imports
import RepUtils
from constants import WEBQ_XML_REPOSITORY, CONVERTERS_ID
from zip_content import ZZipFile
from XMLInfoParser import XMLInfoParser
from constants import QAREPOSITORY_ID
import zip_content
from BasicAuthTransport import BasicAuthTransport
from DataflowsManager import DataflowsManager

from os.path import join
import tempfile
import os, traceback
from zipfile import *

# Article 17 constants
GENERAL_SCHEMA = 'http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd'
HABITAT_SCHEMA = 'http://biodiversity.eionet.europa.eu/schemas/dir9243eec/habitats.xsd'
SPECIE_SCHEMA = 'http://biodiversity.eionet.europa.eu/schemas/dir9243eec/species.xsd'
GML_SCHEMA = 'http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd'
ESRI_EXTENSIONS = ['shp', 'shx', 'dbf', 'prj', 'xml']
SHORT_ESRI_EXTENSIONS = ['shp', 'shx', 'dbf', 'prj']
EXTENDED_ESRI_EXTENSIONS = ['shp', 'shx', 'dbf', 'prj', 'xml', 'shp.xml']
OPTIONAL_ESRI_EXTENSIONS = ['xml', 'shp.xml']
ESRI_EXTRAEXTENSIONS = ['.shp', '.shx', '.dbf', '.prj', '.xml']


def invoke_conversion_service(server_name, method_name, url):
    server = xmlrpclib.ServerProxy(server_name)
    method = getattr(server.ConversionService, method_name)
    return method(url, '')


class EnvelopeCustomDataflows:
    """ This class which Envelope subclasses from contains functions specific to one or more dataflows.
    """

    security = ClassSecurityInfo()

    ##################################################
    #   Generic methods for all dataflows
    ##################################################

    #generic method that converts Excel files (XLS or ODS) to XML
    #if the Excel template comes from Data Dictionary
    security.declareProtected('Change Envelopes', 'upload_excel_file')
    upload_excel_file = DTMLFile('dataflows/envelope_upload_excel_file',globals())

    #generic method that converts Excel files (XLS or ODS) to XML
    security.declareProtected('Change Envelopes', 'upload_generic_excel_file')
    upload_generic_excel_file = DTMLFile('dataflows/envelope_upload_generic_excel_file',globals())

    #generic method that uploads a DD file or accompanying data
    security.declareProtected('Change Envelopes', 'upload_dd_file')
    upload_dd_file = DTMLFile('dataflows/envelope_upload_dd_file',globals())

    #generic method that uploads a single file or a zip
    security.declareProtected('Change Envelopes', 'upload_doc_or_zip')
    upload_doc_or_zip = DTMLFile('dataflows/envelope_upload_doc_or_zip',globals())

    def _get_xml_files_by_schema(self, schema):
        """ """
        return [doc.id for doc in self.objectValues('Report Document') if doc.xml_schema_location == schema]

    def _extract_xml_schema(self, p_content):
        """ """
        xml_schema_location = ''
        l_info_handler = XMLInfoParser().ParseXmlFile(p_content)
        if l_info_handler is not None:
            if l_info_handler.xsi_info:
                if l_info_handler.xsi_schema_location:
                    schema = RepUtils.extractURLs(l_info_handler.xsi_schema_location)
                    if isinstance(schema, list):
                        #only the second URL must be stored in the xml_schema_location
                        xml_schema_location = schema[-1]
            elif l_info_handler.xdi_info:
                #DTD information
                if l_info_handler.xdi_public_id is not None:
                    xml_schema_location = l_info_handler.xdi_public_id
                elif l_info_handler.xdi_system_id is not None:
                    xml_schema_location = l_info_handler.xdi_system_id
        return xml_schema_location

    security.declareProtected('Change Envelopes', 'convert_excel_file')
    def convert_excel_file(self, file, restricted='', strict_check=0, conversion_function='', REQUEST=None):
        """ Uploads the original spreadsheet to the envelope
            Attempts the conversion of the DD-based spreadsheet
            If successful, deletes all XML files in the envelope previously generated by that file
            Adds the converted XML files to the envelope
            Returns the error message on REQUEST and the result code if no REQUEST is given:

            -   1 if the conversion succeeded, with or without validation errors
            -   0 if the conversion did not succeed and the original file was uploaded
            -   -1 if no upload has been done

        """
        if not file or type(file) is type('') or not hasattr(file,'filename'):
            if REQUEST is not None:
                return self.messageDialog(
                                message='Upload failed! No file was specified!',
                                action='index_html')
            else:
                return -1
        l_original_content = file.read()
        # build original file id
        l_id = file.filename
        if l_id:
            l_id = l_id[max(string.rfind(l_id,'/'), string.rfind(l_id,'\\'), string.rfind(l_id,':'))+1:]
            l_id = l_id.strip()
            l_id = RepUtils.cleanup_id(l_id)

        # delete previous version of file if exists
        if hasattr(self, l_id):
            self.manage_delObjects(l_id)
        if l_id.lower().endswith('.xls') or l_id.lower().endswith('.xlsx'):
            l_original_type = 'Excel file'
        elif l_id.endswith('.ods'):
            l_original_type = 'Spreadsheet file'
        else:
            l_original_type = 'Data file'
        # upload original file in the envelope
        self.manage_addDocument(id=l_id, title=l_original_type, file=l_original_content, restricted=restricted)
        if strict_check and l_original_type == 'Data file':
            if REQUEST is not None:
                return self.messageDialog(
                                message='The file was successfully uploaded in the envelope.',
                                action='index_html')
            else:
                return 0

        # must commit transaction first, otherwise the file is not accessible from outside
        transaction.commit()
        l_doc = getattr(self, l_id)

        try:
            # XML/RPC call to the converter
            l_server_name = getattr(self, CONVERTERS_ID).remote_converter
            l_url = self.absolute_url() + '/' + l_id
            l_ret_list = invoke_conversion_service(l_server_name, 'convertDD_XML_split', l_url)

            # the result is a dictionary with the following elements:
            #   resultCode (String): 0 – success; 1- converted with validation errors; 2- system error; 3 – schema not found or expired error
            #   resultDescription (String): short textual description about conversion results. If resultCode > 0, then resultDescription contains error message
            #   conversionLog (String): conversion log in HTML format. The result is HTML fragment wrapped into <div class="feedback"> element.
            #   convertedFiles (Array<Struct>): list of dictionaries of converted files
            #       fileName (String): Name of the result file
            #       content (Byte[]): XML content of result document as a UTF-8 encoded byte array

            # delete the XML files that may be previously generated by conversion of the same file
            self.manage_delObjects([x.id for x in self.objectValues('Report Document') if x.content_type == 'text/xml' and x.id.startswith(l_id[:-4] + '_')])
            # delete the feedback that may be previously generated by conversion of the same file
            if hasattr(self, 'conversion_log_%s' % l_id):
                self.manage_delObjects('conversion_log_%s' % l_id)

            l_result = l_ret_list['resultCode']
            if l_result in ['0', '1']:
                # add XML files
                l_converted_files = l_ret_list['convertedFiles']
                for l_xml in l_converted_files:
                    l_xml_id = l_id[:-4] + '_' + l_xml['fileName']
                    self.manage_addDocument(id=l_xml_id, title='Converted from - %s' % l_id, file=l_xml['content'].data, content_type='text/xml', restricted=restricted)
                # Change the original file title to show the conversion result
                l_doc.manage_editDocument(title='%s - converted into an XML delivery' % l_original_type, content_type=l_doc.content_type)
                # add feedback with the conversion log
                self.manage_addFeedback(id='conversion_log_%s' % l_id, 
                        title='Conversion log for file %s' % l_id, 
                        feedbacktext=l_ret_list['conversionLog'], 
                        automatic=1, 
                        content_type='text/html',
                        document_id=l_id)
                if REQUEST is not None:
                    if len(l_converted_files) == 0:
                        l_msg = 'The file was successfully uploaded in the envelope, but not converted into an XML delivery because the file contains no data.'
                    elif l_result == '1':
                        l_msg = 'The file was successfully uploaded in the envelope and converted into an XML delivery. The conversion contains validation warnings - see the Feedback posted for this file for details.'
                    else:
                        l_msg = 'The file was successfully uploaded in the envelope and converted into an XML delivery.'
                    return self.messageDialog(
                                message=l_msg,
                                action='index_html')
                else:
                    return 1
            elif l_result == '2':
                # Change the original file title to show the conversion result
                l_doc.manage_editDocument(title='%s - not converted into an XML delivery' % l_original_type, content_type=l_doc.content_type)
                # add feedback with the conversion log
                self.manage_addFeedback(id='conversion_log_%s' % l_id, 
                        title='Conversion log for file %s' % l_id, 
                        feedbacktext=l_ret_list['conversionLog'], 
                        automatic=1, 
                        content_type='text/html',
                        document_id=l_id)

                if REQUEST is not None:
                    return self.messageDialog(
                                    message='The file was successfully uploaded in the envelope, but not converted into an XML delivery. See the Feedback posted for this file for details.',
                                    action='index_html')
                else:
                    return 0

            elif l_result == '3':
                # Change the original file title to show the conversion result
                l_doc.manage_editDocument(title='%s - not converted into an XML delivery - not based on the most recent reporting template' % l_original_type, content_type=l_doc.content_type)
                # add feedback with the conversion log
                self.manage_addFeedback(id='conversion_log_%s' % l_id, 
                        title='Conversion log for file %s' % l_id, 
                        feedbacktext=l_ret_list['conversionLog'], 
                        automatic=1, 
                        content_type='text/html',
                        document_id=l_id)
                if REQUEST is not None:
                    return self.messageDialog(
                                    message='The file was successfully uploaded in the envelope, but not converted into an XML delivery, because you are not using the most recent reporting template - %s. See the feedback posted for this file for details.' % l_ret_list['resultDescription'],
                                    action='index_html')
                else:
                    return 0
            else:
                if REQUEST is not None:
                    return self.messageDialog(
                                    message='Incorrect result from the Conversion service. The file was successfully uploaded in the envelope, but not converted into an XML delivery.',
                                    action='index_html')
                else:
                    return 0

        except Exception, err:
            # Change the original file title to show the error in conversion
            l_doc.manage_editDocument(title='%s, could not be converted into an XML delivery' % l_original_type, content_type=l_doc.content_type)
            if REQUEST is not None:
                return self.messageDialog(
                                message='The file was successfully uploaded in the envelope, but not converted into an XML delivery because of a system error: %s' % str(err),
                                action='index_html')
            else:
                return 0

    security.declareProtected('Change Envelopes', 'convert_generic_excel_file')
    def convert_generic_excel_file(self, file, restricted='', strict_check=0, REQUEST=None):
        """ Uploads the original spreadsheet to the envelope
            Attempts the conversion of the spreadsheet
            If successful, deletes all XML files in the envelope previously generated by that file
            Adds the converted XML files to the envelope
            Returns the error message on REQUEST and the result code if no REQUEST is given:
            -   1 if the conversion succeeded
            -   0 if the conversion did not succeed and the original file was uploaded
            -   -1 if no upload has been done
        """
        if not file or type(file) is type('') or not hasattr(file,'filename'):
            if REQUEST is not None:
                return self.messageDialog(
                                message='Upload failed! No file was specified!',
                                action='index_html')
            else:
                return -1
        l_original_content = file.read()
        # build original file id
        l_id = file.filename
        if l_id:
            l_id = l_id[max(string.rfind(l_id,'/'), string.rfind(l_id,'\\'), string.rfind(l_id,':'))+1:]
            l_id = l_id.strip()
            l_id = RepUtils.cleanup_id(l_id)

        # delete previous version of file if exists
        if hasattr(self, l_id):
            self.manage_delObjects(l_id)
        if l_id.endswith('.xls') or l_id.endswith('.xlsx'):
            l_original_type = 'Excel file'
        elif l_id.endswith('.ods'):
            l_original_type = 'Spreadsheet file'
        else:
            l_original_type = 'Data file'
        # upload original file in the envelope
        self.manage_addDocument(id=l_id, file=l_original_content, restricted=restricted)
        if strict_check and l_original_type == 'Data file':
            if REQUEST is not None:
                return self.messageDialog(
                                message='The file was successfully uploaded in the envelope, but not converted into an XML delivery because it is not an Excel file.',
                                action='index_html')
            else:
                return 0

        # must commit transaction first, otherwise the file is not accessible from outside
        transaction.commit()
        l_doc = getattr(self, l_id)

        try:
            # XML/RPC call to the converter
            l_server_name = getattr(self, CONVERTERS_ID).remote_converter
            l_url = self.absolute_url() + '/' + l_id
            l_server = xmlrpclib.ServerProxy(l_server_name)
            l_ret_list = l_server.ConversionService.convertExcelToXML(self.absolute_url() + '/' + l_id)

        except Exception, err:
            # Change the original file title to show the error in conversion
            l_doc.manage_editDocument(title='%s, could not be converted into an XML delivery' % l_original_type, content_type=l_doc.content_type)
            if REQUEST is not None:
                return self.messageDialog(
                                message='The file was successfully uploaded in the envelope, but not converted into an XML delivery, probably because you are not using the most recent reporting template.',
                                action='index_html')
            else:
                return 0

        l_result = []
        l_succeded = 0
        # if the conversion succeded, delete the XML files
        # that may be previously generated a conversion of the same file
        if l_ret_list[0] == '0':
            l_succeded = 1
            self.manage_delObjects([x.id for x in self.objectValues('Report Document') if x.content_type == 'text/xml'])

        # The first element is the error code:
        #    0 – STATUS_OK
        #    1 – STATUS_ERR_VALIDATION
        #    2 – STATUS_ERR_SYSTEM
        #    3 – STATUS_ERR_SCHEMA_NOT_FOUND
        if l_ret_list[0] == '0':
            if len(l_ret_list) == 2:
                # Change the original file title
                l_doc.manage_editDocument(title='%s, empty delivery' % l_original_type, content_type=l_doc.content_type)
                if REQUEST is not None:
                    return self.messageDialog(
                                    message='The file was successfully uploaded in the envelope, but not converted into an XML delivery because no data was filled in.',
                                    action='index_html')
                else:
                    return 0
            l_n = len(l_ret_list)
            l_xmls = l_ret_list[2:l_n:2]
            for i, l_xml in enumerate(l_xmls):
                l_data = l_ret_list[2*i+3]
                l_xml = l_xml.replace('.xslt', '')
                if isinstance(l_data, unicode):
                    l_data = l_data.encode('utf-8')
                self.manage_addDocument(id=l_xml, title='Converted from - %s' % l_id, file=l_data, content_type='text/xml', restricted=restricted)
            # Change the original file title to show the conversion result
            l_doc.manage_editDocument(title='%s using correct template - converted into an XML delivery' % l_original_type, content_type=l_doc.content_type)
            if REQUEST is not None:
                return self.messageDialog(
                            message='The file was successfully uploaded in the envelope and converted into an XML delivery.',
                            action='index_html')
            else:
                return 1
        elif l_ret_list[0] in ['1', '3']:
            # Change the original file title to show the conversion result
            l_doc.manage_editDocument(title='%s, not based on template for automatic processing' % l_original_type, content_type=l_doc.content_type)
            if REQUEST is not None:
                return self.messageDialog(
                                message='The file was successfully uploaded in the envelope, but not converted into an XML delivery, probably because you are not using the most recent reporting template.',
                                action='index_html')
            else:
                return 0
        else:
            l_doc.manage_editDocument(title='%s - not converted into an XML delivery' % l_original_type, content_type=l_doc.content_type)
            if REQUEST is not None:
                return self.messageDialog(
                                message='The file was successfully uploaded in the envelope, but not converted into an XML delivery due to the following error: %s' % l_ret_list[1],
                                action='index_html')
            else:
                return -1

    security.declareProtected('Change Envelopes', 'replace_dd_xml')
    def replace_dd_xml(self, file, restricted='', required_schema=[], REQUEST=None):
        """ Receives the file uploaded check that the schema id
            starts with 'http://dd.eionet.europa.eu/GetSchema?id=' or,
            if the 'required_schema' list is provided, it checks that
            the schema is one of those

            If so, it replaces the existing XML files in the envelope,
            otherwise it complains

            Returns the error message on REQUEST and the result code if no REQUEST is given:
                1 if the file was right
                0 if the file was not right
                -1 if there was no file
        """
        if not file or type(file) is type('') or not hasattr(file,'filename'):
            if REQUEST is not None:
                return self.messageDialog(
                                message='Upload failed! No file was specified!',
                                action='index_html')
            else:
                return -1
        #guess content type
        content = file.read()
        content_type, enc = guess_content_type(file.filename, content)
        if content_type == 'text/xml':
            #verify the XML schema
            schema = self._extract_xml_schema(content)
            if (not required_schema and schema.startswith('http://dd.eionet.europa.eu/GetSchema?id=')) or schema in RepUtils.utConvertToList(required_schema):
                #delete all the XML files from this envelope which containt this schema
                xmls = self._get_xml_files_by_schema(schema)
                self.manage_delObjects(xmls)

                #finally, add a Report Document
                return self.manage_addDocument(title='Data file', file=file, restricted=restricted, REQUEST=REQUEST)
            else:
                if REQUEST is not None:
                    return self.messageDialog(
                                message="The file you are trying to upload wasn't generated according to the Data Dictionary schema! File not uploaded!",
                                action='index_html')
                else:
                    return 0
        else:
            if REQUEST is not None:
                return self.messageDialog(
                                message="The file you are trying to upload is not an XML file! File not uploaded!",
                                action='index_html')
            else:
                return 0

    security.declareProtected('Change Envelopes', 'manage_addDocOrZip')
    def manage_addDocOrZip(self, file, restricted='', REQUEST=None):
        """ Adds a file or unpacks a zip in the envelope """
        if not file or type(file) is type('') or not hasattr(file,'filename'):
            if REQUEST is not None:
                return self.messageDialog(
                                message='No file was specified!',
                                action='index_html')
            return 0
        else:
            if file.filename.endswith('.zip'):
                return self.manage_addzipfile(file=file, restricted=restricted, REQUEST=REQUEST)
            else:
                return self.manage_addDocument(file=file, restricted=restricted, REQUEST=REQUEST)

    security.declareProtected('Change Envelopes', 'manage_addDDFile')
    def manage_addDDFile(self, file, restricted='', required_schema=[], REQUEST=None):
        """ Adds a DD file as follows:
            - if the file is a spreadsheet, it calls convert_excel_file
            - if the file XML, it calls replace_dd_xml
            - otherwise it calls manage_addDocOrZip
        """
        if not file or type(file) is type('') or not hasattr(file,'filename'):
            if REQUEST is not None:
                return self.messageDialog(
                                message='No file was specified!',
                                action='index_html')
            return 0
        else:
            l_filename = file.filename.lower()
            if l_filename.endswith('.xls') or l_filename.endswith('.xlsx') or l_filename.endswith('.ods'):
                return self.convert_excel_file(file=file, restricted=restricted, REQUEST=REQUEST)
            elif l_filename.endswith('.xml'):
                return self.replace_dd_xml(file=file, restricted=restricted, required_schema=required_schema, REQUEST=REQUEST)
            elif l_filename.endswith('.zip'):
                return self.manage_addzipfile(file=file, restricted=restricted, REQUEST=REQUEST)
            else:
                return self.manage_addDocument(file=file, restricted=restricted, REQUEST=REQUEST)

    security.declareProtected('View', 'subscribe_all_actors')
    def subscribe_all_actors(self, event_type=''):
        """ Calls UNS for all actors it has found in the work items in the envelope
            and subscribes them to receive notifications to a specified event if the parameter is provided
        """
        engine = self.ReportekEngine
        actors = []
        for w in self.objectValues('Workitem'):
            if w.actor != 'openflow_engine' and w.actor not in actors:
                actors.append(w.actor)
        filters = []
        country_name = str(self.localities_dict().get(self.country, {'name':'Unknown'})['name'])
        for df in self.dataflow_uris:
            if event_type:
                filters.append({'http://rod.eionet.europa.eu/schema.rdf#locality': country_name, 'http://rod.eionet.europa.eu/schema.rdf#obligation': engine.getDataflowTitle(df), 
                'http://rod.eionet.europa.eu/schema.rdf#event_type': event_type})
            else:
                filters.append({'http://rod.eionet.europa.eu/schema.rdf#locality': country_name, 'http://rod.eionet.europa.eu/schema.rdf#obligation': engine.getDataflowTitle(df)})

        server = xmlrpclib.Server(engine.UNS_server + '/rpcrouter', BasicAuthTransport(engine.UNS_username, engine.UNS_password),verbose=0)
        for act in actors:
            server.UNSService.makeSubscription(engine.UNS_channel_id, act, filters)

    ##################################################
    # Art. 17 - Species and Habitats
    # to be replaced by an XML parser that extracts
    # files referenced by other files
    ##################################################

    security.declareProtected('View', 'getReferencedFiles')
    def getReferencedFiles(self, p_document):
        """ Returns the Report Document objects which are referenced in an XML file
            In the future, parse XML and get referenced file ids
            Now just check for id patterns
        """
        l_ret = []
        if p_document.xml_schema_location == HABITAT_SCHEMA:
            l_nr = p_document.id[len('habitattype-'):-len('.xml')]
            for x in ['map-range-', 'map-favourable-range-', 'map-distribution-', 'map-favourable-distribution-']:
                 if hasattr(self, x + l_nr + '.gml'):
                    l_ret.append(self._getOb(x + l_nr + '.gml'))
            return l_ret
        elif p_document.xml_schema_location == SPECIE_SCHEMA:
            l_nr = p_document.id[len('species-'):-len('.xml')]
            for x in ['map-range-spec-', 'map-distribution-spec-', 'map-favourable-range-spec-']:
                 if hasattr(self, x + l_nr + '.gml'):
                    l_ret.append(self._getOb(x + l_nr + '.gml'))
            return l_ret
        elif p_document.xml_schema_location == GML_SCHEMA:
            doc_identifier = p_document.id[:-3]
            for x in EXTENDED_ESRI_EXTENSIONS:
                 if hasattr(self, doc_identifier + x):
                    l_ret.append(self._getOb(doc_identifier + x))
            return l_ret
        return []

    security.declareProtected('View', 'getBaseDocuments')
    def getBaseDocumentsCounts(self):
        """ returns the count of each type of document """
        type_to_schema = {'general_report':GENERAL_SCHEMA,
                          'habitats':HABITAT_SCHEMA,
                          'species':SPECIE_SCHEMA,
                          'other':GML_SCHEMA}
        objects = [x for x in self.objectValues('Report Document')]
        counts = {}
        for i in type_to_schema.keys():
            if i != 'other':
                counts[i] = len([x for x in objects if x.xml_schema_location == type_to_schema[i]])
            else:
                tmp_count = 0
                for x in objects:
                    if x.xml_schema_location == type_to_schema['other']:
                        if not self.testValidMapName(x.id, [], 0):
                            tmp_count += 1
                    else:
                        if not x.xml_schema_location in type_to_schema.values():
                            tmp_count += 1
                        if self.testAssociatedESRI(x.id):
                            tmp_count -= 1
                counts[i] = tmp_count
        return counts

    security.declareProtected('View', 'testAssociatedESRI')
    def testAssociatedESRI(self, file_id):
        """ """
        res = False
        l_length = -3
        if file_id.find('shp.xml') != -1:
            l_length = -7
        doc_identifier = file_id[:l_length]
        doc_extension = file_id[l_length:]
        if self.testValidMapName(doc_identifier+'gml', [], 0):
            if doc_extension in EXTENDED_ESRI_EXTENSIONS:
                if hasattr(self, doc_identifier + 'gml'):
                    res = True
        return res

    security.declareProtected('View', 'getBaseDocuments')
    def getBaseDocuments(self, p_type, start, skey, rkey, query, prefix=''):
        """ returns the 'p_type' documents batched and filtered by 'query' """
        type_to_schema = {'general_report':GENERAL_SCHEMA,
                          'habitats':HABITAT_SCHEMA,
                          'species':SPECIE_SCHEMA,
                          'other':GML_SCHEMA}
        if p_type != 'other':
            objects = [x for x in self.objectValues('Report Document') if x.xml_schema_location == type_to_schema[p_type]]
        else:
            objects = []
            objects_add = objects.append
            objects_remove = objects.remove
            for x in self.objectValues('Report Document'):
                if x.xml_schema_location == type_to_schema['other']:
                    if not self.testValidMapName(x.id, [], 0):
                        objects_add(x)
                else:
                    if not x.xml_schema_location in type_to_schema.values():
                        objects_add(x)
                    if self.testAssociatedESRI(x.id):
                        objects_remove(x)

        total_unfiltered = len(objects)

        query = query.strip()
        query = query.lower()
        query = query.replace(' ', '-')
        l_query = query
        if query != '':
            if (l_query[0]=='*'):l_query=l_query[1:]
            if (l_query[-1:]=='*'):l_query=l_query[:-1]
            if (query[0]=='*'):
                if(query[-1:]=='*'):
                    objects = [x for x in objects if x.id[len(prefix):-len('.xml')].find(l_query)!=-1]
                else:
                    objects = [x for x in objects if x.id[len(prefix):-len('.xml')].endswith(l_query)]
            else:
                if(query[-1:]=='*'):
                    objects = [x for x in objects if x.id[len(prefix):-len('.xml')].startswith(l_query)]
                else:
                    objects = [x for x in objects if x.id[len(prefix):-len('.xml')] == l_query]
        if self.validParams(skey, rkey):
            objects = RepUtils.utSortByAttr(objects, skey, rkey)
        #paging
        objects_perpage = 10
        total = len(objects)
        try: start = abs(int(start))
        except: start = 1
        start = min(start, total)
        stop = min(start + objects_perpage - 1, total)
        prev = next = -1
        if start != 1:
            prev = start - objects_perpage
            if prev < 0: prev = -1
        if stop < total: next = stop + 1
        return objects, start, stop, total, prev, next, total_unfiltered

    security.declarePrivate('validParams')
    def validParams(self, sortby, how):
        """ Validate sort parameters """
        res = 1
        if (how != '' and how != '1'):
            res = 0
        else:
            if (self.valideObjectProperty(sortby)):
                res = 1
            else:
                res = 0
        return res

    def valideObjectProperty(self, param):
        """ Check if a string is a valid sortable property """
        return param in ['id', 'title', 'upload_time', 'size']

    security.declareProtected('Change Envelopes', 'envelope_zip_draft')
    def envelope_zip_draft(self, REQUEST, RESPONSE):
        """ Go through the envelope and find all the external documents
            then zip them and send the result to the user

            fixme: It is not impossible that the client only wants part of the
            zipfile, as in index_html of Document.py due to the partial
            requests that can be made with HTTP
        """
        path = INSTANCE_HOME

        for item in self._repository:
            path = join(path,item)
        tempfile.tempdir = path
        tmpfile = tempfile.mktemp(".temp")

        request = self.REQUEST
        parents = request.PARENTS
        parent = parents[0]

        outzd = ZipFile(tmpfile, "w", ZIP_DEFLATED)

        for p in parent.objectValues('Report Document'):
            outzd.write(p.physicalpath(), str(p.getId()))

        outzd.close()
        stat = os.stat(tmpfile)

        RESPONSE.setHeader('Content-Type', 'application/x-zip')
        RESPONSE.setHeader('Content-Disposition',
             'attachment; filename="%s.zip"' % self.id)
        RESPONSE.setHeader('Content-Length', stat[6])
        self._copy(tmpfile, RESPONSE)
        os.unlink(tmpfile)
        return ''

    security.declareProtected('Change Envelopes', 'addGisFile')
    addGisFile = DTMLFile('dataflows/Art17/envelopeAddGisFile',globals())

    security.declareProtected('Change Envelopes', 'addGisConfirmed')
    addGisConfirmed = DTMLFile('dataflows/Art17/envelopeAddGisConfirmed',globals())

    security.declareProtected('View', 'documents_management_section_habitats')
    documents_management_section_habitats = DTMLFile('dataflows/Art17/envelopeDocumentsManagement_section_habitats',globals())

    security.declareProtected('Change Envelopes', 'listAddGisOptions')
    listAddGisOptions = DTMLFile('dataflows/Art17/envelopeAddGisOptions',globals())

    security.declareProtected('Change Envelopes', 'getDocumentsByType')
    def getDocumentsByType(self, doc_type):
        """ """
        res = []
        res_add = res.append

        for doc in self.objectValues('Report Document'):
            doc_schema = doc.xml_schema_location
            if doc_schema == HABITAT_SCHEMA and doc_type == 'hab':
                habitatype = doc.id[len('habitattype-'):-len('.xml')]
                res_add(habitatype)
            elif doc_schema == SPECIE_SCHEMA and doc_type == 'spec':
                speciename = doc.id[len('species-'):-len('.xml')].replace('-', ' ')
                res_add(speciename)
        return res

    security.declareProtected('View', 'generateFileName')
    def generateFileName(self, category, filetype, identifier):
        """ """
        filename = ''
        if category == 'hab':
            filename = 'map-%s-%s.gml' % (filetype, identifier)
        elif category == 'spec':
            identifier = identifier.replace(' ', '-')
            filename = 'map-%s-spec-%s.gml' % (filetype, identifier)
        return filename

    security.declareProtected('Change Envelopes', 'getGmlFileAssocFactsheet')
    def getGmlFileAssocFactsheet(self, filename):
        """ """
        if filename.find('spec') != -1:
            return 'spec'
        return 'hab'

    security.declareProtected('Change Envelopes', 'generateGmlFileTitle')
    def generateGmlFileTitle(self, filename):
        """ """
        file_title = ''
        if self.getGmlFileAssocFactsheet(filename) == 'spec':
            for name in filename.split('-')[1:3]:
                if name != 'spec' and file_title:
                    file_title = '%s %s' % (file_title, name)
                elif  name != 'spec' and not file_title:
                    file_title = '%s' % name
            file_title = '%s map' % file_title
        elif  self.getGmlFileAssocFactsheet(filename) == 'hab':
            file_title = '%s map' % ' '.join(filename.split('-')[1:-1])
        return file_title.capitalize()

    security.declareProtected('View', 'testExistingFile')
    def testExistingFile(self, filename):
        """ """
        return hasattr(self, filename)

    security.declareProtected('Change Envelopes', 'createEmptyGmlFile')
    def createEmptyGmlFile(self, filetype='', identifier='', add_target='', add_type='', confirmed=0, REQUEST=None):
        """ """
        p_go = REQUEST.get('go', '')
        if not identifier and p_go == 'Continue':
            REQUEST.SESSION.set('err', 'Please select a file from the list above!')
            REQUEST.RESPONSE.redirect('%s/addGisFile?add_target=%s&add_type=%s' %
                    (self.absolute_url(), add_target, add_type))
        elif identifier and p_go == 'Continue':
            title = '%s map' % filetype.replace('-', ' ').capitalize()
            filename = self.generateFileName(add_target, filetype, identifier)
            if not self.testExistingFile(filename):
                self.EnvelopeCreateEmptyGMLFile(filename, title, self)
                REQUEST.RESPONSE.redirect('%s/%s/flash_document' % (self.absolute_url(), filename))
            else:
                REQUEST.SESSION.set('err', 'The file you want to create already exists. Please confirm if you want to overwrite it.')
                REQUEST.RESPONSE.redirect('%s/addGisConfirmed?file=%s' % (self.absolute_url(), filename))
        else:
            REQUEST.RESPONSE.redirect('%s/addGisFile' % self.absolute_url())

    security.declareProtected('Change Envelopes', 'create_empty_gml_file')
    def create_empty_gml_file(self, file_id, REQUEST=None):
        """ """
        p_go = REQUEST.get('go', '')
        if p_go == 'Add':
            title = self.generateGmlFileTitle(file_id)
            self.manage_delObjects(file_id)
            self.EnvelopeCreateEmptyGMLFile(file_id, title, self)
            REQUEST.RESPONSE.redirect('%s/%s/flash_document' % (self.absolute_url(), file_id))
        else:
            REQUEST.RESPONSE.redirect('%s/addGisFile?add_type=empty&add_target=%s' %
                    (self.absolute_url(), self.getGmlFileAssocFactsheet(file_id)))

    security.declareProtected('Change Envelopes', 'uploadESRIArt17')
    uploadESRIArt17 = DTMLFile('dataflows/Art17/envelopeUploadESRI',globals())

    security.declareProtected('Change Envelopes', 'uploadESRIFiles')
    def uploadESRIFiles(self, filetype='', identifier='', add_target='', add_type='', confirmed=0, REQUEST=None):
        """ """
        p_go = REQUEST.get('go', '')
        if not identifier and p_go == 'Continue':
            REQUEST.SESSION.set('err', 'Please select a file from the list above!')
            REQUEST.RESPONSE.redirect('%s/addGisFile?add_target=%s&add_type=%s' %
                    (self.absolute_url(), add_target, add_type))
        elif identifier and p_go == 'Continue':
            filename = self.generateFileName(add_target, filetype, identifier)
            REQUEST.RESPONSE.redirect('%s/uploadESRIArt17?file=%s' % (self.absolute_url(), filename))
        else:
            REQUEST.RESPONSE.redirect('%s/addGisFile' % self.absolute_url())

    security.declareProtected('Change Envelopes', 'upload_esri_files')
    def upload_esri_files(self,  file_id, shx_file, shp_file, dbf_file, meta_file, prj_file, REQUEST=None):
        """ """
        p_go = REQUEST.get('go', '')
        to_delete = 0
        if p_go == 'Add':
            title = self.generateGmlFileTitle(file_id)
            if not self.testExistingFile(file_id):
                to_delete = 1
                self.EnvelopeCreateEmptyGMLFile(file_id, title, self)
            msg = self.convert_esri_to_xml(file_id, shx_file, shp_file, dbf_file, meta_file, prj_file)
            if msg == 'done':
                REQUEST.RESPONSE.redirect('%s/%s/manage_edit_document' % (self.absolute_url(), file_id))
            else:
                if to_delete:
                    self.manage_delObjects(file_id)
                REQUEST.SESSION.set('err', msg)
                REQUEST.RESPONSE.redirect('%s/uploadESRIArt17?file=%s' % (self.absolute_url(), file_id))
        else:
            REQUEST.RESPONSE.redirect('%s/addGisFile?add_type=esri&add_target=%s' %
                    (self.absolute_url(), self.getGmlFileAssocFactsheet(file_id)))

    security.declareProtected('Change Envelopes', 'uploadGML')
    uploadGML = DTMLFile('dataflows/Art17/envelopeUploadGML',globals())

    security.declareProtected('Change Envelopes', 'uploadGMLFile')
    def uploadGMLFile(self, filetype='', identifier='', add_target='', add_type='', confirmed=0, REQUEST=None):
        """ """
        p_go = REQUEST.get('go', '')
        if not identifier and p_go == 'Continue':
            REQUEST.SESSION.set('err', 'Please select a file from the list above!')
            REQUEST.RESPONSE.redirect('%s/addGisFile?add_target=%s&add_type=%s' %
                    (self.absolute_url(), add_target, add_type))
        elif identifier and p_go == 'Continue':
            filename = self.generateFileName(add_target, filetype, identifier)
            REQUEST.RESPONSE.redirect('%s/uploadGML?file=%s' % (self.absolute_url(), filename))
        else:
            REQUEST.RESPONSE.redirect('%s/addGisFile' % self.absolute_url())

    security.declareProtected('Change Envelopes', 'upload_gml_file')
    def upload_gml_file(self, file_id, file, REQUEST=None):
        """ """
        import os
        p_go = REQUEST.get('go', '')
        msg_err = []
        file_exist = self.testExistingFile(file_id)

        if p_go == 'Add':
            if not len(file.filename) > 0:
                msg_err.append('you must specify a file!')
            title = self.generateGmlFileTitle(file_id)
            if not file_exist:
                self.EnvelopeCreateEmptyGMLFile(file_id, title, self)
            gmlfile_obj = getattr(self, file_id, None)

            # backup data
            file_physicalpath = gmlfile_obj.physicalpath()
            f = open(file_physicalpath)
            file_bkp_content = f.read()
            f.close()

            if gmlfile_obj.get_accept_time():
                msg_err.append('Document cannot be changed since it has already accepted by the client')
            else:
                gmlfile_obj.manage_file_upload(file)
                if gmlfile_obj.xml_schema_location != GML_SCHEMA:
                    msg_err.append('the uploaded file is not constructed according to the specified schema!')
                if gmlfile_obj.content_type != 'text/xml':
                    msg_err.append('the uploaded file is not a valid XML file!')

            if not len(msg_err):
                REQUEST.RESPONSE.redirect('%s/manage_edit_document' % gmlfile_obj.absolute_url())
            else:
                if file_exist:
                    gmlfile_obj.manage_file_upload(file_bkp_content)
                else:
                    self.manage_delObjects(file_id)
                REQUEST.SESSION.set('err', msg_err)
                REQUEST.RESPONSE.redirect('%s/uploadGML?file=%s' % (self.absolute_url(), file_id))
        else:
            REQUEST.RESPONSE.redirect('%s/addGisFile?add_type=gml&add_target=%s' %
                    (self.absolute_url(), self.getGmlFileAssocFactsheet(file_id)))

    security.declareProtected('Change Envelopes', 'addZipFile')
    addZipFile = DTMLFile('dataflows/Art17/envelopeAddZipFile',globals())

    security.declareProtected('Change Envelopes', 'add_zip_file')
    def add_zip_file(self, REQUEST=None):
        """ """
        p_go = REQUEST.get('go', '')
        if p_go == 'Done':
            REQUEST.RESPONSE.redirect('%s' % self.absolute_url())
        else:
            REQUEST.RESPONSE.redirect('%s/addZipFile' % self.absolute_url())

    security.declareProtected('View', 'getHabitatInfo')
    def getHabitatInfo(self):
        """ """
        habitat_info = {}
        for hab_struct in self.Art17habitattypes():
            if hab_struct[1]:
                habitat_info[hab_struct[1]] = hab_struct[2]
        return habitat_info

    security.declareProtected('View', 'getSpeciesInfo')
    def getSpeciesInfo(self):
        """ """
        species_info = {}
        for spec_struct in self.Art17species():
            if spec_struct[3]:
                spec_id = spec_struct[3].replace(' ', '-').lower()
                species_info[spec_id] = spec_struct[3]
        return species_info

    security.declareProtected('View', 'getMapTypes')
    def getMapTypes(self):
        """ """
        return ['range', 'favourable-range', 'distribution', 'favourable-distribution']

    security.declareProtected('Change Envelopes', 'test_valid_map_name')
    def test_valid_map_name(self, name, namelist, zip_search):
        """ """
        if zip_search:
            return name in namelist or self.testExistingFile(name)
        else:
            return self.testExistingFile(name)

    security.declareProtected('Change Envelopes', 'testValidMapName')
    def testValidMapName(self, filename, namelist, zip_search=1):
        """ """
        if not filename[:4] == 'map-':
            return False

        file_ext = filename[-4:]
        file_name = filename[:-4]
        if file_ext == '.xml':
            if filename[-8:] == '.shp.xml':
                file_name = filename[:-8]
        habitat_info = self.getHabitatInfo()

        if filename.find('-spec') > 0:
            spec_name = ''
            l_list = file_name.split('-')
            l_position = l_list.index('spec') + 1
            for k in l_list[l_position:]:
                spec_name = '%s-%s' % (spec_name, k)
            spec_name = spec_name[1:]
            factsheet_name = 'species-%s.xml' % spec_name
        else:
            hab_code = file_name.split('-')[-1]
            if not hab_code in habitat_info.keys():
                return False
            factsheet_name = 'habitattype-%s.xml' % hab_code

        if file_ext == '.gml':
            if not self.test_valid_map_name(factsheet_name, namelist, zip_search):
                return False
        elif file_ext in ESRI_EXTRAEXTENSIONS:
            if not self.test_valid_map_name(factsheet_name, namelist, zip_search):
                return False
            for k in SHORT_ESRI_EXTENSIONS:
                esri_name = '%s.%s' % (file_name, k)
                if zip_search:
                    if not esri_name in namelist:
                        return False
                else:
                    if not self.testExistingFile(esri_name):
                        return False
        else:
            return False

        return True

    security.declareProtected('Change Envelopes', 'processZipNamelist')
    def processZipNamelist(self, namelist):
        """ """
        report = {'valid':{},
                  'bad':{},
                  'other':{},
                  'error':{},
                  'info':{'overwrite': (0, 0)}}
        count_overwrite = 0
        overwrite = 0
        habitat_info = self.getHabitatInfo()

        for filename in namelist:
            l_key = ''
            l_value = ''
            msg_err = ''
            l_warning = '-'
            warning_esri = ''

            if self.testValidMapName(filename, namelist):
                file_ext = filename[-3:]
                if file_ext == 'gml':
                    # GML file
                    file_title = self.generateGmlFileTitle(filename)
                else:
                    # ESRI file
                    gml_asoc_file = '%s.gml' % filename[:-4]
                    if file_ext == 'xml':
                        if filename.endswith('.shp.xml'):
                            gml_asoc_file = '%s.gml' % filename[:-8]
                    file_title = '%s file of the %s' % (file_ext.upper(), self.generateGmlFileTitle(filename))
                    if self.testExistingFile(gml_asoc_file):
                        warning_esri = 'action: overwrite'
                    else:
                        warning_esri = 'action: add'
                    if filename.endswith('.shp.xml'):
                        warning_esri = ''
            elif self.test_filename_species(filename):
                # Species factsheet
                file_title = filename[8:-4].replace('-', ' ').capitalize()
            elif filename[:12] == 'habitattype-' and filename[-4:] == '.xml' and filename[12:-4] in habitat_info.keys():
                # Habitat factsheet
                file_title = habitat_info[filename[12:-4]]
            elif filename == 'general-report.xml':
                # General report
                file_title = 'General report for art 17'
            else:
                if filename.find('/') > 0 or filename.find('\\') > 0:
                    msg_err = 'the archive has a hierarchical structure'
                else:
                    msg_err = 'incorrect filename'

            # set info
            if len(msg_err) > 0:
                l_key = 'bad'
                l_value = msg_err
            else:
                l_key = 'valid'
                l_exist = self.testExistingFile(filename)
                l_warning = 'action: add'
                if l_exist:
                    count_overwrite += 1
                    overwrite = 1
                    l_warning = 'action: overwrite'

                if warning_esri:
                    tmp_filename = '%s.gml' % filename[:-4]
                    tmp_file_title = self.generateGmlFileTitle(filename)
                    tmp_exist = self.testExistingFile(tmp_filename)
                    if warning_esri == 'action: overwrite':
                        if tmp_filename not in report['other'].keys():
                            count_overwrite += 1
                        overwrite = 1
                        tmp_warning = 'action: overwrite'
                    else:
                        tmp_warning = 'action: add'
                    tmp_value = (tmp_file_title, tmp_exist, tmp_warning)
                    report['other'][tmp_filename] = tmp_value

                l_value = (file_title, l_exist, l_warning)

            report[l_key][filename] = l_value

        report['info']['overwrite'] = (overwrite, count_overwrite)
        return report

    security.declareProtected('Change Envelopes', 'processZipFile')
    def processZipFile(self, file, overwrite):
        """ """
        tmp_esri_processed = []
        try:
            zipfile = ZZipFile(file)
        except Exception, e:
            report = {'valid':{},
                      'bad':{'%s' % file.filename: '%s' % e},
                      'other':{},
                      'error':{},
                      'skipped':{},
                      'info':{'overwrite': (0, 0)}}
            return report

        zip_namelist = zipfile.namelist()

        # generate Zip files report
        report = self.processZipNamelist(zip_namelist)

        # unzip files from the archive
        info_overwrite = report['info']['overwrite'][0]
        test_overwrite = not overwrite
        if overwrite and info_overwrite:
            test_overwrite = False

        # add/update content
        if not len(report['bad'].keys()) > 0 and test_overwrite:
            valid_list = report['valid'].keys()
            ignore_list = []
            for filename in valid_list:
                zipfile.setcurrentfile(filename)
                file_id = filename
                file_ext = file_id[-3:]
                file_basename = file_id[:-4]
                if filename[-7:] == 'shp.xml':
                    file_ext = file_id[-7:]
                    file_basename = file_id[:-8]
                file_datetime = zipfile.getinfo(filename).date_time

                # test datetime of GML and ESRI files
                if file_id[:4] == 'map-':
                    try:
                        if file_ext == 'gml':
                            tmp_datetime = zipfile.getinfo('%s.shp' % file_basename).date_time
                        else:
                            tmp_datetime = zipfile.getinfo('%s.gml' % file_basename).date_time

                        if file_datetime < tmp_datetime:
                            if file_ext == 'gml':
                                ignore_list.append(file_id)
                                if report['info']['overwrite'][1] and report['valid'][file_id][1]:
                                    tmp_res = report['info']['overwrite'][1] - 1
                                    if tmp_res == 0:    tmp_ovr = 0
                                    else:               tmp_ovr = 1
                                    report['info']['overwrite'] = (tmp_ovr, tmp_res)
                                del report['valid'][file_id]
                                report['error'][file_id] = 'File not generated! The Zip contains newer ERSI files corresponding to this GML.'
                            else:
                                for k in SHORT_ESRI_EXTENSIONS:
                                    tmp_filename = '%s.%s' % (file_basename, k)
                                    ignore_list.append(tmp_filename)
                                    if report['info']['overwrite'][1] and report['valid'][tmp_filename][1]:
                                        tmp_res = report['info']['overwrite'][1] - 1
                                        if tmp_res == 0:    tmp_ovr = 0
                                        else:               tmp_ovr = 1
                                        report['info']['overwrite'] = (tmp_ovr, tmp_res)
                                    del report['valid'][tmp_filename]
                                    report['error'][tmp_filename] = 'File not generated! The Zip contains a newer GML file associated to this ESRI file.'
                                for k in OPTIONAL_ESRI_EXTENSIONS:
                                    tmp_filename = '%s.%s' % (file_basename, k)
                                    if tmp_filename in report['valid'].keys():
                                        ignore_list.append(tmp_filename)
                                        if report['info']['overwrite'][1] and report['valid'][tmp_filename][1]:
                                            tmp_res = report['info']['overwrite'][1] - 1
                                            if tmp_res == 0:    tmp_ovr = 0
                                            else:               tmp_ovr = 1
                                            report['info']['overwrite'] = (tmp_ovr, tmp_res)
                                        del report['valid'][tmp_filename]
                                        report['error'][tmp_filename] = 'File not generated! The Zip contains a newer GML file associated to this ESRI file.'
                    except:
                        pass

                if file_id not in ignore_list:
                    file_title = report['valid'][filename][0]
                    file_content = zipfile.read()

                    if file_id[:4] == 'map-' and file_ext in EXTENDED_ESRI_EXTENSIONS and not file_basename in tmp_esri_processed:
                        # ESRI files
                        tmp_content = file_content

                        if file_ext != 'prj':
                            zipfile.setcurrentfile('%s.prj' % file_basename)
                            prj_file = zipfile.read()
                        if file_ext != 'shp':
                            zipfile.setcurrentfile('%s.shp' % file_basename)
                            shp_file = zipfile.read()
                        if file_ext != 'shx':
                            zipfile.setcurrentfile('%s.shx' % file_basename)
                            shx_file = zipfile.read()
                        if file_ext != 'dbf':
                            zipfile.setcurrentfile('%s.dbf' % file_basename)
                            dbf_file = zipfile.read()
                        try:
                            if not file_ext in OPTIONAL_ESRI_EXTENSIONS:
                                zipfile.setcurrentfile('%s.%s' % (file_basename, file_ext))
                                xml_file = zipfile.read()
                        except:
                            xml_file = ''

                        if file_ext == 'prj':
                            prj_file = tmp_content
                        if file_ext == 'shp':
                            shp_file = tmp_content
                        if file_ext == 'shx':
                            shx_file = tmp_content
                        if file_ext == 'dbf':
                            dbf_file = tmp_content
                        if file_ext in OPTIONAL_ESRI_EXTENSIONS:
                            xml_file = tmp_content

                        msg = self.zip_to_xml_esri('%s' % file_basename, shx_file, shp_file, dbf_file, xml_file, prj_file)
                        tmp_esri_processed.append(file_basename)

                        for k in SHORT_ESRI_EXTENSIONS:
                            tmp_filename = '%s.%s' % (file_basename, k)
                            ignore_list.append(tmp_filename)
                        for k in OPTIONAL_ESRI_EXTENSIONS:
                            tmp_filename = '%s.%s' % (file_basename, k)
                            if tmp_filename in report['valid'].keys():
                                ignore_list.append(tmp_filename)

                        if msg != 'done':
                            add_content = False
                            gml_filename = '%s.gml' % file_basename
                            report['error'][gml_filename] = 'file not generated! Check corresponding ESRI files for errors!'
                            for k in SHORT_ESRI_EXTENSIONS:
                                tmp_filename = '%s.%s' % (file_basename, k)
                                if report['info']['overwrite'][1] and report['valid'][tmp_filename][1]:
                                    tmp_res = report['info']['overwrite'][1] - 1
                                    if tmp_res == 0:    tmp_ovr = 0
                                    else:               tmp_ovr = 1
                                    report['info']['overwrite'] = (tmp_ovr, tmp_res)
                                del report['valid'][tmp_filename]
                                report['error'][tmp_filename] = 'file not generated. %s' % msg
                                if gml_filename in report['other'].keys():
                                    gml_title = report['other'][gml_filename][0]
                                    report['other'][gml_filename] = (gml_title, False, 'file not generated')
                            for k in OPTIONAL_ESRI_EXTENSIONS:
                                tmp_filename = '%s.%s' % (file_basename, k)
                                if tmp_filename in report['valid'].keys():
                                    if report['info']['overwrite'][1] and report['valid'][tmp_filename][1]:
                                        tmp_res = report['info']['overwrite'][1] - 1
                                        if tmp_res == 0:    tmp_ovr = 0
                                        else:               tmp_ovr = 1
                                        report['info']['overwrite'] = (tmp_ovr, tmp_res)
                                    del report['valid'][tmp_filename]
                                    report['error'][tmp_filename] = 'file not generated. %s' % msg
                                    if gml_filename in report['other'].keys():
                                        gml_title = report['other'][gml_filename][0]
                                        report['other'][gml_filename] = (gml_title, False, 'file not generated')
                        else:
                            for k in SHORT_ESRI_EXTENSIONS:
                                tmp_file_id = '%s.%s' % (file_basename, k)
                                tmp_file_title = report['valid'][tmp_file_id][0]
                                tmp_file_content = eval('%s_file' % k)
                                self.add_art17_file(tmp_file_id, tmp_file_title, tmp_file_content)
                            for k in OPTIONAL_ESRI_EXTENSIONS:
                                tmp_file_id = '%s.%s' % (file_basename, k)
                                if tmp_file_id in report['valid'].keys():
                                    tmp_file_title = report['valid'][tmp_file_id][0]
                                    tmp_file_content = eval('xml_file')
                                    self.add_art17_file(tmp_file_id, tmp_file_title, tmp_file_content)

                    if not file_id in ignore_list:
                        self.add_art17_file(file_id, file_title, file_content)

        return report

    def add_art17_file(self, file_id, file_title, file_content):
        """ """
        if self.testExistingFile(file_id):
            doc_ob = getattr(self, file_id)
            if not doc_ob.get_accept_time():
                doc_ob.manage_file_upload(file_content, '')
        else:
            self.manage_addDocument(file_id, file_title, file_content, '','')

    security.declareProtected('Change Envelopes', 'zip_to_xml_esri')
    def zip_to_xml_esri(self, base_name, shx_file, shp_file, dbf_file, xml_file, prj_file):
        """ """
        try:
            from Products.Reportek_dependencies.GML.shp_to_gml import shp_to_gml
            #generate GML convertion
            gml_filename = '%s.gml' % base_name
            gml_file_obj = getattr(self, gml_filename, None)

            if gml_file_obj == None:
                self.EnvelopeCreateEmptyGMLFile(gml_filename, self.generateGmlFileTitle(gml_filename), self)
                gml_file_obj = getattr(self, gml_filename, None)

            if gml_file_obj.get_accept_time():
                l_msg = 'Document cannot be changed since it has already accepted by the client'
            else:
                l_filename_tmp = '%s.shp' % base_name
                if len(prj_file) == 0:
                    return 'PRJ file is empty!'

                #temporary generate ESRI data/files
                RepUtils.createTempFile(shp_file, '%s.shp' % base_name)
                RepUtils.createTempFile(shx_file, '%s.shx' % base_name)
                RepUtils.createTempFile(dbf_file, '%s.dbf' % base_name)
                RepUtils.createTempFile(prj_file, '%s.prj' % base_name)
                RepUtils.createTempFile(xml_file, '%s.xml' % base_name)

                gml_data = shp_to_gml(filename=l_filename_tmp, in_schema=str(gml_file_obj.xml_schema_location),
                                    temp_name=gml_file_obj.id[:gml_file_obj.id.rfind('.')])

                #upload GML data on the GML file
                gml_file_obj.manage_file_upload(gml_data, 'text/xml')

                #delete temp files
                for k in ESRI_EXTENSIONS:
                    RepUtils.deleteTempFile('%s.%s' % (base_name, k))

                l_msg = 'done'
        except Exception, e:
            l_msg = 'Error during conversion! %s' % str(e)
        return l_msg

    security.declareProtected('Change Envelopes', 'addXmlFile')
    addXmlFile = DTMLFile('dataflows/Art17/envelopeAddXmlFile',globals())

    security.declareProtected('Change Envelopes', 'test_filename_species')
    def test_filename_species(self, filename):
        """ """
        if len(filename) < 17:
            return False
        spec_name = filename[8:-4]
        if filename[:8] == 'species-' and filename[-4:] == '.xml' and not ' ' in spec_name:
            l_list = spec_name.split('-')
            if len(l_list) >= 2:
                for k in l_list:
                    if not len(k) > 0:
                        return False
            else:
                return False
        else:
            return False
        return True

    security.declareProtected('Change Envelopes', 'process_xml_file')
    def process_xml_file(self, file_name, file_content, overwrite):
        """ """
        msg = []
        msg_add = msg.append
        habitat_info = self.getHabitatInfo()

        file_exist = self.testExistingFile(file_name)

        if not len(file_name) > 0:
            msg_add('you must specify a file')
            return msg

        if file_exist and not overwrite:
            msg_add('file already exists')
            return msg

        if self.test_filename_species(file_name):
            # Species factsheet
            file_title = file_name[8:-4].replace('-', ' ').capitalize()
        elif file_name[:12] == 'habitattype-' and file_name[-4:] == '.xml' and file_name[12:-4] in habitat_info.keys():
            # Habitat factsheet
            file_title = habitat_info[file_name[12:-4]]
        elif file_name == 'general-report.xml':
            # General report
            file_title = 'General report for art 17'
        else:
            msg_add("the '%s' is not a valid filename" % file_name)
            return msg

        #add/update XML content
        if file_exist:
            xml_ob = getattr(self, file_name)
            if xml_ob.get_accept_time():
                msg_add('Document cannot be changed since it has already accepted by the client')
                return msg
            xml_ob.manage_file_upload(file_content, '')
            msg_add("'%s' updated." % file_title)
        else:
            self.manage_addDocument(file_name, file_title, file_content, '','')
            msg_add("'%s' added." % file_title)

        msg_add('done')
        return msg

    security.declareProtected('Change Envelopes', 'add_xml_file')
    def add_xml_file(self, file, overwrite='', REQUEST=None):
        """ """
        file_name = RepUtils.getFilename(file.filename)
        file_content = file.read()
        msg = self.process_xml_file(file_name, file_content, overwrite)

        REQUEST.SESSION.set('msg', msg)
        REQUEST.RESPONSE.redirect('%s/addXmlFile' % self.absolute_url())

    security.declareProtected('Change Envelopes', 'addOtherFile')
    addOtherFile = DTMLFile('dataflows/Art17/envelopeAddOtherFile',globals())

    security.declareProtected('Change Envelopes', 'process_other_file')
    def process_other_file(self, id='', title='', file='', restricted=''):
        """ """
        msg = []
        msg_add = msg.append
        try:
            tmp_msg = self.manage_addDocument(id, title, file, '', restricted)
        except Exception, e:
            msg_add('%s' % e)
            return msg
        if tmp_msg:
            msg_add("The '%s' was successfully created!" % tmp_msg)
            msg_add('done')
        else:
            msg_add('you must specify a file')
        return msg

    security.declareProtected('Change Envelopes', 'add_other_file')
    def add_other_file(self, id='', title='', file='', restricted='', REQUEST=None):
        """ """
        msg = self.process_other_file(id, title, file, restricted)
        REQUEST.SESSION.set('msg', msg)
        REQUEST.RESPONSE.redirect('%s/addOtherFile' % self.absolute_url())

    security.declareProtected('Use OpenFlow', 'completeTask')
    completeTask = DTMLFile('dataflows/Art17/envelopeCompleteTask',globals())

    security.declareProtected('Use OpenFlow', 'complete_task')
    def complete_task(self, workitem_id, REQUEST=None):
        """ """
        p_action = REQUEST.get('action', '')
        if p_action == 'Complete task':
            self.completeWorkitem(workitem_id)
        REQUEST.RESPONSE.redirect(self.absolute_url())

    ##################################################
    #   Conversions - SHP to GML related
    ##################################################
    security.declareProtected('Change Envelopes', 'convert_esri_to_xml')
    def convert_esri_to_xml(self, file_id, shx_file, shp_file, dbf_file, xml_file, prj_file):
        """ """
        shp_filename = RepUtils.getFilename(shp_file.filename)
        dbf_filename = RepUtils.getFilename(dbf_file.filename)
        shx_filename = RepUtils.getFilename(shx_file.filename)
        prj_filename = RepUtils.getFilename(prj_file.filename)
        if len(shp_filename) and len(dbf_filename) and len(shx_filename) and len(prj_filename):

            tmp_basename = shp_filename[:-3]
            xml_filename = '%sxml' % tmp_basename

            #pre-generation tests
            for k in SHORT_ESRI_EXTENSIONS:
                if eval('%s_filename' % k)[:-3] != tmp_basename:
                    return 'All files must have the same name and different extensions.'
            try:    prj_file_data = prj_file.read()
            except: prj_file_data = ''
            if len(prj_file_data) == 0:
                return 'PRJ file is empty!'

            from Products.Reportek_dependencies.GML.shp_to_gml import shp_to_gml
            try:
                #generate GML convertion
                l_filename_tmp = RepUtils.cookId(shp_file)
                l_filename = l_filename_tmp[:l_filename_tmp.rfind('.')]

                gml_file_obj = getattr(self, file_id, None)

                if gml_file_obj.get_accept_time():
                    return 'Document cannot be changed since it has already accepted by the client'

                #get uploaded ESRI data
                shp_file_data = shp_file.read()
                shx_file_data = shx_file.read()
                dbf_file_data = dbf_file.read()
                try:    xml_file_data = xml_file.read()
                except: xml_file_data = ''

                #temporary generate ESRI data/files
                RepUtils.createTempFile(shp_file_data, shp_filename)
                RepUtils.createTempFile(shx_file_data, shx_filename)
                RepUtils.createTempFile(dbf_file_data, dbf_filename)
                RepUtils.createTempFile(prj_file_data, prj_filename)
                RepUtils.createTempFile(xml_file_data, xml_filename)

                gml_data = shp_to_gml(filename=l_filename_tmp, in_schema=str(gml_file_obj.xml_schema_location),
                                    temp_name=gml_file_obj.id[:gml_file_obj.id.rfind('.')])

                #upload GML data on the GML file
                gml_file_obj.manage_file_upload(gml_data, 'text/xml')

                #upload/add ESRI files on envelope
                gml_filename = gml_file_obj.id[:-4]
                gml_file_title = gml_file_obj.title
                for k in ESRI_EXTENSIONS:
                    esri_file_id = '%s.%s' % (gml_filename, k)
                    esri_file_data = eval('%s_file_data' % k)
                    if self.testExistingFile(esri_file_id):
                        esri_file_obj = getattr(self, esri_file_id, None)
                        esri_file_obj.manage_file_upload(esri_file_data, '')
                    else:
                        self.manage_addDocument(esri_file_id, '%s file of the %s' % (k.upper(), gml_file_title),
                                        esri_file_data, '','')

                #delete temp files
                for k in ESRI_EXTENSIONS:
                    RepUtils.deleteTempFile('%s.%s' % (l_filename, k))

                l_msg = 'done'
            except Exception, e:
                l_msg = 'Error during conversion! %s' % str(e)
        else:
            l_msg = 'Missing mandatory files:'
            for k in SHORT_ESRI_EXTENSIONS:
                if not len(eval('%s_filename' % k)):
                    l_msg = '%s %s file,' % (l_msg, k.upper())
            l_msg = '%s.' % l_msg[:-1]
        return l_msg

    security.declareProtected('Change Envelopes', 'convert_ESRI2XML')
    def convert_ESRI2XML(self, file_id, shx_file, shp_file, dbf_file, meta_file, prj_file, REQUEST=None):
        """ """
        msg = self.convert_esri_to_xml(file_id, shx_file, shp_file, dbf_file, meta_file, prj_file)
        if msg == 'done':
            REQUEST.RESPONSE.redirect(self.absolute_url())
        else:
            REQUEST.RESPONSE.redirect('%s/uploadESRI?file=%s&msg=%s' % (self.absolute_url(), file_id, msg))

    security.declareProtected('Change Envelopes', 'uploadESRI')
    uploadESRI = DTMLFile('dtml/envelopeUploadESRI',globals())

    ##################################################
    #   Rivers
    ##################################################

    security.declareProtected('Change Envelopes', 'upload_rivers_excel_file')
    upload_rivers_excel_file = DTMLFile('dataflows/Rivers/documentAddExcelData',globals())

    security.declareProtected('Change Envelopes', 'upload_xml_file')
    upload_xml_file = DTMLFile('dataflows/Rivers/documentAddXMLData',globals())

    security.declareProtected('Change Envelopes', 'upload_data_file')
    upload_data_file = DTMLFile('dataflows/Rivers/documentAddOtherData',globals())

    ##################################################
    #   Groundwater
    ##################################################

    security.declareProtected('Change Envelopes', 'fetchXMLFileGW')
    def fetchXMLFileGW(self, REQUEST=None):
        """ Grabs one XML file from a fixed location and uploads it as Report Document
        """
        # Construct the name of the file based on patters and the country code
        # Countries are kept as URI like 'http://cdr.eionet.eu.int/rdf/countries#LY'
        l_file_id_gw = self.getCountryCode().upper() + '_bodies.xml'
        l_file_id_sw = self.getCountryCode().upper() + '_saltwaterintrusion.xml'
        l_file_gw, l_content_type = RepUtils.utGrabFromUrl(WEBQ_XML_REPOSITORY + l_file_id_gw)
        l_file_sw, l_content_type = RepUtils.utGrabFromUrl(WEBQ_XML_REPOSITORY + l_file_id_sw)
        if l_file_gw is None and l_file_sw is None and REQUEST is not None:
            return self.messageDialog(
                                message='There is no initial data available. Use the webforms to create and edit the delivery files.',
                                action=self.absolute_url())
        elif l_file_gw is None and l_file_sw is None:
            return 0

        if hasattr(self, l_file_id_gw):
            self.manage_delObjects(l_file_id_gw)
        if hasattr(self, l_file_id_sw):
            self.manage_delObjects(l_file_id_sw)
        if l_file_gw is not None:
            self.manage_addDocument(id=l_file_id_gw, file=l_file_gw, content_type=l_content_type)
        if l_file_sw is not None:
            self.manage_addDocument(id=l_file_id_sw, file=l_file_sw, content_type=l_content_type)

        if REQUEST is not None:
            return self.messageDialog(
                            message='File(s) successfully fetched!',
                            action=self.absolute_url())
        return 1

    security.declareProtected('Change Envelopes', 'uploadGISfiles')
    def uploadGISfiles(self, file_shp=None, file_shx=None, file_prj=None, file_dbf=None, file_metainfo=None, REQUEST=None):
        """ """
        if file_shp.filename.find('.shp') != -1 and \
                file_shx.filename.find('.shx') != -1 and \
                file_prj.filename.find('.prj') != -1 and \
                file_dbf.filename.find('.dbf') != -1 and \
                file_metainfo.filename.find('.xml') != -1:
            self.manage_addDocument(file=file_shp)
            self.manage_addDocument(file=file_shx)
            self.manage_addDocument(file=file_prj)
            self.manage_addDocument(file=file_dbf)
            self.manage_addDocument(file=file_metainfo)
            if REQUEST is not None:
                return self.messageDialog(
                                message="Files successfully uploaded!",
                                action='.')
            else:
                return 1
        elif file_shp.filename and file_shx.filename and file_prj.filename and \
                file_dbf.filename and file_metainfo.filename:
            if REQUEST is not None:
                return self.messageDialog(
                                message="Files not uploaded! In order for the GIS delivery to be correct and complete, a 'shp', a 'shx', a 'prj', a 'dbf' and an XML file should be present!",
                                action='.')
        else:
            if REQUEST is not None:
                return self.messageDialog(
                                message="Files not uploaded! All fields are mandatory! You must specify all files indicated in order for the GIS delivery to be correct and complete!",
                                action='.')
        return 0

    security.declareProtected('Change Envelopes', 'uploadGISZIPfiles')
    def uploadGISZIPfiles(self, file_gis_zip=None, REQUEST=None):
        """ """
        if file_gis_zip.filename:
            # According to the zipfile.py ZipFile just needs a file-like object
            try:
                zf = ZZipFile(file_gis_zip)
            except:
                if REQUEST is not None:
                    return self.messageDialog(
                                    message="Files not uploaded! The file you have specified is not a zip file!",
                                    action='.')
                else:
                    return 0

            l_file_list = zf.namelist()
            l_mess = ''
            l_extensions = ESRI_EXTRAEXTENSIONS
            for name in l_file_list:
                # test that the archive is not hierarhical
                if name[-1] == '/' or name[-1] == '\\':
                    l_mess = "Files not uploaded! The zip file you specified is hierarchical. It contains folders.\nPlease upload a non-hierarchical structure of files."
                if len(name) > 4:
                    if name[-4:].lower() in l_extensions:
                        l_extensions.remove(name[-4:].lower())
            if l_mess:
                if REQUEST is not None:
                    return self.messageDialog(
                                    message=l_mess,
                                    action='./index_html')
                else:
                    return 0
            # test if all types of files have been added in the archive
            elif len(l_extensions) > 0:
                if REQUEST is not None:
                    return self.messageDialog(
                                    message="Files not uploaded! Not all the files were present in the archive.\nIn order for the GIS delivery to be correct and complete, a 'shp', a 'shx', a 'prj', a 'dbf' and an XML file should be present!",
                                    action='./index_html')
                else:
                    return 0

            for name in zf.namelist():
                zf.setcurrentfile(name)
                self._add_file_from_zip(zf,name, '')

            if REQUEST is not None:
                return self.messageDialog(
                                message="Files successfully uploaded!",
                                action='.')
            else:
                return 1
        else:
            if REQUEST is not None:
                return self.messageDialog(
                                message="You must specify a zip file containing your GIS delivery!",
                                action='.')
            else:
                return 0

    ##################################################
    #   Air Quality Questionnaire
    ##################################################

    def getShapeFiles(self):
        """ Returns all the shape file names from the envelope """
        self.REQUEST.RESPONSE.setHeader('content-type', 'text/xml; charset=utf-8')
        xml = []
        xml_a = xml.append
        xml_a('<?xml version="1.0" encoding="utf-8"?>')
        xml_a("<files>")
        for doc in self.objectValues('Report Document'):
            if doc.id.endswith('.shp'):
                xml_a('<file id="' + doc.id + '" url="' + doc.absolute_url() + '" />')
        xml_a("</files>")
        return ''.join(xml)

    def createRegionInstances(self, x="3", y="28", form_name="form2.xml", language="en"):
        """ Creates XMLs for each region defined in form2.xml e.g. form3_region1.xml"""
        x, y = int(x), int(y)
        #read region names from form2.xml
        regions = []
        dom = self.getFormContentAsXML(form_name)
        rows = dom.getElementsByTagName("form2-row")
        for row in rows:
            region_name = self.getXMLNodeData(row, "region-name")
            if region_name not in regions: regions.append(region_name)

        #for each of the forms from 3 to 27, generate a region specific xml
        region_template = "<reporting-regions>\n\t<region>%s</region>\n</reporting-regions>"
        aqq_empty_instances = self.restrictedTraverse("/", None)["emptyinstances"]["aqq"]
        for xml_number in range(x, y):
            for region in regions:
                xml_filename = "form%s_%s.xml" % (xml_number, region)
                xml_filecontent = aqq_empty_instances["form%s" % xml_number](language)
                xml_filecontent = xml_filecontent.replace("$$$REGION_DATA$$$", region_template % region)
                self.manage_addDocument(xml_filename, "", xml_filecontent, "text/xml", "")

    def getZonesForRegion(self, form_name=None, aqq_rule=None):
      """
      Return the zones available for the specified region and form
      @param form_name This is the name of the instance being edited by the XForm engine (form25...xml etc.).
      Method will retrieve from inside the name of the region within tag <region> and depending on form_name
      will furthermore filter the data according to the chemical compound being edited.
      @param aqq rule to further filter the zones, see b) from ticket. These are hard-coded conventions, for example 'form8b' refers to form 8, second tab
      If no rule is specified, defaults to True, including the zone within the result
      @see https://svn.eionet.europa.eu/projects/Reportnet/ticket/1759
      """
      self.REQUEST.RESPONSE.setHeader('content-type', 'text/xml; charset=utf-8')
      ret = []
      ret.append('<?xml version="1.0" encoding="utf-8"?>')
      ret.append('<response>')
      try:
        form_name = form_name.split('/')[-1]
        #Open the file from request (located in currently editing envelope) and retrieve from it the zones we need to find zones for
        dom = self.getFormContentAsXML(form_name)
        node_rr = dom.getElementsByTagName('reporting-regions')
        req_region_names = []
        if node_rr:
          node = node_rr[0]
          regions = node.getElementsByTagName('region')
          for region in regions:
            req_region_names.append(region.childNodes[0].data)

        #a) Read the form2.xml and extract all necessary codes
        dom = self.getFormContentAsXML('form2.xml')
        zones = dom.getElementsByTagName('form2-row')
        for zone in zones:
          region_name = self.getXMLNodeData(zone, 'region-name')
          if region_name in req_region_names:
            #b) Apply the second type of rule, filter zone by its checked compounds (in form 2)
            if self.matchAQQCompoundRules(zone, aqq_rule):
              ret.append('<zone>')
              ret.append('<name>%s</name>' % self.getXMLNodeData(zone, 'full-zone-name'))
              ret.append('<code>%s</code>' % self.getXMLNodeData(zone, 'zone-code'))
              ret.append('</zone>')
      except:
        traceback.print_exc()
        print 'Error parsing files from envelope: form2.xml or %s' % form_name
      ret.append('</response>')
      return ''.join(ret)


    def matchAQQCompoundRules(self, dom_zone, aqq_rule):
      #Match the AQQ rules see b) from  https://svn.eionet.europa.eu/projects/Reportnet/ticket/1759
      #@param dom_zone minidom xml fragment for a single <form2-row> tag
      #@param form_name Rules are matched based on form_name
      #Rule no. 1 - In form 19 return only the zones having 'O' checked in form 2
      if aqq_rule and aqq_rule.startswith('form19'):
        data = self.getXMLNodeData(dom_zone, 'o')

        return data == 'true'

      #TODO: Other rules
      return True

    def getXMLNodeData(self, domEl, nodeName):
    #Retrieve the data for a node/subnode etc. Works for single nodes only.
        ret = None
        if domEl:
          ret = domEl.getElementsByTagName(nodeName)[0].childNodes[0].data
        return ret

    def getFormContentAsXML(self, form_name):
    #Load an XML from 'report document'/disk into minidom for parsing
      ret = None
      for doc in self.objectValues('Report Document'):
            if doc.id == form_name:
                f = open(doc.physicalpath(), 'r')
                ret = f.read()
                f.close()
                break
      return parseString(ret)

# Initialize the class in order the security assertions be taken into account
InitializeClass(EnvelopeCustomDataflows)
