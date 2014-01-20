""" Multiple dataflow mappings for a single obligation """

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
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

import messages


log = logging.getLogger(__name__)


manage_addDataflowMappingTable_html = PageTemplateFile(
    'zpt/dataflow_mapping_table_create.zpt', globals())


def manage_addDataflowMappingTable(self, id, title, dataflow_uri,
                                   REQUEST=None):
    """ add a new converter object """
    ob = DataflowMappingTable(id, title, dataflow_uri)
    self._setObject(id, ob)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)


class DataflowMappingTable(SimpleItem):
    """ Mappings between dataflows and types of XML files (XML schemas) """

    meta_type = 'Reportek Dataflow Mapping Table'
    icon = 'misc_/Reportek/datafow_mapping_table_gif'

    security = ClassSecurityInfo()

    manage_options = (
        {'label': 'Schemas', 'action': 'manage_html'},
    ) + SimpleItem.manage_options

    def __init__(self, id, title, dataflow_uri):
        self.id = id
        self.title = title
        self.dataflow_uri = dataflow_uri
        self.mapping = {'schemas': []}

    security.declarePrivate('mapping')
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

    security.declareProtected(view_management_screens, 'update')
    def update(self, title, dataflow_uri, REQUEST):
        """ """
        self.title = title
        self.dataflow_uri = dataflow_uri

        mapping_groups = defaultdict(dict)
        for field_name, value in REQUEST.form.items():
            if field_name.startswith('schema_'):
                _, n, subname = field_name.split('_', 2)
                mapping_groups[int(n)][subname] = value.decode('utf-8')

        self.mapping = {
            'schemas': [{
                    'url': group['url'],
                    'name': group['name'],
                    'has_webform': bool(group.get('has_webform')),
                } for n, group in sorted(mapping_groups.items())]
        }

        REQUEST.RESPONSE.redirect(self.absolute_url() + '/manage_html')

    security.declareProtected(view_management_screens, 'manage_html')
    manage_html = PageTemplateFile('zpt/dataflow_mapping_table.zpt', globals())

    security.declarePublic('dataflows_select')
    dataflows_select = PageTemplateFile('zpt/dataflows_select', globals())

InitializeClass(DataflowMappingTable)
