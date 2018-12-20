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
from Globals import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from zope.contenttype import guess_content_type
from AccessControl import ClassSecurityInfo
import re
import xmlrpclib
import string
import logging
import tempfile
import transaction
from xml.dom.minidom import parseString
from collections import defaultdict

# Product specific imports
import RepUtils
from constants import CONVERTERS_ID
from zip_content import ZZipFile
from XMLInfoParser import detect_single_schema, SchemaError
from Toolz import Toolz
import json
import zip_content

# from zipfile import *

conversion_log = logging.getLogger(__name__ + '.conversion')

ESRI_EXTENSIONS = ['shp', 'shx', 'dbf', 'prj', 'xml']
SHORT_ESRI_EXTENSIONS = ['shp', 'shx', 'dbf', 'prj']
EXTENDED_ESRI_EXTENSIONS = ['shp', 'shx', 'dbf', 'prj', 'xml', 'shp.xml']
OPTIONAL_ESRI_EXTENSIONS = ['xml', 'shp.xml']
ESRI_EXTRAEXTENSIONS = ['.shp', '.shx', '.dbf', '.prj', '.xml']


def invoke_conversion_service(server_name, method_name, url):
    server = xmlrpclib.ServerProxy(server_name)
    method = getattr(server.ConversionService, method_name)
    if method_name == 'convertDD_XML_split':
        return method(url, '')
    return method(url)


