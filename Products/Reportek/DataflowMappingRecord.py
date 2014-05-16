__doc__ = """ Mappings between dataflows and XML schemas """

from OFS.SimpleItem import SimpleItem
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Five.browser import BrowserView


class AddForm(BrowserView):

    def __init__(self, context, request):
        super(AddForm, self).__init__(context, request)
        self.parent = self.context.getParentNode()

    def add(self):
        form = self.request.form
        oid = form.get('id')
        ob = DataflowMappingRecord(
                oid,
                form.get('title'),
                form.get('dataflow_uri'),
                form.get('allowedSchemas'),
                form.get('webformSchemas'),
                form.get('file_id'))
        self.parent._setObject(oid, ob)
        self.parent[oid]._fix_attributes()
        return self.request.response.redirect(
                    self.parent.absolute_url() + '/manage_main')

    def __call__(self, *args, **kwargs):
        if self.request.method == 'POST':
            return self.add()
        return self.index(context=self.parent)


class DataflowMappingRecord(SimpleItem):
    """ Mappings between reporting obligations (dataflows) and types of XML files (XML schemas) """

    meta_type = 'Reportek Dataflow Mapping Record'
    icon = 'misc_/Reportek/datafow_mappings_gif'

    security = ClassSecurityInfo()

    def __init__(self, id, title='', dataflow_uri='', allowedSchemas=[], webformSchemas=[], file_id=''):
        """ constructor """
        self.id = id
        self.title = title
        self.dataflow_uri = dataflow_uri
        self.allowedSchemas = filter(None, allowedSchemas)
        self.webformSchemas = filter(None, webformSchemas)
        if file_id == '': self.file_id = id + '.xml'
        else: self.file_id = file_id

    def __setstate__(self,state):
        DataflowMappingRecord.inheritedAttribute('__setstate__')(self, state)
        self._fix_attributes()

    def _fix_attributes(self):
        if not hasattr(self,'allowedSchemas'):
            if self.has_webForm:
                self.allowedSchemas = []
                self.webformSchemas = [self.schema_url]
            else:
                self.allowedSchemas = [self.schema_url]
                self.webformSchemas = []
        # Quick fix because DTML scripts are getting object properties directly.
        if not hasattr(self,'schema_url'):
            if len(self.allowedSchemas) > 0:
                self.schema_url = self.allowedSchemas[0]
                self.has_webForm = 0
            elif len(self.webformSchemas) > 0:
                self.schema_url = self.webformSchemas[0]
                self.has_webForm = 1
            else:
                self.schema_url = "We have no schema"
                self.has_webForm = 0
        if not hasattr(self,'file_id'):
            self.file_id = self.id + '.xml'

    manage_options = (
        (
            {'label' : 'Settings', 'action' : 'manage_settings_html'},
        )
        +
        SimpleItem.manage_options
    )

    security.declareProtected(view_management_screens, 'manage_settings')
    def manage_settings(self, title='', dataflow_uri='', allowedSchemas=[], webformSchemas=[], file_id='', REQUEST=None):
        """ Editing of a Dataflow Mapping Record """
        self.title = title
        self.dataflow_uri = dataflow_uri
        self.allowedSchemas = filter(None, allowedSchemas)
        self.webformSchemas = filter(None, webformSchemas)
        self.file_id = file_id
        if len(self.allowedSchemas) > 0:
            self.schema_url = self.allowedSchemas[0]
            self.has_webForm = 0
        elif len(self.webformSchemas) > 0:
            self.schema_url = self.webformSchemas[0]
            self.has_webForm = 1
        else:
            self.schema_url = "We have no schema"
            self.has_webForm = 0
        self._fix_attributes()
        self._p_changed = 1
        if REQUEST:
            message="Content changed"
            return self.manage_settings_html(self,REQUEST,manage_tabs_message=message)

    def set_schema_type(self, schema_url, has_webform):
        """ If the schema_url is listed in the object and the status has
            changed, then move it to the other list
        """
        for l_schema in self.allowedSchemas:
            if l_schema == schema_url and hasWebform == True:
                self.webformSchemas.append(schema_url)
                self.allowedSchemas.remove(schema_url)
                self._p_changed = 1
        for l_schema in self.webformSchemas:
            if l_schema == schema_url and hasWebform == False:
                self.allowedSchemas.append(schema_url)
                self.webformSchemas.remove(schema_url)
                self._p_changed = 1
        self._fix_attributes()

    security.declareProtected(view_management_screens, 'manage_settings_html')
    manage_settings_html = PageTemplateFile('zpt/dataflow-mappings/mapDataflowSchemaEdit', globals())

InitializeClass(DataflowMappingRecord)
