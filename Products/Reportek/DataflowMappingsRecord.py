__doc__ = """ Multiple dataflow mappings for a single obligation """

import logging
import xmlrpclib
from os import environ

import messages
import requests
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from Products.Five.browser import BrowserView
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.ZCatalog.CatalogAwareness import CatalogAware
from ZODB.PersistentList import PersistentList

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
                form.get('dataflow_uris'))
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
                                    self.request.form['dataflow_uris'])
            if existing_records:
                [record] = existing_records
                raise Exception(
                            'A record with this dataflow already exists: {0}'
                            .format(record.getURL())
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


    security.declareProtected(view_management_screens, 'get_mapping')
    def get_mapping(self):
        """ Return the low-level mapping (persistent) list.
        This is momentarily required by Article 21, workflow, but we should refactor
        the whole mechanism """
        return self._mappings

    security.declareProtected(view_management_screens, 'mapping')
    # FIXME This was supposed to be used from web but properties cannot
    # so we should remove this hasle.
    @property
    def mapping(self):
        """ x"""
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
                    'has_webform': True if webq_resp.get(row['url']) else False,
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

    security.declareProtected(view_management_screens, 'add_schema')
    def add_schema(self, REQUEST):
        """ Add schema """

        schema_uri = REQUEST.form.get('schema', '').strip()
        schema_name = REQUEST.form.get('name', '').strip()
        has_webform = REQUEST.form.get('has_webform', None)
        wf_edit_url = REQUEST.form.get('wf_edit_url', None)

        if not schema_uri or not schema_name:
            return 'Schema and name cannot be empty!'
        # go through the getter to obtain an object
        if schema_uri in ( r['url'] for r in self._mappings ):
            return 'Schema already exists!'

        if has_webform == 'auto':
            webq_url = self.ReportekEngine.webq_url
            webq = xmlrpclib.ServerProxy(webq_url).WebQService
            webq_resp = webq.getXForm([schema_uri])
            # WebQ has a form for this, so we shall need and webform file id
            if webq_resp.get(schema_uri):
                has_webform = True
            else:
                has_webform = False
        else:
            has_webform = True if has_webform == 'yes' else False
        form_data = {
            'url': schema_uri,
            'name': schema_name,
            'has_webform': has_webform,
        }
        if has_webform and wf_edit_url:
            form_data['wf_edit_url'] = wf_edit_url
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
                self.dataflow_uri = REQUEST.form['dataflow_uris']
                self.reindex_object()
                message_dialog = 'Saved changes.'
            if REQUEST.form.get('update_xls_conversion'):
                self._xls_conversion = REQUEST.form.get('xls_conversion')
                self.xls_remove_empty_elems = bool(REQUEST.form.get('xls_remove_empty_elems', False))
                message_dialog = 'XLS Conversion method updated.'

        return self._edit(
                    schemas=self._mappings,
                    message_dialog=message_dialog,
                )

    @property
    def xls_conversion(self):
        """Return the type of xls conversion."""
        if not getattr(self, '_xls_conversion', None):
            self._xls_conversion = 'split'

        return getattr(self, '_xls_conversion', None)

InitializeClass(DataflowMappingsRecord)