class EnvelopeCustomDataflows(Toolz):
    """ This class which Envelope subclasses from contains functions specific to one or more dataflows.
    """

    fileTypeByName_pattern = re.compile(r'\.(xml|xlf|xslt?|xsd|gml)$', flags=re.I)
    security = ClassSecurityInfo()

    ##################################################
    #   Generic methods for all dataflows
    ##################################################

    # generic method that converts Excel files (XLS or ODS) to XML
    # if the Excel template comes from Data Dictionary
    security.declareProtected('Change Envelopes', 'upload_excel_file')
    upload_excel_file = PageTemplateFile('zpt/envelope/upload_excel_file', globals())

    # generic method that converts Excel files (XLS or ODS) to XML
    security.declareProtected('Change Envelopes', 'upload_generic_excel_file')
    upload_generic_excel_file = PageTemplateFile('zpt/envelope/upload_generic_excel_file', globals())

    # generic method that uploads a DD file or accompanying data
    security.declareProtected('Change Envelopes', 'upload_dd_file')
    upload_dd_file = PageTemplateFile('zpt/envelope/upload_dd_file', globals())

    # generic method that uploads a single file or a zip
    security.declareProtected('Change Envelopes', 'upload_doc_or_zip')
    upload_doc_or_zip = PageTemplateFile('zpt/envelope/upload_doc_or_zip', globals())

    # generic method that uploads a MMR file or accompanying data
    security.declareProtected('Change Envelopes', 'upload_mmr_file')
    upload_mmr_file = PageTemplateFile('zpt/envelope/upload_mmr_file', globals())

    def _get_xml_files_by_schema(self, schema):
        """ Returns the list of XML files with the given schema from that envelope """
        return [doc.id for doc in self.objectValues('Report Document') if doc.xml_schema_location == schema]

    security.declareProtected('Change Envelopes', 'log_file_conversion')

    def log_file_conversion(self, filename, result):
        """ Logs the file conversion result on the workitem """
        if hasattr(self, 'REQUEST'):
            for l_w in self.getWorkitemsActiveForMe(self.REQUEST):
                l_w.addEvent('file conversion', 'File: {0} ; ({1})'
                             .format(
                    filename,
                    result
                )
                             )

    security.declareProtected('Change Envelopes', 'get_conv_results')

    def get_conv_results(self):
        """ Retrieve conversion results from workitems """
        conv_results = {}
        if hasattr(self, 'REQUEST'):
            wks = self.getListOfWorkitems()
            for wk in wks:
                wk_fc_log = {}
                for ev_log in wk.event_log:
                    if ev_log.get('event') == 'file conversion':
                        fc_log = {}
                        active = False
                        file_info, result = ev_log.get('comment').split(' ; ')
                        filename = file_info.split('File:')[-1].strip()
                        if filename in self.objectIds():
                            active = True
                        fc_log['active'] = active
                        fc_log['status'] = result.split(']:')[0].lstrip('([')
                        msg = result.split(']:')[-1].strip(' )')
                        fc_log['code'] = ''
                        fc_log['message'] = msg
                        if len(msg.split('Code: ')) > 1:
                            fc_log['code'] = msg.split('Code: ')[-1].rstrip(')')
                        wk_fc_log[filename] = fc_log
                conv_results[wk.getId()] = wk_fc_log
        return conv_results

    def get_failed_active_conversions(self):
        """ Returns failed active conversions. Active means the file has not
            been deleted
        """
        failed = []
        conv_results = self.get_conv_results()
        has_conversions = [conv for conv in conv_results
                           if conv_results.get(conv)]

        for wk_log in has_conversions:
            files = conv_results.get(wk_log)
            for filename, c_info in files.iteritems():
                if c_info.get('active') and c_info.get('status') != 'INFO':
                    failed.append(filename)

        return failed

    security.declareProtected('Change Envelopes', 'convert_excel_file')

    def convert_excel_file(self, file, restricted='', strict_check=0, conversion_function='', REQUEST=None):
        """ Uploads the original spreadsheet to the envelope,
            deleting the file with the same id, if exists.
            Attempts the conversion of the DD-based spreadsheet
            If successful, deletes all XML files in the envelope previously generated by that file
            Adds the converted XML files to the envelope
            Returns the error message on REQUEST and the result code if no REQUEST is given:

            -   1 if the conversion succeeded, with or without validation errors
            -   0 if the conversion did not succeed and the original file was uploaded
            -   -1 if no upload has been done

        """
        if not file or type(file) is type('') or not hasattr(file, 'filename'):
            if REQUEST is not None:
                return self.messageDialog(
                    message='Upload failed! No file was specified!',
                    action='index_html')
            else:
                return -1
        l_original_content = file.read()
        # build original file id
        l_id = self.cook_file_id(file.filename)

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
        # XML/RPC call to the converter
        l_server_name = getattr(self, CONVERTERS_ID).remote_converter
        l_url = self.absolute_url() + '/' + l_id
        # default xls conversion xmlrpc method
        method_name = 'convertDD_XML_split'
        dfm = self.getDataflowMappingsContainer()
        if dfm:
            xls_conversion = dfm.get_xls_conversion_type(self.dataflow_uris)
            method_name = {'split': 'convertDD_XML_split',
                           'nosplit': 'convertDD_XML'}.get(xls_conversion,
                                                           'convertDD_XML_split')
        try:
            l_ret_list = invoke_conversion_service(l_server_name, method_name, l_url)
        except Exception as e:
            if REQUEST is not None:
                conversion_log.error(
                    "Error while calling remote {} for xmlrpc method {}. ({})".format(
                        l_server_name, method_name, str(e)))
                self.log_file_conversion(l_id, '[ERROR]: Conversion failed due to a system error.')
                return self.messageDialog(
                    message=('The file was successfully uploaded in the '
                             'envelope, but not converted into an '
                             'XML delivery because of a system error: %s') % str(e),
                    action='index_html')
            else:
                return 0

        try:

            # the result is a dictionary with the following elements:
            #   resultCode (String): 0 – success; 1- converted with validation errors; 2- system error; 3 – schema not found or expired error
            #   resultDescription (String): short textual description about conversion results. If resultCode > 0, then resultDescription contains error message
            #   conversionLog (String): conversion log in HTML format. The result is HTML fragment wrapped into <div class="feedback"> element.
            #   convertedFiles (Array<Struct>): list of dictionaries of converted files
            #       fileName (String): Name of the result file
            #       content (Byte[]): XML content of result document as a UTF-8 encoded byte array

            # delete the XML files that may be previously generated by conversion of the same file
            self.manage_delObjects([x.id for x in self.objectValues('Report Document') if
                                    x.content_type == 'text/xml' and x.id.startswith(l_id[:-4] + '_')])
            # delete the feedback that may be previously generated by conversion of the same file
            if hasattr(self, 'conversion_log_%s' % l_id):
                self.manage_delObjects('conversion_log_%s' % l_id)

            l_result = l_ret_list['resultCode']
            if l_result in ['0', '1']:
                # add XML files
                l_converted_files = l_ret_list['convertedFiles']
                for l_xml in l_converted_files:
                    if method_name == 'convertDD_XML_split':
                        l_xml_id = l_id[:-4] + '_' + l_xml['fileName']
                    else:
                        l_xml_id = l_xml['fileName']
                    self.manage_addDocument(id=l_xml_id, title='Converted from - %s' % l_id, file=l_xml['content'].data,
                                            content_type='text/xml', restricted=restricted)
                # Change the original file title to show the conversion result
                l_doc.manage_editDocument(title='%s - converted into an XML delivery' % l_original_type,
                                          content_type=l_doc.content_type)
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
                        c_log = '[ERROR]: File contains no data (Code: {})'.format(l_result)
                    elif l_result == '1':
                        l_msg = 'The file was successfully uploaded in the envelope and converted into an XML delivery. The conversion contains validation warnings - see the Feedback posted for this file for details.'
                        c_log = '[WARNING]: Conversion contains validation warnings (Code: {})'.format(l_result)
                    else:
                        l_msg = 'The file was successfully uploaded in the envelope and converted into an XML delivery.'
                        c_log = '[INFO]: Conversion successful'.format(l_result)
                    self.log_file_conversion(l_id, c_log)
                    return self.messageDialog(
                        message=l_msg,
                        action='index_html')
                else:
                    return 1
            elif l_result == '2':
                # Change the original file title to show the conversion result
                l_doc.manage_editDocument(title='%s - not converted into an XML delivery' % l_original_type,
                                          content_type=l_doc.content_type)
                # add feedback with the conversion log
                self.manage_addFeedback(id='conversion_log_%s' % l_id,
                                        title='Conversion log for file %s' % l_id,
                                        feedbacktext=l_ret_list['conversionLog'],
                                        automatic=1,
                                        content_type='text/html',
                                        document_id=l_id)

                if REQUEST is not None:
                    conversion_log.error(
                        l_ret_list.get('resultDescription',
                                       'Error in converting file at %s' % l_doc.absolute_url())
                    )
                    self.log_file_conversion(l_id,
                                             '[ERROR]: Conversion failed due to a system error. (Code: {})'.format(
                                                 l_result))
                    return self.messageDialog(
                        message='The file was successfully uploaded in the envelope, but not converted into an XML delivery. See the Feedback posted for this file for details.',
                        action='index_html')
                else:
                    return 0

            elif l_result == '3':
                # Change the original file title to show the conversion result
                l_doc.manage_editDocument(
                    title='%s - not converted into an XML delivery - not based on the most recent reporting template' % l_original_type,
                    content_type=l_doc.content_type)
                # add feedback with the conversion log
                self.manage_addFeedback(id='conversion_log_%s' % l_id,
                                        title='Conversion log for file %s' % l_id,
                                        feedbacktext=l_ret_list['conversionLog'],
                                        automatic=1,
                                        content_type='text/html',
                                        document_id=l_id)
                if REQUEST is not None:
                    self.log_file_conversion(l_id,
                                             '[ERROR]: Conversion failed due missing or expired reporting schema. (Code: {})'.format(
                                                 l_result))
                    return self.messageDialog(
                        message='The file was successfully uploaded in the envelope, but not converted into an XML delivery, because you are not using the most recent reporting template - %s. See the feedback posted for this file for details.' %
                                l_ret_list['resultDescription'],
                        action='index_html')
                else:
                    return 0
            else:
                if REQUEST is not None:
                    self.log_file_conversion(l_id,
                                             '[ERROR]: Conversion failed due to a system error. (Code: {})'.format(
                                                 l_result))
                    return self.messageDialog(
                        message='Incorrect result from the Conversion service. The file was successfully uploaded in the envelope, but not converted into an XML delivery.',
                        action='index_html')
                else:
                    return 0

        except Exception, err:
            # Change the original file title to show the error in conversion
            l_doc.manage_editDocument(title='%s, could not be converted into an XML delivery' % l_original_type,
                                      content_type=l_doc.content_type)
            if REQUEST is not None:
                conversion_log.error(
                    l_ret_list.get('resultDescription',
                                   'Error in converting file at %s' % l_doc.absolute_url())
                )
                self.log_file_conversion(l_id, '[ERROR]: Conversion failed due to a system error.')
                return self.messageDialog(
                    message='The file was successfully uploaded in the envelope, but not converted into an XML delivery because of a system error: %s' % str(
                        err),
                    action='index_html')
            else:
                return 0

    security.declareProtected('Change Envelopes', 'replace_dd_xml')

    def replace_dd_xml(self, file, filename=None, check_schema=True, restricted='', required_schema=[], replace_xml=1, REQUEST=None):
        """ Cheks if the schema id of the file is either empty or is in the 'required_schema' list.
            If yes, it adds the new file; if there are XML files in the envelope with the same schema, those are deleted first.
            If no, it doesn't upload the file and complains.

            Returns the error message on REQUEST and the result code if no REQUEST is given:
                1 if the file is XML and of the right schema
                0 if the file is either not XML or with the right schema
                -1 if there was no file
        """
        if not file or type(file) is type('') or (not hasattr(file, 'filename') and not filename):
            if REQUEST is not None:
                return self.messageDialog(
                    message='Upload failed! No file was specified!',
                    action='index_html')
            else:
                return -1
        # guess content type
        first_1k = file.read(1024)
        file.seek(0)
        if not filename:
            filename = file.filename
        content_type, enc = guess_content_type(filename, first_1k)
        schema = None
        if content_type == 'text/xml':
            # don't attempt to extract schema for shapefiles that have their
            # own metadata in a schema-less xml
            if filename.endswith('.shp.xml'):
                check_schema = False
            if check_schema:
                try:
                    # verify the XML schema
                    schema = detect_single_schema(file)
                except SchemaError as e:
                    if REQUEST:
                        return self.messageDialog(
                            message="The file you are trying to upload does not have valid schema location."
                                    " File not uploaded! Reason: %s" % str(e.args),
                            action='index_html')
            file.seek(0)
            # if no list of schemas were specified, or if the current XML schema is part of the given list
            if not required_schema or schema in RepUtils.utConvertToList(required_schema) or not check_schema:
                cookid = self.cook_file_id(filename)
                if int(replace_xml) == 1 and check_schema:
                    # delete all the XML files from this envelope which contain this schema
                    xmls = self._get_xml_files_by_schema(schema)
                    self.manage_delObjects(xmls)
                else:
                    # just delete the document with the same id, if exists
                    if hasattr(self, cookid):
                        self.manage_delObjects(cookid)

                # finally, add a Report Document
                return self.manage_addDocument(id=cookid, title='Data file',
                                               file=file, filename=filename,
                                               content_type=content_type,
                                               restricted=restricted,
                                               REQUEST=REQUEST)
            else:
                if REQUEST is not None:
                    return self.messageDialog(
                        message="The file you are trying to upload wasn't generated "
                                " according to the correct schema!"
                                " File not uploaded!",
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

    def manage_addDocOrZip(self, file, restricted='', id='', required_schema=[],
                           replace_xml=0, disallow='', REQUEST=None):
        """ Adds a file or unpacks a zip in the envelope
             If the file is XML, it calls replace_dd_xml,
             otherwise, it just uploads the file using manage_addDocument
         """
        if not file or type(file) is type('') or not hasattr(file, 'filename'):
            if REQUEST is not None:
                return self.messageDialog(
                    message='No file was specified!',
                    action='index_html')
            return 0
        else:
            if file.filename.endswith('.zip'):
                return self.manage_addDDzipfile(
                    file=file,
                    restricted=restricted,
                    required_schema=required_schema,
                    replace_xml=int(replace_xml),
                    disallow=disallow,
                    REQUEST=REQUEST)
            elif re.search(self.fileTypeByName_pattern, file.filename):
                return self.replace_dd_xml(
                    file=file,
                    restricted=restricted,
                    required_schema=required_schema,
                    replace_xml=int(replace_xml),
                    REQUEST=REQUEST)
            else:
                return self.manage_addDocument(
                    id=id,
                    file=file,
                    restricted=restricted,
                    disallow=disallow,
                    REQUEST=REQUEST)

    security.declareProtected('Change Envelopes', 'manage_addDDFile')

    def manage_addDDFile(self, file, restricted='', required_schema=[], replace_xml=1, REQUEST=None):
        """ Adds a file created using a DD template as follows:
            - if the file is a spreadsheet, it calls convert_excel_file
            - if the file XML, it calls replace_dd_xml
            - if the file zip, it calls manage_addDDzipfile
            - otherwise it calls manage_addDocument
        """
        if not file or type(file) is type('') or not hasattr(file, 'filename'):
            if REQUEST is not None:
                return self.messageDialog(
                    message='No file was specified!',
                    action='index_html')
            return 0
        else:
            l_filename = file.filename.lower()
            if l_filename.endswith('.xls') or l_filename.endswith('.xlsx') or l_filename.endswith('.ods'):
                return self.convert_excel_file(file=file, restricted=restricted, REQUEST=REQUEST)
            elif re.search(self.fileTypeByName_pattern, l_filename):
                return self.replace_dd_xml(file=file, restricted=restricted, required_schema=required_schema,
                                           replace_xml=int(replace_xml), REQUEST=REQUEST)
            elif l_filename.endswith('.zip'):
                return self.manage_addDDzipfile(file=file, restricted=restricted, required_schema=required_schema,
                                                replace_xml=int(replace_xml), REQUEST=REQUEST)
            else:
                return self.manage_addDocument(file=file, restricted=restricted, REQUEST=REQUEST)

    security.declareProtected('Add Envelopes', 'manage_addDDzipfile')
    def manage_addDDzipfile(self, file='', content_type='', restricted='',
                            required_schema=[], replace_xml=0, disallow='',
                            REQUEST=None):
        """ Expands a zipfile into a number of Documents.
            For the XML files, checks if the schema is correct for that dataflow, meaning the schema is part of the
            'required_schema' list of approved schemas. It uploads all files, then deletes the files that should have
            not been uploaded because of the wrong schema.

            Returns:
                - 0 if there was no file or the zip file was hierarchical
                - 1 if all files were uploaded successfully
                - 2 if one or more files were not uploaded from the archive

            If you need a function that uploads all files as they are,
            without any schema cheks, use manage_addzipfile
        """
        if type(file) is not type('') and hasattr(file, 'filename'):
            replace_xml = int(replace_xml)
            # make a list of all XML files in the envelope and their schemas, they may need to be deleted afterwards
            # if the zip file contains XML files with the same schema and the flag 'replace_xml' is 1
            xml_f = {}
            l = [(x.xml_schema_location, x.id) for x in self.objectValues('Report Document') if x.xml_schema_location]
            for i, j in l:
                if xml_f.has_key(i):
                    xml_f[i].append(j)
                else:
                    xml_f[i] = [j]

            # According to the zipfile.py ZipFile just needs a file-like object
            zf = zip_content.ZZipFileRaw(file)
            zip_file_ids = zf.namelist()
            file_ids_not_uploaded = []
            file_ids_to_delete = []

            for name in zip_file_ids:
                # test that the archive is not hierarhical
                if name[-1] == '/' or name[-1] == '\\':
                    if REQUEST is not None:
                        return self.messageDialog(
                            message='The zip file you specified is hierarchical. It contains folders.\n'
                                    'Please upload a non-hierarchical structure of files.',
                            action='./index_html')
                    else:
                        return 0

            for name in zip_file_ids:
                id = self.cook_file_id(name)
                zf.setcurrentfile(name)
                zipped_file_id = self.manage_addDocument(id=id, title=id, file=zf, restricted=restricted, disallow=disallow)
                transaction.commit()
                if not zipped_file_id:
                    # something happened with the file upload and the upload didn't go through
                    file_ids_not_uploaded.append(id)
                    continue
                zipped_file = getattr(self, zipped_file_id)
                schemaless_shp_meta = name.endswith('.shp.xml')
                 # for XML files, check if the schema is in the list of accepted schemas for that dataflow
                # and if the other files in the envlope with this schema should be replaced
                if re.search(self.fileTypeByName_pattern, id):
                    if not schemaless_shp_meta and (required_schema and not zipped_file.xml_schema_location in \
                            RepUtils.utConvertLinesToList(required_schema)):
                        # delete this XML file, it has the wrong schema for this dataflow
                        self.manage_delObjects(zipped_file_id)
                        #print name, zipped_file_id
                        file_ids_not_uploaded.append(zipped_file_id)
                        transaction.commit()

                    if replace_xml and zipped_file.xml_schema_location in xml_f.keys():
                        # delete all the XML files from this envelope which have this schema
                        for f in xml_f[zipped_file.xml_schema_location]:
                            file_ids_to_delete.append(f)

            # if 'replace_xml', delete all XML files with the same schemas as files just uploaded
            file_ids_to_delete = list(set(file_ids_to_delete))
            #print file_ids_to_delete
            self.manage_delObjects([x for x in file_ids_to_delete if x not in zip_file_ids])
            if file_ids_not_uploaded:
                if len(file_ids_not_uploaded) == len(zip_file_ids):
                    msg = 'No files were added in the envelope, because their schemas are not correct for this dataflow or file types are not allowed in this context!'
                else:
                    msg = 'Some files from the zip file were not uploaded in the envelope ' \
                          'because their schemas are not correct for this dataflow or certain file types are not allowed in this context!'
            else:
                msg = 'The file(s) in this zip archive were successfully uploaded in the envelope'

            if REQUEST is not None:
                return self.messageDialog(message=msg, action='./manage_main')
            elif file_ids_not_uploaded:
                return 2
            else:
                return 1

        elif REQUEST is not None:
            return self.messageDialog(message="You must specify a file!", action='./manage_main')
        else:
            return 0

    security.declareProtected('View', 'subscribe_all_actors')
    def subscribe_all_actors(self, event_type=''):
        """ Calls UNS for all actors it has found in the work items in the envelope
            and subscribes them to receive notifications to a specified event if the parameter is provided
        """
        engine = self.ReportekEngine
        if engine.UNS_server:
            actors = []
            for w in self.objectValues('Workitem'):
                if w.actor != 'openflow_engine' and w.actor not in actors:
                    actors.append(w.actor)
            filters = []
            country_name = str(engine.localities_dict().get(self.country, {'name': 'Unknown'})['name'])
            for df in self.dataflow_uris:
                if event_type:
                    filters.append({'http://rod.eionet.europa.eu/schema.rdf#locality': country_name,
                                    'http://rod.eionet.europa.eu/schema.rdf#obligation': engine.getDataflowTitle(df),
                                    'http://rod.eionet.europa.eu/schema.rdf#event_type': event_type})
                else:
                    filters.append({'http://rod.eionet.europa.eu/schema.rdf#locality': country_name,
                                    'http://rod.eionet.europa.eu/schema.rdf#obligation': engine.getDataflowTitle(df)})

            engine.uns_subscribe_actors(actors, filters)

    security.declareProtected('Change Envelopes', 'uploadGISfiles')
    def uploadGISfiles(self, file_shp=None, file_shx=None, file_prj=None, file_dbf=None, file_metainfo=None,
                       REQUEST=None):
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
                self._add_file_from_zip(zf, name, '')

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
        # read region names from form2.xml
        regions = []
        dom = self.getFormContentAsXML(form_name)
        rows = dom.getElementsByTagName("form2-row")
        for row in rows:
            region_name = self.getXMLNodeData(row, "region-name")
            if region_name not in regions: regions.append(region_name)

        # for each of the forms from 3 to 27, generate a region specific xml
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
            # Open the file from request (located in currently editing envelope) and retrieve from it the zones we need to find zones for
            dom = self.getFormContentAsXML(form_name)
            node_rr = dom.getElementsByTagName('reporting-regions')
            req_region_names = []
            if node_rr:
                node = node_rr[0]
                regions = node.getElementsByTagName('region')
                for region in regions:
                    req_region_names.append(region.childNodes[0].data)

            # a) Read the form2.xml and extract all necessary codes
            dom = self.getFormContentAsXML('form2.xml')
            zones = dom.getElementsByTagName('form2-row')
            for zone in zones:
                region_name = self.getXMLNodeData(zone, 'region-name')
                if region_name in req_region_names:
                    # b) Apply the second type of rule, filter zone by its checked compounds (in form 2)
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
        # Match the AQQ rules see b) from  https://svn.eionet.europa.eu/projects/Reportnet/ticket/1759
        # @param dom_zone minidom xml fragment for a single <form2-row> tag
        # @param form_name Rules are matched based on form_name
        # Rule no. 1 - In form 19 return only the zones having 'O' checked in form 2
        if aqq_rule and aqq_rule.startswith('form19'):
            data = self.getXMLNodeData(dom_zone, 'o')

            return data == 'true'

        # TODO: Other rules
        return True

    def getXMLNodeData(self, domEl, nodeName):
        # Retrieve the data for a node/subnode etc. Works for single nodes only.
        ret = None
        if domEl:
            ret = domEl.getElementsByTagName(nodeName)[0].childNodes[0].data
        return ret

    def getFormContentAsXML(self, form_name):
        # Load an XML from 'report document'/disk into minidom for parsing
        ret = None
        for doc in self.objectValues('Report Document'):
            if doc.id == form_name:
                f = doc.data_file.open()
                ret = f.read()
                f.close()
                break
        return parseString(ret)

    def convert(self, xml_schema, req_xsl, file_url):
        """Call the conversion service for the file and return the converted file
        """
        converters = self.unrestrictedTraverse(CONVERTERS_ID)
        xsls = converters.get_remote_converters_for_schema(xml_schema)
        xsls_valid = [x for x in xsls if req_xsl == x['xsl']]
        xsls_ids = [x['convert_id'] for x in xsls_valid]

        if not xsls_ids:
            raise ValueError('Could not find a valid converter (%s) for schema: %s' % (req_xsl, xml_schema))

        file_url = '/{}'.format(file_url) if not file_url.startswith('/') else file_url
        return converters.run_remote_conversion(file_url=file_url,
                                                converter_id=xsls_ids[0],
                                                write_to_response=False)

    def sanitize_report_files(self, schema_convs, wk=None):
        """ Pass the envelope documents with the specified schemas conversions
         through a sanitization process through converters with the specified
         xsls. Expected schema_convs structure: {schema: ['xsl']}
        """
        def do_log(m_type, msg, wk=None):
            if wk:
                wk.addEvent(msg)
            else:
                log = getattr(conversion_log, m_type, None)
                if log:
                    log(msg)

        for xml_file in self.objectValues('Report Document'):
            schema = xml_file.xml_schema_location
            if schema in schema_convs.keys():
                url = xml_file.absolute_url(1)
                try:
                    converted = self.convert(schema, schema_convs.get(schema),
                                             url)
                    xml_id = xml_file.getId()
                    xml_title = getattr(xml_file, 'title', '')
                    xml_restricted = getattr(xml_file, 'restricted', '')
                    fbs = [fb for fb in xml_file.getFeedbacksForDocument()]
                    # Change the document_ids of the associated feedback files
                    # so that they don't get deleted when the xml contents are
                    # being replaced
                    for fb in fbs:
                        fb.document_id = ''
                        fb.reindex_object()
                    self.manage_addDocument(id=xml_id,
                                            title=xml_title,
                                            file=converted,
                                            content_type='text/xml',
                                            restricted=xml_restricted)
                    do_log("info",
                           "Successfully sanitized: {}.".format(xml_id), wk)
                    # Apply the correct document_ids to the associated feedbacks
                    for fb in fbs:
                        fb.document_id = xml_id
                        fb.reindex_object()
                    # Commit the transaction
                    transaction.commit()
                except Exception as e:
                    do_log("error",
                           "An error occured during the sanitization process: {}".format(str(e)),
                            wk)
            else:
                do_log("warning",
                       "Sanitization process skipped for {} for not matching the required schema(s).".format(xml_file.getId()),
                       wk)

    security.declareProtected('Change Envelopes', 'manage_addMMRXLSFile')
    def manage_addMMRXLSFile(self, file='', restricted='', required_schema=[], replace_xml=1, REQUEST=None):
        """ Adds an XLS file based on the MMR template:
            - if the file is a spreadsheet, it will call the local converters to convert it to XML
            - if the file XML, it calls replace_dd_xml
            - otherwise it calls manage_addDocument
        """
        if not file or type(file) is type('') or not hasattr(file, 'filename'):
            if REQUEST is not None:
                return self.messageDialog(
                    message='No file was specified!',
                    action='index_html')
            return 0
        else:
            l_filename = file.filename.lower()
            l_id = self.cook_file_id(file.filename)

            # delete previous version of file if exists
            if hasattr(self, l_id):
                self.manage_delObjects(l_id)
            # upload original file in the envelope
            self.manage_addDocument(id=l_id, file=file, restricted=restricted, REQUEST=REQUEST)

            # must commit transaction first, otherwise the file is not accessible from outside
            transaction.commit()
            if l_id.split('.')[-1].startswith('xls'):
                l_doc = getattr(self, l_id)
                converters = self.unrestrictedTraverse(CONVERTERS_ID)
                available_local_converters = []
                converter = None
                available_local_converters = converters._get_local_converters()
                for conv_obj in available_local_converters:
                    if conv_obj.title == 'Convert MMR Projections XLS to XML':
                        if l_doc.content_type in conv_obj.ct_input:
                            converter = conv_obj

                if converter:
                    conv = converter.convert(l_doc, converter.id)
                    if conv.content:
                        with tempfile.TemporaryFile() as tmp:
                            tmp.write(conv.content.encode('utf-8'))
                            tmp.seek(0)
                            return self.replace_dd_xml(
                                file=tmp,
                                filename='.'.join([l_id.split('.')[0], 'xml']),
                                check_schema=False,
                                restricted=restricted,
                                required_schema=required_schema,
                                replace_xml=int(replace_xml),
                                REQUEST=REQUEST)
            if REQUEST is not None:
                return self.messageDialog(
                    message="Files successfully uploaded!",
                    action='.')

    def update_doc_metadata(self, doc_ids=None, extra_params=''):
        converters = self.unrestrictedTraverse(CONVERTERS_ID)
        available_local_converters = []
        converter = None
        available_local_converters = converters._get_local_converters()
        metadata = {}
        for conv_obj in available_local_converters:
            if conv_obj.id == 'xml_to_json':
                converter = conv_obj

        if converter:
            if not doc_ids:
                docs = [doc for doc in self.objectValues('Report Document')
                        if doc.content_type == 'text/xml']
            else:
                docs = [self.unrestrictedTraverse(doc_id) for doc_id in doc_ids
                        if self.unrestrictedTraverse(doc_id).content_type == 'text/xml']
            for doc in docs:
                conv = converter.convert(doc, converter.id, extra_params=extra_params)
                try:
                    r_metadata = json.loads(conv.content)
                except Exception as e:
                    conversion_log.error("Unable to extract metadata for {}, with converter: {}".format(doc.getId(), converter.id))
                    return
                if extra_params:
                    metadata = {}
                    params = extra_params.split(' ')
                    for param in params:
                        m = r_metadata.get(param)
                        if m:
                            if len(m) == 1:
                                m = m[0]
                                metadata[m.keys()[0]] = m[m.keys()[0]]
                            else:
                                m_key = m[0].keys()[0]
                                metadata[m_key] = [k[m_key] for k in m]
                else:
                    metadata = r_metadata
                doc.metadata = metadata
                doc.reindex_object()
            return True

    def get_xml_metadata(self):
        """Retrieve the metadata from the XML document"""
        xmls = [doc for doc in self.objectValues('Report Document')
                if doc.content_type == 'text/xml' and hasattr(doc, 'metadata')]

        if len(xmls) == 1:
            return getattr(xmls[0], 'metadata')

    # These properties are defined for BDR FGAS reports
    # TODO: change these to methods instead, due to inconsistent behavior of the properties for some reason
    def get_fgas_activities(self):
        """Activities"""
        KEY = 'Activities'
        metadata = self.get_xml_metadata()
        if metadata:
            act = metadata.get(KEY)
            if act:
                return [a for a in act if act[a] == 'true']

    def get_fgas_reported_gases(self):
        """Reported Gases"""
        KEY = 'ReportedGases'
        metadata = self.get_xml_metadata()
        if metadata:
            result = []
            gases = metadata.get(KEY)
            if gases:
                if isinstance(gases, dict):
                    gases = [gases]
                for gas in gases:
                    result.append({
                        'Name': gas.get('Name'),
                        'GasId': gas.get('GasId'),
                        'GasGroup': gas.get('GasGroup'),
                        'GasGroupId': gas.get('GasGroupId')
                    })
                return result

    def get_fgas_i_authorisations(self):
        """tr_09A_imp SumOfPartnerAmounts"""
        KEY = 'tr_09A_imp'
        metadata = self.get_xml_metadata()
        if metadata:
            i_auth = metadata.get(KEY)
            if i_auth:
                return i_auth.get('SumOfPartnerAmounts')

    def get_fgas_a_authorisations(self):
        """F9_S13 AuthBalance Amount"""
        KEY = 'F9_S13'
        metadata = self.get_xml_metadata()
        if metadata:
            a_auth = metadata.get(KEY)
            if a_auth:
                a_balance = a_auth.get('AuthBalance', {})
                return a_balance.get('Amount')

    def get_pretty_activities(self):
        """Pretty print activities"""
        act_map = {'D': 'EU Destruction Company',
                   'E': 'EU Exporter Bulk',
                   'Eq-I': 'EU Importer FGases',
                   'Eq-I-RACHP-HFC': 'EU Importer FGases HFC',
                   'Eq-I-other': 'EU Importer FGases Other',
                   'FU': 'EU Feedstock User',
                   'I': 'EU Importer Bulk',
                   'I-HFC': 'EU Importer Bulk HFC',
                   'I-other': 'EU Importer Bulk Other',
                   'NIL-Report': 'NIL Report',
                   'P': 'EU Producer',
                   'P-HFC': 'EU Producer HFC',
                   'P-other': 'EU Producer Other',
                   'auth': 'Undertaking Authorisation',
                   'auth-NER': 'Undertaking Authorisation NER'}
        acts = self.get_fgas_activities()
        if acts:
            return [act_map.get(fa, fa) for fa in self.get_fgas_activities()]

# Initialize the class in order the security assertions be taken into account
InitializeClass(EnvelopeCustomDataflows)
