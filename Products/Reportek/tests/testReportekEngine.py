import unittest
from StringIO import StringIO
import zipfile
from DateTime import DateTime
from mock import Mock, patch
from utils import (create_fake_root, create_upload_file,
                  create_envelope, add_document)
from Products.Reportek.ReportekEngine import ReportekEngine
from Products.Reportek.Envelope import Envelope
from Products.Reportek.Collection import Collection
from Products.Reportek import constants
from Products.Reportek import Converters
from common import BaseTest
from common import ConfigureReportek


class ReportekEngineTest(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(ReportekEngineTest, self).afterSetUp()
        self.createStandardCatalog()

        self.engine.localities_dict=Mock(return_value={
            'http://rod.eionet.eu.int/spatial/2': {'name': 'Albania'},
            'http://rod.eionet.eu.int/spatial/3': {'name': 'Austria'}
        })
        self.engine.ZopeTime = Mock(return_value=DateTime())
        self.engine.Build_collections_form = Mock(return_value="form_template")

    def test_searchfeedbacks_on_disk(self):
        self.createStandardDependencies()
        self.createStandardCollection()
        self.createStandardEnvelope()
        try:
            dtml = ReportekEngine.searchfeedbacks
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_resultsfeedbacks_on_disk(self):
        try:
            dtml = ReportekEngine.resultsfeedbacks
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_recent_uploads_on_disk(self):
        try:
            dtml = ReportekEngine.recent
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_searchdataflow_on_disk(self):
        try:
            zpt = ReportekEngine._searchdataflow
            zpt.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_searchxml_on_disk(self):
        try:
            dtml = ReportekEngine.searchxml
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_resultsxml_on_disk(self):
        try:
            dtml = ReportekEngine.resultsxml
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_countryreporters_on_disk(self):
        try:
            dtml = ReportekEngine.countryreporters
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_getUniqueValuesFor(self):
        process = Mock()
        process.absolute_url = Mock(return_value='/ProcessURL')
        first_envelope = Envelope(process=process,
                            title='FirstEnvelope',
                            authUser='TestUser',
                            year=2012,
                            endyear=2013,
                            partofyear='January',
                            country='http://example.com/country/1',
                            locality='TestLocality',
                            descr='TestDescription')
        first_envelope._content_registry_ping = Mock()
        first_envelope.id = 'first_envelope'
        self.root._setObject(first_envelope.id, first_envelope)
        self.root[first_envelope.id].manage_changeEnvelope(
                dataflow_uris='http://example.com/dataflow/1'
        )
        results = self.engine.getUniqueValuesFor('dataflow_uris')
        self.assertEqual(results, ('http://example.com/dataflow/1',))

    def test_assign_role_with_Assign_client(self):
        self.root._setObject( 'col', Collection('col',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': ['http://rod.eionet.eu.int/spatial/3'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        self.assertEqual(
            ('Reporter',),
            self.root.col.get_local_roles_for_userid('testuser')
        )

    def test_assign_multiple_roles_with_Assign_client(self):
        self.root._setObject( 'col', Collection('col',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': ['http://rod.eionet.eu.int/spatial/3'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        kwargs.update({'crole': 'Auditor'})
        self.engine.Assign_client(**kwargs)
        self.assertEqual(
            ('Reporter', 'Auditor'),
            self.root.col.get_local_roles_for_userid('testuser')
        )

    def test_remove_role_with_Remove_client(self):
        self.root._setObject( 'col', Collection('col',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': ['http://rod.eionet.eu.int/spatial/3'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        self.engine.Remove_client(**kwargs)
        self.assertEqual((), self.root.col.get_local_roles_for_userid('testuser'))

    def test_remove_specified_role_only_with_Remove_client(self):
        self.root._setObject( 'col', Collection('col',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': ['http://rod.eionet.eu.int/spatial/3'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        kwargs.update({'crole': 'Auditor'})
        self.engine.Assign_client(**kwargs)
        kwargs.update({'crole': 'Reporter'})
        self.engine.Remove_client(**kwargs)
        self.assertEqual(
            ('Auditor',),
            self.root.col.get_local_roles_for_userid('testuser')
        )

    def test_assign_role_to_multiple_collections(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.root._setObject( 'col2', Collection('col2',
            'EU, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/2',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.assertEqual((), self.root.col1.get_local_roles_for_userid('testuser'))
        self.assertEqual((), self.root.col2.get_local_roles_for_userid('testuser'))
        kwargs = {
            'ccountries': ['http://rod.eionet.eu.int/spatial/2',
                           'http://rod.eionet.eu.int/spatial/3'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        self.assertEqual(
            ('Reporter', ),
            self.root.col1.get_local_roles_for_userid('testuser')
        )
        self.assertEqual(
            ('Reporter', ),
            self.root.col2.get_local_roles_for_userid('testuser')
        )

    def test_remove_role_from_multiple_collections(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.root._setObject( 'col2', Collection('col2',
            'EU, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/2',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': [
                'http://rod.eionet.eu.int/spatial/2',
                'http://rod.eionet.eu.int/spatial/3'
            ],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        self.assertEqual(
            ('Reporter', ),
            self.root.col1.get_local_roles_for_userid('testuser')
        )
        self.assertEqual(
            ('Reporter', ),
            self.root.col2.get_local_roles_for_userid('testuser')
        )
        self.engine.Remove_client(**kwargs)
        self.assertEqual(
            (),
            self.root.col1.get_local_roles_for_userid('testuser')
        )
        self.assertEqual(
            (),
            self.root.col2.get_local_roles_for_userid('testuser')
        )

    def test_remove_not_existing_role(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': ['at'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Remove_client(**kwargs)
        self.assertEqual(
            (),
            self.root.col1.get_local_roles_for_userid('testuser')
        )

    def test_assign_role_to_multiple_users(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': ['http://rod.eionet.eu.int/spatial/3'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser', 'testuser1']
        }
        self.engine.Assign_client(**kwargs)
        self.assertEqual(
            ('Reporter', ),
            self.root.col1.get_local_roles_for_userid('testuser')
        )
        self.assertEqual(
            ('Reporter', ),
            self.root.col1.get_local_roles_for_userid('testuser1')
        )

    def test_remove_role_for_specified_user_only(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': ['http://rod.eionet.eu.int/spatial/3'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser', 'testuser1']
        }
        self.engine.Assign_client(**kwargs)
        self.assertEqual(
            ('Reporter', ),
            self.root.col1.get_local_roles_for_userid('testuser')
        )
        kwargs.update({'dns': ['testuser']})
        self.engine.Remove_client(**kwargs)
        self.assertEqual((), self.root.col1.get_local_roles_for_userid('testuser'))
        self.assertEqual(
            ('Reporter',),
            self.root.col1.get_local_roles_for_userid('testuser1')
        )

    def test_assign_role_to_specific_obligation_only(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.root._setObject( 'col2', Collection('col2',
            'EU, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/2',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/2'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': ['http://rod.eionet.eu.int/spatial/2'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/2',
            'dns': ['testuser', 'testuser1']
        }
        self.engine.Assign_client(**kwargs)
        self.assertEqual((), self.root.col1.get_local_roles_for_userid('testuser'))
        self.assertEqual(
            ('Reporter',),
            self.root.col2.get_local_roles_for_userid('testuser1'))

    def test_wrong_assign_returns_fail_message(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': ['http://rod.eionet.eu.int/spatial/3'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/2', #different obligation
            'dns': ['testuser']
        }
        result = self.engine.Assign_client(**kwargs)
        self.assertEqual('fail', result[0]['status'])

    def test_assign_returns_ok_message(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': ['http://rod.eionet.eu.int/spatial/3'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        result = self.engine.Assign_client(**kwargs)
        self.assertEqual('success', result[0]['status'])

    def test_assign_returns_both_ok_and_fail_messages(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.root._setObject( 'col2', Collection('col2',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/2',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/2'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': [
                'http://rod.eionet.eu.int/spatial/3',
                'http://rod.eionet.eu.int/spatial/2'
            ],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        result = self.engine.Assign_client(**kwargs)
        self.assertEqual('success', result[0]['status'])
        self.assertEqual('fail', result[1]['status'])

    def test_remove_returns_ok_message(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': [
                'http://rod.eionet.eu.int/spatial/3',
            ],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        result = self.engine.Remove_client(**kwargs)
        self.assertEqual('success', result[0]['status'])

    def test_remove_returns_fail_message(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': [
                'http://rod.eionet.eu.int/spatial/3',
            ],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/2',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        result = self.engine.Remove_client(**kwargs)
        self.assertEqual('fail', result[0]['status'])

    def test_remove_returns_both_ok_and_fail_messages(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.root._setObject( 'col2', Collection('col2',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/2',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/2'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': [
                'http://rod.eionet.eu.int/spatial/3',
                'http://rod.eionet.eu.int/spatial/2'
            ],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        result = self.engine.Remove_client(**kwargs)
        self.assertEqual('success', result[0]['status'])
        self.assertEqual('fail', result[1]['status'])

    @unittest.expectedFailure
    def test_manage_editEngine_GET(self):
        """
        This tests simulates a GET to ReportekEngine/manage_editEngine
        and checks that engine's attributes are not changed
        """
        from copy import copy
        self.engine.ZopeTime = Mock(return_value=DateTime())
        before_values = copy(self.engine.__dict__)
        # FIXME
        self.login()
        assert self.engine.manage_properties()
        self.assertEqual(before_values, self.engine.__dict__)

    @unittest.expectedFailure
    def test_manage_editEngine_no_REQUEST(self):
        """
        This tests simulates a programmatic call to ReportekEngine.manage_editEngine
        and checks that engine's attributes are changed accordingly
        """
        # FIXME
        self.engine.ZopeTime = Mock(return_value=DateTime())
        self.engine.title='Before Title'
        self.engine.manage_editEngine(title='After Title', REQUEST=None)
        self.assertEqual('After Title', self.engine.title)

    @unittest.expectedFailure
    def test_manage_editEngine_POST(self):
        """
        This tests simulates a POST to ReportekEngine.manage_editEngine
        and checks that engine's attributes are changed accordingly
        """
        # FIXME
        self.root.REQUEST['REQUEST_METHOD'] = 'POST'
        self.engine.ZopeTime = Mock(return_value=DateTime())
        self.engine.title='Before Title'
        self.engine.manage_editEngine(title='After Title', REQUEST=self.root.REQUEST)
        self.assertEqual('After Title', self.engine.title)

    def test_Build_collections_with_GET(self):
        self.root.REQUEST.method = 'GET'
        localities = {
            'http://spatial/3': {
                'iso': 'AT',
                'name': 'Austria',
                'uri': 'http://spatial/3'
            }
        }
        self.engine.localities_dict = Mock(return_value=localities)
        self.engine.localities_table = Mock(return_value=[])
        self.engine.dataflow_table = Mock(return_value=[])
        self.root._setObject( 'at', Collection('at',
            'Austria', '', '', '',
            'http://spatial/3',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))

        self.engine.Build_collections(
            ccountries = ['http://spatial/3'],
            ctitle='Test collection',
            cobligation= ['http://dataflow/1'],
            cid='',
            REQUEST=self.root.REQUEST
        )
        self.assertEqual(0, len(self.root.at.objectIds()))

    def test_Build_collections_with_POST(self):
        self.root.REQUEST.method = 'POST'
        localities = {
            'http://spatial/3': {
                'iso': 'AT',
                'name': 'Austria',
                'uri': 'http://spatial/3'
            }
        }
        self.engine.localities_dict = Mock(return_value=localities)
        self.engine.localities_table = Mock(return_value=[])
        self.engine.dataflow_table = Mock(return_value=[])
        self.root._setObject( 'at', Collection('at',
            'Austria', '', '', '',
            'http://spatial/3',
            '', '',
            ['http://dataflow/1'],
            allow_collections=0, allow_envelopes=1))

        self.engine.Build_collections(
            ccountries = ['http://spatial/3'],
            ctitle='Test collection',
            cobligation= ['http://dataflow/1'],
            cid='',
            REQUEST=self.root.REQUEST
        )
        self.assertEqual(1, len(self.root.at.objectIds()))

    def test_Build_collections_multiple_countries(self):
        self.root.REQUEST.method = 'POST'
        localities = {
            'http://spatial/1': {
                'iso': 'iso1',
                'name': 'name1',
                'uri': 'http://spatial/1'
            },
            'http://spatial/2': {
                'iso': 'iso2',
                'name': 'name2',
                'uri': 'http://spatial/2'
            }
        }
        self.engine.localities_dict = Mock(return_value=localities)
        self.engine.localities_table = Mock(return_value=[])
        self.engine.dataflow_table = Mock(return_value=[])
        self.root._setObject( 'iso1', Collection('iso1',
            'name1', '', '', '',
            'http://spatial/1',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))
        self.root._setObject( 'iso2', Collection('iso2',
            'name2', '', '', '',
            'http://spatial/2',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))

        self.engine.Build_collections(
            ccountries = ['http://spatial/1', 'http://spatial/2'],
            ctitle='Test collection',
            cobligation= ['http://dataflow/2'],
            cid='',
            REQUEST=self.root.REQUEST
        )
        self.assertEqual(1, len(self.root.iso1.objectIds()))
        self.assertEqual(1, len(self.root.iso2.objectIds()))

    def test_Build_collections_specific_country_only(self):
        self.root.REQUEST.method = 'POST'
        localities = {
            'http://spatial/1': {
                'iso': 'iso1',
                'name': 'name1',
                'uri': 'http://spatial/1'
            },
            'http://spatial/2': {
                'iso': 'iso2',
                'name': 'name2',
                'uri': 'http://spatial/2'
            }
        }
        self.engine.localities_dict = Mock(return_value=localities)
        self.engine.localities_table = Mock(return_value=[])
        self.engine.dataflow_table = Mock(return_value=[])
        self.root._setObject( 'iso1', Collection('iso1',
            'name1', '', '', '',
            'http://spatial/1',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))
        self.root._setObject( 'iso2', Collection('iso2',
            'name2', '', '', '',
            'http://spatial/2',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))

        self.engine.Build_collections(
            ccountries = ['http://spatial/1'],
            ctitle='Test collection',
            cobligation= ['http://dataflow/1'],
            cid='',
            REQUEST=self.root.REQUEST
        )
        self.assertEqual(1, len(self.root.iso1.objectIds()))
        self.assertEqual(0, len(self.root.iso2.objectIds()))

    def pattern_test(self, pattern=''):
        self.root.REQUEST.method = 'POST'
        localities = {
            'http://spatial/1': {
                'iso': 'iso1',
                'name': 'name1',
                'uri': 'http://spatial/1'
            },
        }
        self.engine.localities_dict = Mock(return_value=localities)
        self.engine.localities_table = Mock(return_value=[])
        self.engine.dataflow_table = Mock(return_value=[])
        self.engine.Build_collections(
            pattern = pattern,
            ccountries = ['http://spatial/1'],
            ctitle='Test collection',
            cobligation= ['http://dataflow/1'],
            cid='',
            REQUEST=self.root.REQUEST
        )

    def test_Build_collections_with_one_level_structure_pattern(self):
        self.root._setObject( 'iso1', Collection('iso1',
            'name1', '', '', '',
            'http://spatial/1',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))
        self.root.iso1._setObject( 'eu', Collection('eu',
            'eu', '', '', '',
            'http://spatial/1',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))
        self.pattern_test('eu')
        self.assertEqual(1, len(self.root.iso1.eu.objectIds()))

    def test_Build_collections_with_multiple_levels_structure_pattern(self):
        self.root._setObject( 'iso1', Collection('iso1',
            'name1', '', '', '',
            'http://spatial/1',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))
        self.root.iso1._setObject( 'lev1', Collection('lev1',
            'eu', '', '', '',
            'http://spatial/1',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))
        self.root.iso1.lev1._setObject( 'lev2', Collection('lev2',
            'eu', '', '', '',
            'http://spatial/1',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))
        self.pattern_test('lev1/lev2')
        self.assertEqual(1, len(self.root.iso1.lev1.lev2.objectIds()))

    def test_Build_collections_with_bad_structure_pattern(self):
        self.root._setObject( 'iso1', Collection('iso1',
            'name1', '', '', '',
            'http://spatial/1',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))
        self.root.iso1._setObject( 'eu', Collection('eu',
            'eu', '', '', '',
            'http://spatial/1',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))
        self.pattern_test('bad')
        self.assertEqual(0, len(self.root.iso1.eu.objectIds()))

    def test_Build_collections_with_leading_slash_pattern(self):
        self.root._setObject( 'iso1', Collection('iso1',
            'name1', '', '', '',
            'http://spatial/1',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))
        self.root.iso1._setObject( 'eu', Collection('eu',
            'eu', '', '', '',
            'http://spatial/1',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))
        self.pattern_test('/eu')
        self.assertEqual(1, len(self.root.iso1.eu.objectIds()))

    def test_Build_collections_with_backslashes_pattern(self):
        self.root._setObject( 'iso1', Collection('iso1',
            'name1', '', '', '',
            'http://spatial/1',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))
        self.root.iso1._setObject( 'eu', Collection('eu',
            'eu', '', '', '',
            'http://spatial/1',
            '', '',
            [],
            allow_collections=0, allow_envelopes=1))
        self.pattern_test('\eu')
        self.assertEqual(1, len(self.root.iso1.eu.objectIds()))


class SearchResultsTest(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(SearchResultsTest, self).afterSetUp()
        self.createStandardCatalog()
        from Products.Reportek.Envelope import Envelope
        process = Mock()
        process.absolute_url = Mock(return_value='/ProcessURL')
        first_envelope = Envelope(process=process,
                            title='FirstEnvelope',
                            authUser='TestUser',
                            year=2012,
                            endyear=2013,
                            partofyear='January',
                            country='http://example.com/country/1',
                            locality='TestLocality',
                            descr='TestDescription')
        first_envelope._content_registry_ping = Mock()
        first_envelope.id = 'first_envelope'
        self.root._setObject(first_envelope.id, first_envelope)
        self.root[first_envelope.id].manage_changeEnvelope(dataflow_uris='http://example.com/dataflow/1')
        self.root['first_envelope'].getEngine = Mock()
        setattr(
            self.root.getPhysicalRoot(),
            constants.CONVERTERS_ID,
            Converters.Converters())
        safe_html = Mock(convert=Mock(return_value=Mock(text='feedbacktext')))
        getattr(self.root.getPhysicalRoot(),
                constants.CONVERTERS_ID).__getitem__ = Mock(return_value=safe_html)
        self.root['first_envelope'].manage_addFeedback('feedbackid', 'Title',
                                                       'Feedback text', '','WorkflowEngine/begin_end', 1)
        self.root['first_envelope'].manage_addFeedback('feedback5', 'Title',
                                                       'Feedback text', '','WorkflowEngine/begin_end', 1)
        self.root['first_envelope'].manage_addFeedback('feedback10', 'Title',
                                                       'Feedback text', '','WorkflowEngine/begin_end', 1)

        second_envelope = Envelope(process=process,
                            title='SecondEnvelope',
                            authUser='TestUser',
                            year=2012,
                            endyear=2013,
                            partofyear='June',
                            country='http://example.com/country/2',
                            locality='TestLocality',
                            descr='TestDescription')
        second_envelope._content_registry_ping = Mock()
        second_envelope.id = 'second_envelope'
        self.root._setObject(second_envelope.id, second_envelope)
        self.root[second_envelope.id].manage_changeEnvelope(dataflow_uris='http://example.com/dataflow/2')

    def test_returns_all(self):
        results = self.engine.getSearchResults()
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [self.root.first_envelope,
                                self.root.first_envelope['feedbackid'],
                                self.root.first_envelope['feedback5'],
                                self.root.first_envelope['feedback10'],
                                self.root.second_envelope])

    def test_filter_by_meta_type(self):
        results = self.engine.getSearchResults(meta_type='Report Feedback')
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [self.root.first_envelope['feedbackid'],
                                self.root.first_envelope['feedback5'],
                                self.root.first_envelope['feedback10']])

    def test_filter_by_dataflow_uris(self):
        results = self.engine.getSearchResults(dataflow_uris='http://example.com/dataflow/2')
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [self.root.second_envelope])

    def test_filter_by_country(self):
        results = self.engine.getSearchResults(country='http://example.com/country/1')
        res = [el.getObject() for el in results]
        self.assertEqual(res, [self.root.first_envelope,
                                self.root.first_envelope['feedbackid'],
                                self.root.first_envelope['feedback5'],
                                self.root.first_envelope['feedback10']])

    def test_filter_by_id(self):
        results = self.engine.getSearchResults(id={'range': 'min:max',
                                                   'query': ['feedback0','feedback9']})
        feedbacks = [el.getObject() for el in results]
        self.assertEqual(feedbacks, [self.root.first_envelope['feedback5'],
                                self.root.first_envelope['feedback10']])

    def test_filter_by_reportingdate(self):
        self.root['first_envelope'].manage_changeEnvelope(
                                reportingdate=DateTime("2010/07/02 00:00:00 GMT+2"))
        results = self.engine.getSearchResults(
                    reportingdate={'range': 'min:max',
                                   'query': [DateTime("2010/07/01 00:00:00 GMT+2"),
                                             DateTime("2010/07/03 00:00:00 GMT+2")]
                                  })
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [self.root.first_envelope])


class ReportekEngineZipTest(unittest.TestCase):

    def test_zip_download(self):
        content = 'test content for our document'
        root = create_fake_root()
        engine = BaseTest.create_reportek_engine(root)

        envelope = create_envelope(root)
        doc = add_document(envelope, create_upload_file(content, 'foo.txt'))
        envelope.released = True
        envelope.title = "TestedEnvelope"

        response_body = StringIO()
        mock_response = Mock(write=response_body.write)

        with patch('Products.Reportek.ReportekEngine.getSecurityManager'):
            engine.zipEnvelopes(['/envelope'], Mock(), mock_response)

        response_body.seek(0)
        response_zip = zipfile.ZipFile(response_body)
        self.assertEqual(response_zip.namelist(), [
            'TestedEnvelope/foo.txt', 'TestedEnvelope/metadata.txt',
            'TestedEnvelope/README.txt', 'TestedEnvelope/history.txt'])
        self.assertEqual(response_zip.read('TestedEnvelope/foo.txt'), content)
