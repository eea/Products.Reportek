# -*- coding: utf-8 -*-
import os
import unittest
from copy import deepcopy

from App.Common import package_home
from mock import Mock
from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem
from StringIO import StringIO
from Testing import ZopeTestCase
from utils import makerequest, simple_addEnvelope
from zope import interface
from zope.component import provideAdapter
from zope.interface import implements
from zope.traversing.adapters import DefaultTraversable
from zope.traversing.interfaces import ITraversable

from Products.Five import zcml
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek import RepUtils, constants
from Products.Reportek.Collection import Collection, manage_addCollection
from Products.Reportek.ReportekEngine import ReportekEngine
from Products.Reportek.RepUtils import getToolByName

ZopeTestCase.installProduct("Reportek")
ZopeTestCase.installProduct("PythonScripts")


def _createStandardCollection(app):
    # title, descr,year, endyear, partofyear, country, locality,
    # dataflow_uris,allow_collections=0, allow_envelopes=0, id='', REQUEST=None
    p = app.manage_addProduct["Reportek"]
    manage_addCollection(
        p,
        "TestTitle",
        "Desc",
        "2003",
        "2004",
        "",
        "http://rod.eionet.eu.int/spatial/2",
        "",
        ["http://rod.eionet.eu.int/obligations/8"],
        allow_collections=1,
        allow_envelopes=1,
        id="collection",
    )
    return app.collection


class BaseUnitTest(unittest.TestCase):
    def getId(self):
        return self.id()


