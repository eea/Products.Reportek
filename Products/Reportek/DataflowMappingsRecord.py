__doc__ = """ Multiple dataflow mappings for a single obligation """

import json
from os import environ
import logging
import xmlrpclib
import requests
from OFS.SimpleItem import SimpleItem
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from ZODB.PersistentList import PersistentList

from Products.ZCatalog.CatalogAwareness import CatalogAware
from Products.Five.browser import BrowserView
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

import messages

log = logging.getLogger(__name__)



class AddForm(BrowserView):


    def __init__(self, context, request):
        super(AddForm, self).__init__(context, request)
        self.parent = self.context.getParentNode()


    def add(self):
        form = self.request.form
        oid = form.get('id')
        ob = DataflowMappingsRecord(
                oid,
                form.get('title'),
                form.get('dataflow_uri'))
        self.parent._setObject(oid, ob)
        return self.request.response.redirect(
                    self.parent.absolute_url() + '/manage_main')


    def get_records_by_dataflow(self, dataflow_uri):
        return self.parent.Catalog(
                meta_type='Dataflow Mappings Record',
                dataflow_uri=dataflow_uri,
                path='/DataflowMappings')


    def __call__(self, *args, **kwargs):
        if self.request.method == 'POST':
            existing_records = self.get_records_by_dataflow(
                                    self.request.form['dataflow_uri'])
            if existing_records:
                [record] = existing_records
                raise Exception(
                            'A record with this dataflow already exists: {0}'
                            .format(record.absolute_url())
                        )
            return self.add()
        return self.index(context=self.parent)



class DataflowMappingsRecord(CatalogAware, SimpleItem):
    """ Multiple dataflow mappings for a single obligation """

    meta_type = 'Dataflow Mappings Record'

    security = ClassSecurityInfo()


    manage_options = (
        {'label': 'Schemas', 'action': 'edit'},
    ) + SimpleItem.manage_options


    def __init__(self, id, title, dataflow_uri):
        self.id = id
        self.title = title
        self.dataflow_uri = dataflow_uri
        self._mappings = PersistentList()


    security.declareProtected(view_management_screens, 'mapping')
    @property
    def mapping(self):
        return {'schemas': self._mappings}


    @mapping.setter
    def mapping(self, value):
        if 'schemas' in value:
            self._mappings = PersistentList(value['schemas'])


    security.declareProtected(view_management_screens, 'load_from_dd')
    def load_from_dd(self, REQUEST):
        """ """
        resp = requests.get(environ['DATADICTIONARY_SCHEMAS_URL'], params={
            'obligationId': self.dataflow_uri.replace('.eu.int', '.europa.eu'),
        })
        if resp.status_code == 200:
            webq_url = self.ReportekEngine.webq_url
            webq = xmlrpclib.ServerProxy(webq_url).WebQService
            webq_resp = webq.getXForm([row['url'] for row in resp.json()])

            new_mappings = PersistentList()
            for i, row in enumerate(resp.json()):
                mapping = {
                    'url': row['url'],
                    'name': row['name'],
                    'webform_file_id': "%s_%d.xml"%(self.id, i) if webq_resp.get(row['url']) else '',
                }
                new_mappings.append(mapping)
            self._mappings = new_mappings
            messages.add(REQUEST, "Mappings updated from Data Dictionary.")

        elif resp.status_code == 404:
            log.info("404 response from DD for %r (%s)",
                     resp.url, self.dataflow_uri)
            messages.add(REQUEST, "No mappings found in Data Dictionary.",
                         'error')

        else:
            log.warn("Error fetching DD mappings for %r: %r, %r",
                     self.dataflow_uri, resp, resp.text)
            messages.add(REQUEST, "Error fetching from Data Dictionary",
                         'error')

        REQUEST.RESPONSE.redirect(self.absolute_url() + '/edit')

    def _get_next_webform_file_id(self):
        webform_file_ids = [ x['webform_file_id'] for x in self._mappings if x['webform_file_id'] ]
        if not webform_file_ids:
            return "%s_1.xml" % self.id
        for i in xrange(1, 1000):
            candidate_id = "%s_%d.xml" % (self.id, i)
            if candidate_id not in webform_file_ids:
                return candidate_id
        raise IndexError("More than 1000 schemas in a mapping")

    security.declareProtected(view_management_screens, 'add_schema')
    def add_schema(self, REQUEST):
        """ Add schema """

        schema_uri = REQUEST.form.get('schema', '').strip()
        schema_name = REQUEST.form.get('name', '').strip()
        if not schema_uri or not schema_name:
            return 'Schema and name cannot be empty!'
        # go through the getter to obtain an object
        if schema_uri in ( r['url'] for r in self._mappings ):
            return 'Schema already exists!'

        form_data = {
            'url': schema_uri,
            'name': schema_name,
            'webform_file_id': REQUEST.form.get('webform_file_id', ''),
        }
        if form_data['webform_file_id'] == 'Auto detect':
            webq_url = self.ReportekEngine.webq_url
            webq = xmlrpclib.ServerProxy(webq_url).WebQService
            webq_resp = webq.getXForm([schema_uri])
            # WebQ has a form for this, so we shall need and webform file id
            if webq_resp.get(schema_uri):
                form_data['webform_file_id'] = self._get_next_webform_file_id()
            else:
                form_data['webform_file_id'] = ''
        elif form_data['webform_file_id'] and not form_data['webform_file_id'].endswith('.xml'):
            form_data['webform_file_id'] = form_data['webform_file_id'] + '.xml'
        self._mappings.append(form_data)
        return 'Schema successfully added'



    security.declareProtected(view_management_screens, 'add_schema')
    def delete_schemas(self, REQUEST):
        """ Delete schemas """
        schemas = REQUEST.form.get('ids', [])
        self._mappings = PersistentList( x for x in self._mappings if x['url'] not in schemas )


    _edit = PageTemplateFile( 'zpt/dataflow-mappings/edit_record.zpt', globals())


    security.declareProtected(view_management_screens, 'edit')
    def edit(self, REQUEST):
        """ Edit properties """

        message_dialog = ''

        if REQUEST.method == 'POST':

            if REQUEST.form.get('add'):
                message_dialog = self.add_schema(REQUEST)

            if REQUEST.form.get('delete'):
                message_dialog = self.delete_schemas(REQUEST)

            if REQUEST.form.get('update'):
                self.title = REQUEST.form['title']
                self.dataflow_uri = REQUEST.form['dataflow_uri']
                message_dialog = 'Saved changes.'

        return self._edit(
                    schemas=self._mappings,
                    message_dialog=message_dialog,
                )


InitializeClass(DataflowMappingsRecord)
