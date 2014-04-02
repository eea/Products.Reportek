__doc__ = """ Multiple dataflow mappings for a single obligation """

import json
from collections import defaultdict
from os import environ
import logging
import xmlrpclib
import requests
from OFS.SimpleItem import SimpleItem
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens

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
        return [
            record
            for record in self.parent.objectValues('Dataflow Mappings Record')
            if record.dataflow_uri == dataflow_uri
        ]

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
        self.mapping = {'schemas': []}

    security.declareProtected(view_management_screens, 'mapping')
    @property
    def mapping(self):
        return json.loads(self.mapping_json)

    @mapping.setter
    def mapping(self, value):
        self.mapping_json = json.dumps(value)

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

            self.mapping = {
                'schemas': [{
                    'url': row['url'],
                    'name': row['name'],
                    'has_webform': bool(webq_resp.get(row['url'])),
                } for row in resp.json()]
            }
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

        REQUEST.RESPONSE.redirect(self.absolute_url() + '/manage_html')


    _edit = PageTemplateFile( 'zpt/dataflow-mappings/edit_record.zpt', globals())


    security.declareProtected(view_management_screens, 'add_schema')
    def add_schema(self, REQUEST):
        """ Add schema """

        data = self.mapping
        schema_uri = REQUEST.form.get('schema', '').strip()

        if schema_uri:
            if schema_uri in [r.get('url') for r in data.get('schemas')]:
                return 'Schema already exists!'
            else:
                form_data = {
                    'url': schema_uri,
                    'name': REQUEST.form.get('name'),
                    'has_webform':REQUEST.form.get('has_webform', False)
                }
                data['schemas'].append(form_data)
                self.mapping = data
                return 'Schema successfully added'

        return 'Schema cannot be empty!'


    security.declareProtected(view_management_screens, 'add_schema')
    def delete_schemas(self, REQUEST):
        """ Delete schemas """

        data = self.mapping
        schemas = REQUEST.form.get('ids', [])

        newdata = []
        for x in data.get('schemas'):
            if x['url'] not in schemas:
                newdata.append(x)

        self.mapping = {'schemas': newdata}


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

        data = self.mapping

        return self._edit(
                    schemas=data.get('schemas'),
                    message_dialog=message_dialog,
                )


InitializeClass(DataflowMappingsRecord)