# This is a mix-in class to set up Reportek
class ConfigureReportek:
    exampledataflows = [
        {
            "terminated": "0",
            "PK_RA_ID": "8",
            "SOURCE_TITLE": "Basel Convention",
            "details_url": "http://rod.eionet.europa.eu/show.jsv?id=8&mode=A",
            "TITLE": "Yearly report to the Basel Convention",
            "uri": "http://rod.eionet.eu.int/obligations/8",
            "LAST_UPDATE": "2007-07-02",
            "PK_SOURCE_ID": "142",
        },
        {
            "terminated": "0",
            "PK_RA_ID": "9",
            "SOURCE_TITLE": "LCP Directive",
            "details_url": "http://rod.eionet.europa.eu/show.jsv?id=9&mode=A",
            "TITLE": """Summary  of emission  inventory from large"""
            """combustion plants (LCP)""",
            "uri": "http://rod.eionet.eu.int/obligations/9",
            "LAST_UPDATE": "2007-12-11",
            "PK_SOURCE_ID": "500",
        },
        {
            "terminated": "0",
            "PK_RA_ID": "11",
            "SOURCE_TITLE": "LCP Directive",
            "details_url": "http://rod.eionet.europa.eu/show.jsv?id=11&mode=A",
            "TITLE": """Report on programmes on emissions from large"""
            """combustion plants""",
            "uri": "http://rod.eionet.eu.int/obligations/11",
            "LAST_UPDATE": "2007-09-25",
            "PK_SOURCE_ID": "500",
        },
        {
            "terminated": "0",
            "PK_RA_ID": "15",
            "SOURCE_TITLE": "EEA AMP",
            "details_url": "http://rod.eionet.europa.eu/show.jsv?id=15&mode=A",
            "TITLE": "CLRTAP (AE-1)",
            "uri": "http://rod.eionet.eu.int/obligations/15",
            "LAST_UPDATE": "2006-11-01",
            "PK_SOURCE_ID": "499",
        },
        {
            "terminated": "1",
            "PK_RA_ID": "16",
            "SOURCE_TITLE": "EEA AMP",
            "details_url": "http://rod.eionet.europa.eu/show.jsv?id=16&mode=A",
            "TITLE": "UNFCCC (AE-2)",
            "uri": "http://rod.eionet.eu.int/obligations/16",
            "LAST_UPDATE": "2005-07-07",
            "PK_SOURCE_ID": "499",
        },
    ]

    examplelocalities = [
        {
            "iso": "AL",
            "name": "Albania",
            "uri": "http://rod.eionet.eu.int/spatial/2",
        },
        {
            "iso": "DZ",
            "name": "Algeria",
            "uri": "http://rod.eionet.eu.int/spatial/110",
        },
    ]

    def createStandardCatalog(self):
        from zope.component import getSiteManager

        from Products.ExtendedPathIndex.ExtendedPathIndex import (
            ExtendedPathIndex,
        )
        from Products.PluginIndexes.DateIndex.DateIndex import DateIndex
        from Products.PluginIndexes.FieldIndex.FieldIndex import FieldIndex
        from Products.PluginIndexes.KeywordIndex.KeywordIndex import (
            KeywordIndex,
        )
        from Products.PluginIndexes.PathIndex.PathIndex import PathIndex
        from Products.Reportek import create_reportek_indexes
        from Products.Reportek.catalog import ReportekCatalog
        from Products.Reportek.interfaces import IReportekCatalog
        from Products.ZCTextIndex.ZCTextIndex import PLexicon, ZCTextIndex

        ctool_id = constants.DEFAULT_CATALOG
        catalog = getToolByName(self.app, ctool_id, None)
        if not catalog:
            catalog = ReportekCatalog()
            self.app._setObject(ctool_id, catalog)
            tool_obj = catalog
            sm = getSiteManager(self.app)
            if (
                tool_obj is not None
                and sm.queryUtility(IReportekCatalog) is None
            ):
                sm.registerUtility(tool_obj, IReportekCatalog)
            catalog.meta_types = [
                {"name": "FieldIndex", "instance": FieldIndex},
                {"name": "KeywordIndex", "instance": KeywordIndex},
                {"name": "DateIndex", "instance": DateIndex},
                {"name": "ZCTextIndex", "instance": ZCTextIndex},
                {"name": "PathIndex", "instance": PathIndex},
                {"name": "ExtendedPathIndex", "instance": ExtendedPathIndex},
            ]
            lexicon = PLexicon("lexicon", "")
            catalog._setObject("lexicon", lexicon)
            create_reportek_indexes(catalog)
        if catalog not in self.app.objectValues():
            self.app._setObject(ctool_id, catalog)

        return catalog

    def createStandardDependencies(self):
        """Create a simple workflow process.
        Then map process to all dataflows and all countries
        """
        # Assume the workflow engine was created automatically
        of = getattr(self.app, "WorkflowEngine")

        # Create a Process Definition with two activity (Begin, End) and one
        # transition.
        of.manage_addProcess(id="begin_end", BeginEnd=1)
        pd = getattr(of, "begin_end")
        pd.addTransition(id="begin_end", From="Begin", To="End")

        # Map begin_end process to all dataflows and all countries
        of.setProcessMappings("begin_end", "1", "1")

    def createStandardCollection(self):
        # title, descr,year, endyear, partofyear, country, locality,
        # dataflow_uris,allow_collections=0, allow_envelopes=0, id='',
        # REQUEST=None
        from Products.Reportek.Collection import manage_addCollection

        manage_addCollection(
            self.app,
            "Collection Title",
            "Desc",
            "2003",
            "2004",
            "",
            "http://rod.eionet.eu.int/spatial/2",
            "",
            ["http://rod.eionet.eu.int/obligations/8"],
            allow_collections=1,
            allow_envelopes=1,
            id="collection",
        )
        return self.app.collection

    def createStandardEnvelope(self):
        """To create an envelope the following is needed:
        1) self.REQUEST.AUTHENTICATED_USER.getUserName() must return
           something
        2) There must exist a default workflow
        """
        from AccessControl import getSecurityManager

        col = self.app.collection
        #  title, descr, year, endyear, partofyear, locality,
        # REQUEST=None, previous_delivery=''
        self.login()
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        # col.manage_addProduct['Reportek'].manage_addEnvelope(
        #   'Envelope title', '', '2003', '2004', '',
        # 'http://rod.eionet.eu.int/spatial/2', REQUEST=None,
        # previous_delivery='')
        # TODO why wrap it in a product dispatcher? what happens if not?
        e = simple_addEnvelope(
            col.manage_addProduct["Reportek"],
            "",
            "",
            "2003",
            "2004",
            "",
            locality="http://rod.eionet.eu.int/spatial/2",
            REQUEST=None,
            previous_delivery="",
        )
        return e


