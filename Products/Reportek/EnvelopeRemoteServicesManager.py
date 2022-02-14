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
# Miruna Badescu, Finsiel Romania


"""EnvelopeRemoteServicesManager

This class which Envelope subclasses from handles the integration with
remote systems (GDEM, UNS, etc.)

"""

import logging
import re

# Product specific imports
import RepUtils
from AccessControl import ClassSecurityInfo
from constants import QAREPOSITORY_ID
# Zope imports
from Globals import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.Document import Document
from Products.Reportek.exceptions import EnvelopeReleasedException

logger = logging.getLogger("Reportek")


class EnvelopeRemoteServicesManager:
    """ This class which Envelope subclasses from handles the integration
        with various remote systems (GDEM, UNS, etc.)
    """

    security = ClassSecurityInfo()
    webq_xml_pat = re.compile(r'(?P<base>.+__\d+)(?P<additional>\.\d+)?\.xml')

    security.declareProtected('View', 'hasSpecificFile')

    def hasSpecificFile(self, schema):
        """ Checks if an envelope has an XML file with certain schema """
        return len([x for x in self.objectValues('Report Document')
                    if x.xml_schema_location == schema])

    # duplicate function - check where it is called and remove
    security.declarePublic('hasFilesForSchema')

    def hasFilesForSchema(self, p_schema_url):
        """ If a values was provided for the p_schema_url, determine whether
        there are XML files in the envelope with a certain schema.
        Otherwise checks if there are any files at all
        """
        l_list = [x for x in self.objectValues(
            'Report Document') if x.xml_schema_location == p_schema_url]
        return len(l_list)

    def getFilesForSchema(self, schema_uri):
        """Return a list of Documents names in this envelope that are bound
        to the schema_uri.
        """
        return [doc for doc in self.objectValues(Document.meta_type)
                if doc.xml_schema_location == schema_uri]

    security.declarePublic('getNextDocId')

    def getNextDocId(self, schema_uri=None, baseName=None):
        """ Find an available name for a document inside this envelope.
        Could be a new document per schema or another document (multilang)
        for a schema that already has some documents.
        schema_uri - give a name in the familly of this schema
        baseName - use this as a base for naming the document, otherwise
        envelope id will be used
        """
        if not baseName:
            baseName = self.id
        else:
            baseName = RepUtils.cleanup_id(baseName)
            if len(baseName) < 3:
                baseName = self.id

        docs = [doc for doc in self.objectValues('Report Document')]
        # first file
        if not docs:
            return "%s__1.xml" % baseName

        docNames = [doc.id for doc in docs]

        docNamesForSchema = None
        if schema_uri:
            docNamesForSchema = [doc.id for doc in docs
                                 if doc.xml_schema_location == schema_uri]
        # try to add a document in the name__nn.mm.xml familly
        if docNamesForSchema:
            base = None
            for doc in docNamesForSchema:
                m = self.webq_xml_pat.match(doc)
                if m:
                    base = m.group('base')
                    break
                elif doc.endswith('.xml'):
                    base = doc[:-4]
                    break
            # no naming we know, but there are files for this schema
            if not base:
                base = baseName
            for i in xrange(1, 1000):
                candidate_id = "%s.%d.xml" % (base, i)
                if candidate_id not in docNames:
                    return candidate_id
            raise IndexError("More than 1000 schemas in a mapping")

        else:
            # No other files for this schema, but there are files whatsoever
            for i in xrange(1, 1000):
                candidate_id = "%s__%d.xml" % (baseName, i)
                if candidate_id not in docNames:
                    return candidate_id
            raise IndexError("More than 1000 schemas in a mapping")

    ##################################################
    # QA service
    ##################################################

    security.declareProtected('View', 'canRunQAOnFiles')

    def canRunQAOnFiles(self):
        """ Returns a list of QA script labels
            which can be manually run against the contained XML files
        """
        return getattr(self, QAREPOSITORY_ID).canRunQAOnFiles(
            self.objectValues('Report Document'))

    security.declareProtected('View', 'note')
    note = PageTemplateFile('zpt/envelope/note', globals())

    security.declareProtected('View', 'runQAScript')

    def runQAScript(self, p_file_url, p_script_id, REQUEST, return_inline=0):
        """ Runs the QA script with the specified id against
            the source XML file
            This method can be only called from the browser and the result is
            displayed in a temporary page or, in case 'return_inline' is not
            false, the result is a string
        """
        l_qa_app = getattr(self, QAREPOSITORY_ID).getQAApplication()
        if not l_qa_app:
            if return_inline:
                return 'System error.'
            REQUEST.SESSION.set('note_content_type', 'text/html')
            REQUEST.SESSION.set('note_title', 'Error')
            REQUEST.SESSION.set(
                'note_text', 'The operation could not be completed.')
            REQUEST.RESPONSE.redirect('note')
        try:
            l_file_id, l_tmp = getattr(self, QAREPOSITORY_ID)._runQAScript(
                p_file_url, p_script_id)
            if not l_tmp:
                REQUEST.SESSION.set('note_content_type', 'text/html')
                REQUEST.SESSION.set('note_title', 'Error')
                REQUEST.SESSION.set(
                    'note_text',
                    '''QA Service returned an empty result running '''
                    '''script_id: {}, for file: {}.'''.format(p_script_id,
                                                              p_file_url))
                REQUEST.RESPONSE.redirect('note')
            else:
                if return_inline:
                    return l_tmp[1].data
                REQUEST.SESSION.set('note_content_type', l_tmp[0])
                if l_file_id != 'xml':
                    REQUEST.SESSION.set(
                        'note_title', 'QA result for file %s' % l_file_id)
                else:
                    REQUEST.SESSION.set('note_title', 'QA result for envelope')
                REQUEST.SESSION.set(
                    'note_tip',
                    '''This page is only temporary. The page URL address '''
                    '''can not be used as a reference to the result. <br />'''
                    '''<br />Please use the "<em>File >> Save As</em>" '''
                    '''option within your browser to save the '''
                    '''validation results.''')
                REQUEST.SESSION.set('note_text', l_tmp[1].data)
                REQUEST.RESPONSE.redirect('note')
        except Exception as err:
            l_err = str(err).replace('<', '&lt;')
            if return_inline:
                msg = ('''The operation could not be completed because '''
                       '''of the following error: %s''' % l_err)
                return msg
            REQUEST.SESSION.set('note_content_type', 'text/html')
            REQUEST.SESSION.set('note_title', 'Error')
            REQUEST.SESSION.set(
                'note_text',
                '''The operation could not be completed because of '''
                '''the following error: %s''' % l_err)
            REQUEST.RESPONSE.redirect('note')

    security.declareProtected('View', 'runQAScripts')

    def runQAScripts(self, REQUEST):
        """ Runs multiple QA scripts with the specified file ids
            This method can be only called from the browser and the result is
            displayed in a temporary page

            Parameters in query string:
            |   file_url1=script_id11,script_id12&...
            This function assumes that all qa results have the same
            content type: 'text/html'
        """
        l_qa_app = getattr(self, QAREPOSITORY_ID).getQAApplication()

        # extract the file ids and scripts from the REQUEST
        l_files_dict = {}
        for l_file, l_scripts in REQUEST.form.items():
            l_files_dict[l_file] = l_scripts.split(',')
        if len(l_files_dict.keys()) == 0 or not l_qa_app:
            REQUEST.SESSION.set('note_content_type', 'text/html')
            REQUEST.SESSION.set('note_title', 'Error in QA service')
            REQUEST.SESSION.set(
                'note_text',
                'The quality assessment operation could not be completed.')
            REQUEST.RESPONSE.redirect('note')

        try:
            l_res = []
            for l_file, l_scripts in l_files_dict.items():
                l_file_id = l_file.split('/')[-1]
                l_res.append(
                    '<h2>QA results for file %s</h2><hr />' % l_file_id)
                for l_script in l_scripts:
                    l_f, l_d = getattr(self, QAREPOSITORY_ID)._runQAScript(
                        l_file, l_script)
                    l_res.append(l_d[1].data)

            REQUEST.SESSION.set('note_content_type', 'text/html')
            REQUEST.SESSION.set('note_title', 'Quality assessment results')
            REQUEST.SESSION.set(
                'note_tip',
                'This page is only temporary. The page url address can not\
                 be used as a reference to the result. <br /><br />\
                 Please use the "<em>File >> Save As</em>" option within\
                  your browser to save the validation results.')
            REQUEST.SESSION.set('note_text', ' '.join(l_res))
            REQUEST.RESPONSE.redirect('note')

        except Exception:
            REQUEST.SESSION.set('note_content_type', 'text/html')
            REQUEST.SESSION.set('note_title', 'Error in QA service')
            REQUEST.SESSION.set(
                'note_text',
                'The quality assessment operation could not be completed.')
            REQUEST.RESPONSE.redirect('note')

    ##################################################
    # Remote applications functions
    ##################################################

    security.declareProtected('View', 'getDocumentsForRemoteService')

    def getDocumentsForRemoteService(self):
        """ Finds all Report Documents of type XML that have to begin/complete
            a remote operation
            Returns the dictionary of {xml_schema_location:[URL_file]}
        """
        def parse_uri(uri, replace=False):
            """ Use only http uris if QA http resources is checked in
                ReportekEngine props
            """
            if replace:
                new_uri = uri.replace('https://', 'http://')
                logger.info("Original uri: %s has been replaced with uri: %s"
                            % (uri, new_uri))
                uri = new_uri
            return uri

        l_res = {}
        engine = self.getEngine()
        http_res = getattr(engine, 'qa_httpres', False)
        l_valid_schemas = self.getDataflowMappingsContainer(
        ).getSchemasForDataflows(self.dataflow_uris)
        for docu in self.objectValues('Report Document'):
            if (docu.content_type == 'text/xml' and docu.xml_schema_location
                    and (docu.xml_schema_location in l_valid_schemas
                         or not l_valid_schemas)):
                l_key = str(docu.xml_schema_location)
                if l_key in l_res:
                    l_res[l_key].append(
                        parse_uri(docu.absolute_url(), http_res))
                else:
                    l_res[l_key] = [parse_uri(docu.absolute_url(), http_res)]
        # add the envelope 'xml' method for each obligation
        for l_dataflow in self.dataflow_uris:
            l_res[l_dataflow] = [
                parse_uri(self.absolute_url(), http_res) + '/xml']
        return l_res

    security.declareProtected('Use OpenFlow', 'triggerApplication')

    def triggerApplication(self, p_workitem_id, REQUEST=None):
        """ Triggers remote applications """
        app_path = self.getApplicationUrl(p_workitem_id)
        app_ob = self.restrictedTraverse(app_path)
        l_res = app_ob.__of__(self).callApplication(p_workitem_id, REQUEST)

        # returns the result just to be able to see the result in a browser
        # if something goes wrong
        return l_res

    ##################################################
    # WebQ integration functions
    ##################################################

    security.declareProtected('Change Envelopes', 'webqKeepAlive')

    def webqKeepAlive(self):
        """This is used by webq to keep user logged in.
        Webq has all the browser request context we have, because the webq link
        is part of the same domain as BDR. Apache forwards the call to webq
        domain, keeping all the context (cookies). When webq calls this api,
        with the BDR specific cookies attached a login check will be made by
        PAS, refreshing the ZCacheable TTL for this user if he is logged in.
        302 will be returned otherwise (to the login page).
        """
        return ''

    # Protected by the same permission as for adding Report Documents
    security.declareProtected('Change Envelopes', 'saveXML')

    def saveXML(self, file_id, file, schema_url='', title='',
                applyRestriction='', restricted='', REQUEST=''):
        """ Saves the XML file modified by the WebQ as Report Document
            Called by HTTP
            For now, the return values are file_id- success and
            0 - something went wrong, but
            they could be detailed with error codes and values
        """
        if self.released:
            raise EnvelopeReleasedException("Envelope is released.\
                                             The document cannot be saved.")
        try:
            if file_id in self.objectIds():
                # the file will be replaced
                l_file = self._getOb(file_id)
                l_file.manage_file_upload(file=file, content_type='text/xml')
            else:
                # the file will be added
                if not file_id:
                    file_id = RepUtils.generate_id('doc')
                self.manage_addDocument(
                    id=file_id, title=title, file=file,
                    content_type='text/xml')
                l_file = self._getOb(file_id)
            # enforce the schema_url attribute - maybe the
            # parser did not detect it at file upload
            if schema_url and l_file.schema_url != schema_url:
                l_file.schema_url = schema_url
            if applyRestriction:
                if restricted == '1':
                    self.manage_restrict([file_id], None)
                elif restricted == '0':
                    self.manage_unrestrict([file_id], None)
            REQUEST.RESPONSE.setHeader('Content-Type', 'text/plain')
            REQUEST.RESPONSE.write('1' + file_id)
            return '1'
        except Exception as err:
            REQUEST.RESPONSE.setHeader('Content-Type', 'text/plain')
            REQUEST.RESPONSE.write('0' + str(err))
            return '0'

    security.declareProtected('Change Envelopes', 'fetchFile')

    def fetchFile(self, p_location='', p_file_name='', REQUEST=None):
        """ Grabbs a file from a certain location and uploads it as
            Report Document
        """
        l_file, l_content_type = RepUtils.utGrabFromUrl(p_location)
        if l_file is None:
            if REQUEST is not None:
                return self.messageDialog(
                    message='Error fetching the file at: ' + p_location + '!',
                    action=self.absolute_url())
            return 0
        if hasattr(self, p_file_name):
            self.manage_delObjects(p_file_name)
        self.manage_addDocument(
            id=p_file_name, file=l_file, content_type=l_content_type)
        if REQUEST is not None:
            return self.messageDialog(
                message='File successfully fetched!',
                action=self.absolute_url())

    security.declareProtected('View', 'getXMLFiles')

    def getXMLFiles(self):
        """ Returns a list of the XML files in this envelope.
            The return value is a struct where the key is the schemaurl and
            the value is a list of structs containing fileurls and file-titles
        """
        l_ret_dict = {}
        for l_doc in self.objectValues('Report Document'):
            if l_doc.content_type == 'text/xml' and l_doc.xml_schema_location:
                if l_doc.xml_schema_location in l_ret_dict:
                    l_ret_dict[str(l_doc.xml_schema_location)].append(
                        (l_doc.absolute_url(), l_doc.title_or_id()))
                else:
                    l_ret_dict[str(l_doc.xml_schema_location)] = [
                        (l_doc.absolute_url(), l_doc.title_or_id())]
        return l_ret_dict

    def getXMLSchemas(self):
        """ Gets all the schemas from the contained XML files """
        l_dict = {}
        l_list = [x.xml_schema_location for x in self.objectValues(
            'Report Document') if x.xml_schema_location != '']
        # remove duplicates
        for l_item in l_list:
            l_dict[l_item] = ''
        return l_dict.keys()

    security.declarePublic('getValidXMLSchemas')

    def getValidXMLSchemas(self, web_form_only=False):
        """ The purpose is to know if to put an edit button and a record in
            'view as...' select next to XML files
        """
        mappings_c = self.getDataflowMappingsContainer()
        return mappings_c.getSchemasForDataflows(self.dataflow_uris,
                                                 web_form_only=web_form_only)

    security.declarePublic('get_webform_for_schema')

    def get_webform_for_schema(self, schema):
        mappings_c = self.getDataflowMappingsContainer()
        wf_cust = mappings_c.get_webform_url_for_schema(schema,
                                                        self.dataflow_uris,
                                                        web_form_only=True)
        return wf_cust or self.getEngine().webq_before_edit_page

    def getWebQ_BeforeEditForm_URL(self, schema=None, custom_params=False):
        """ Retrieves the URL to the edit for of the XML file - if any """
        attributes = {
            'instance': self.absolute_url(),
            'envelope': self.absolute_url(),
            'schema': schema,
            'obligation': self.dataflow_uris[0],
            'language': 'En',
            'companyId': self.company_id,
            'countrycode': (self.getCountryCode(self.country)
                            if getattr(self, 'country', '') else None),
            'file_id': '',
            'file_url': ''
        }
        if schema:
            sch_files = self.getFilesForSchema(schema)
            if sch_files:
                attributes['file_id'] = sch_files[0].id
                attributes['file_url'] = sch_files[0].absolute_url()

        form_url = self.get_webform_for_schema(schema).format(**attributes)
        if custom_params:
            return form_url.split('?')[0]
        return form_url

    def getWebQ_MenuEnvelope_URL(self):
        """ Retrieves the URL to the edit for of the XML file - if any """
        return self.getEngine().webq_envelope_menu


# Initialize the class in order the security assertions be taken into account
InitializeClass(EnvelopeRemoteServicesManager)
