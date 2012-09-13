# This is a mix-in class to set up Reportek

class ConfigureReportek:

    exampledataflows = [
    {'terminated': '0', 'PK_RA_ID': '8', 'SOURCE_TITLE': 'Basel Convention',
     'details_url': 'http://rod.eionet.europa.eu/show.jsv?id=8&mode=A',
     'TITLE': 'Yearly report to the Basel Convention',
     'uri': 'http://rod.eionet.eu.int/obligations/8',
     'LAST_UPDATE': '2007-07-02', 'PK_SOURCE_ID': '142'},

    {'terminated': '0', 'PK_RA_ID': '9', 'SOURCE_TITLE': 'LCP Directive',
         'details_url': 'http://rod.eionet.europa.eu/show.jsv?id=9&mode=A',
         'TITLE': 'Summary  of emission  inventory from large combustion plants (LCP)',
         'uri': 'http://rod.eionet.eu.int/obligations/9',
         'LAST_UPDATE': '2007-12-11', 'PK_SOURCE_ID': '500'},
    {'terminated': '0', 'PK_RA_ID': '11', 'SOURCE_TITLE': 'LCP Directive',
         'details_url': 'http://rod.eionet.europa.eu/show.jsv?id=11&mode=A',
         'TITLE': 'Report on programmes on emissions from large combustion plants',
         'uri': 'http://rod.eionet.eu.int/obligations/11',
         'LAST_UPDATE': '2007-09-25', 'PK_SOURCE_ID': '500'},
    {'terminated': '0', 'PK_RA_ID': '15', 'SOURCE_TITLE': 'EEA AMP',
         'details_url': 'http://rod.eionet.europa.eu/show.jsv?id=15&mode=A',
         'TITLE': 'CLRTAP (AE-1)',
         'uri': 'http://rod.eionet.eu.int/obligations/15',
         'LAST_UPDATE': '2006-11-01', 'PK_SOURCE_ID': '499'},
    {'terminated': '1', 'PK_RA_ID': '16', 'SOURCE_TITLE': 'EEA AMP',
         'details_url': 'http://rod.eionet.europa.eu/show.jsv?id=16&mode=A',
         'TITLE': 'UNFCCC (AE-2)',
         'uri': 'http://rod.eionet.eu.int/obligations/16',
         'LAST_UPDATE': '2005-07-07', 'PK_SOURCE_ID': '499'},
              ]

    examplelocalities = [
        {'iso': 'AL', 'name': 'Albania', 'uri': 'http://rod.eionet.eu.int/spatial/2'},
        {'iso': 'DZ', 'name': 'Algeria', 'uri': 'http://rod.eionet.eu.int/spatial/110'},
              ]
    def createStandardDependencies(self):
        """ Create localities_table, dataflow_table and a simple workflow process.
            Then map process to all dataflows and all countries
        """
        # Create localities_table
        self.app.manage_addProduct['PythonScripts'].manage_addPythonScript(id='localities_table')
        pyapp = getattr(self.app, 'localities_table')
        pyapp.ZPythonScript_edit(params='',
              body="""return %s""" % str(self.examplelocalities) )

        # Create dataflow_table
        self.app.manage_addProduct['PythonScripts'].manage_addPythonScript(id='dataflow_table')
        pyapp = getattr(self.app, 'dataflow_table')
        pyapp.ZPythonScript_edit(params='',
              body="""return %s""" % str(self.exampledataflows) )

        # Assume the workflow engine was created automatically
        of = getattr(self.app, 'WorkflowEngine')

        # Create a Process Definition with two activity (Begin, End) and one transition.
        of.manage_addProcess(id='begin_end', BeginEnd=1)
        pd = getattr(of, 'begin_end')
        pd.addTransition(id='begin_end', From='Begin', To='End')

        # Map begin_end process to all dataflows and all countries
        of.setProcessMappings('begin_end', '1','1')

    def createStandardCollection(self):
        # title, descr,year, endyear, partofyear, country, locality,
        # dataflow_uris,allow_collections=0, allow_envelopes=0, id='', REQUEST=None
        self.app.manage_addProduct['Reportek'].manage_addCollection('TestTitle', 'Desc',
            '2003', '2004', '', 'http://rod.eionet.eu.int/spatial/2', '', ['http://rod.eionet.eu.int/obligations/8'],
            allow_collections=1, allow_envelopes=1, id='collection')


    def createStandardEnvelope(self):
        """ To create an envelope the following is needed:
            1) self.REQUEST.AUTHENTICATED_USER.getUserName() must return something
            2) There must exist a default workflow
        """
        from AccessControl import getSecurityManager
        col = self.app.collection
        #  title, descr, year, endyear, partofyear, locality,
        # REQUEST=None, previous_delivery=''
        self.login()
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        #col.manage_addProduct['Reportek'].manage_addEnvelope('', '', '2003', '2004', '',
        # 'http://rod.eionet.eu.int/spatial/2', REQUEST=None, previous_delivery='')
        from utils import simple_addEnvelope
        simple_addEnvelope(col.manage_addProduct['Reportek'], '', '', '2003', '2004', '',
                           locality='http://rod.eionet.eu.int/spatial/2', REQUEST=None, previous_delivery='')
        for e in col.objectValues():
            if e.id[:3] == "env":
                return e