# TODO BaseTest is supposed to be used in unit tests, it uses Mock objects
# that are not pickable
# we need some mechanism to implement functional, vertical tests, like copy
# paste zodb objects
class BaseTest(ZopeTestCase.ZopeTestCase, ConfigureReportek):
    implements(ITraversable)
    provideAdapter(DefaultTraversable, (interface.Interface,), ITraversable)

    def getId(self):
        return self.id()

    def get_abs_path(self, filename, _prefix=None):
        if _prefix:
            if isinstance(_prefix, str):
                filename = os.path.join(_prefix, filename)
            else:
                filename = os.path.join(package_home(_prefix), filename)

        return filename

    def afterSetUp(self):
        name = "mock"
        new_environ = {
            "PATH_INFO": "/" + name,
            "_stdout": StringIO(),
        }
        # root is an aquisition wrapper over app and REQUEST, as if REQUEST
        # agreggates app
        # some tests use app.REQUEST and some use root
        self.root = makerequest(self.app, new_environ["_stdout"], new_environ)
        self.app.REQUEST = self.root.REQUEST
        self.app.REQUEST.AUTHENTICATED_USER = Mock()
        self.app.REQUEST.AUTHENTICATED_USER.getUserName.return_value = "gigel"
        self.root.standard_html_header = ""
        self.root.standard_html_footer = ""
        self.root.management_page_charset = "utf-8"
        self.root.buttons_loginout = ""
        self.root.buttons_py = ""
        dropdown = open(
            self.get_abs_path("data/dropdownmenus.txt", globals()), "rb"
        )
        self.root.manage_addFile(id="dropdownmenus.txt", file=dropdown)
        dropdown.close()
        self.root["breadcrumb"] = PageTemplateFile(
            "data/breadcrumb.pt", globals()
        )
        self.root["standard_template.pt"] = PageTemplateFile(
            "data/standard_template.pt", globals()
        )
        try:
            import Products.Reportek

            zcml.load_config("configure.zcml", Products.Reportek)
        except ImportError:
            pass

        self.engine = self.create_reportek_engine(self.root)
        self.wf = self.create_flow_engine(self.root)
        self.createStandardCatalog()

    def addCollection(self, ctx, **kw):
        # title, descr,year, endyear, partofyear, country, locality,
        # dataflow_uris,allow_collections=0, allow_envelopes=0, id='',
        # REQUEST=None
        from Products.Reportek.Collection import manage_addCollection

        manage_addCollection(ctx, **kw)
        return ctx[kw.get("id")]

    def tearDown(self):
        catalog = getToolByName(self.app, constants.DEFAULT_CATALOG, None)
        if catalog:
            catalog.manage_catalogClear()
        # self.root._delObject(constants.WORKFLOW_ENGINE_ID)

    @staticmethod
    def create_reportek_engine(parent):
        ob = ReportekEngine()
        ob.dataflow_rod = Mock(
            return_value=deepcopy(ConfigureReportek.exampledataflows)
        )
        ob.localities_rod = Mock(
            return_value=deepcopy(ConfigureReportek.examplelocalities)
        )
        parent._setObject(ob.id, ob)
        return parent[ob.id]

    @staticmethod
    def create_flow_engine(parent, wf_id="WorkflowEngine"):
        from Products.Reportek.OpenFlowEngine import OpenFlowEngine

        ofe = OpenFlowEngine(wf_id, "title")
        parent._setObject(ofe.id, ofe)
        return parent[ofe.id]

    @staticmethod
    def create_envelope(col, **kwargs):
        # obj.login() # Login as test_user_1_
        # user = getSecurityManager().getUser()
        # obj.app.REQUEST.AUTHENTICATED_USER = user
        # reportek = obj.app.manage_addProduct['Reportek']
        if "year" in kwargs.keys():
            year = kwargs["year"]
        else:
            year = "2003"
        if "endyear" in kwargs.keys():
            endyear = kwargs["endyear"]
        else:
            endyear = "2004"
        if "country" in kwargs.keys():
            country = kwargs["country"]
        else:
            country = "http://rod.eionet.eu.int/spatial/2"
        env = simple_addEnvelope(
            col,
            "",
            "",
            year,
            endyear,
            "",
            country,
            REQUEST=None,
            previous_delivery="",
        )
        env.getCountryName = Mock(return_value="Unknown")
        env.getCountryCode = Mock(return_value="xx")
        return env

    @staticmethod
    def create_mock_request():
        request = Mock()
        request.physicalPathToVirtualPath = lambda x: x
        request.physicalPathToURL = lambda x: x
        response = request.RESPONSE
        response._data = StringIO()
        response.write = response._data.write
        request._headers = {}
        request.get_header = request._headers.get
        request.getHeader = Mock(return_value="bla")
        return request


class WorkflowTestCase(BaseTest):
    def afterSetUp(self):
        super(WorkflowTestCase, self).afterSetUp()
        self._setup_workflow()

    def _setup_workflow(self):
        args = {
            "id": "collection",
            "title": "mock_collection",
            "year": "2011",
            "endyear": "2012",
            "partofyear": "wholeyear",
            "country": "http://rod.eionet.eu.int/spatial/2",
            "locality": "",
            "descr": "",
            "dataflow_uris": ["http://rod.eionet.eu.int/obligations/8"],
            "allow_collections": True,
            "allow_envelopes": True,
        }
        col = Collection(**args)
        self.app._setObject("collection", col)
        self.app._setObject("Templates", Folder("Templates"))
        template = SimpleItem()
        template.id = "StartActivity"
        template.__call__ = Mock(return_value="Envelope Test Template")
        self.app.Templates._setOb("StartActivity", template)
        self.app.Templates.StartActivity.title_or_id = Mock(
            return_value="Start Activity Template"
        )

        self.create_process(self, "process")
        self.wf.addApplication("StartActivity", "Templates/StartActivity")
        self.wf.process.addActivity(
            "AutoBegin",
            split_mode="xor",
            join_mode="xor",
            start_mode=1,
            application="StartActivity",
        )
        self.wf.process.begin = "AutoBegin"
        self.wf.setProcessMappings("process", "", "")

    @staticmethod
    def create_process(obj, p_id, dataflows=None, countries=None):
        """Creates a process with explicit dataflows, countries by default"""
        obj.app.WorkflowEngine.manage_addProcess(p_id, BeginEnd=1)
        p_dataflows = ["http://rod.eionet.eu.int/obligations/8"]
        p_countries = ["http://rod.eionet.eu.int/spatial/2"]
        if dataflows:
            p_dataflows = dataflows
        if countries:
            p_countries = countries
        obj.app.WorkflowEngine.setProcessMappings(
            p_id, "", "", p_dataflows, p_countries
        )
        return obj.app.WorkflowEngine._getOb(p_id).absolute_url(1)

    def create_cepaa_set(self, idx):
        col_id = "col%s" % idx
        env_id = "env%s" % idx
        proc_id = "proc%s" % idx
        act_id = "act%s" % idx
        app_id = "act%s" % idx

        country = "http://spatial/%s" % idx
        dataflow_uris = "http://obligation/%s" % idx
        # "create collection, envelope, process, activity, application"
        col_args = {
            "id": col_id,
            "title": "mock_collection",
            "year": "2011",
            "endyear": "2012",
            "partofyear": "wholeyear",
            "country": country,
            "locality": "",
            "descr": "",
            "dataflow_uris": [dataflow_uris],
            "allow_collections": True,
            "allow_envelopes": True,
        }
        col = self.addCollection(self.app, **col_args)

        self.app.Templates.StartActivity = Mock(
            return_value="Test Application"
        )
        self.app.Templates.StartActivity.title_or_id = Mock(
            return_value="Start Activity Template"
        )
        self.create_process(
            self, proc_id, dataflows=[dataflow_uris], countries=[country]
        )
        self.wf.addApplication(app_id, "SomeFolder/%s" % app_id)

        self.app.Applications._setOb(proc_id, Folder(proc_id))
        proc = getattr(self.app.Applications, proc_id)

        app = SimpleItem(app_id)
        app.id = app_id
        app.__call__ = Mock(return_value="Test Application")
        proc._setOb(app_id, app)
        getattr(self.wf, proc_id).addActivity(
            act_id, split_mode="xor", join_mode="xor", start_mode=1
        )
        getattr(self.wf, proc_id).begin = act_id
        self.wf.setProcessMappings(proc_id, "", "", [dataflow_uris], [country])

        env_args = dict(
            process=getattr(self.wf, proc_id),
            title="Envelope_{}".format(idx),
            authUser="TestUser",
            year=2012,
            endyear=2013,
            partofyear="January",
            country=country,
            locality="TestLocality",
            descr="TestDescriptionFor_{}".format(idx),
        )
        # Mock generate_id to have predictable ids
        RepUtils.generate_id = Mock(return_value=env_id)
        self.create_envelope(col, **env_args)
