# -*- coding: utf-8 -*-
from common import BaseTest
from Products.Reportek import RepUtils

import logging
logger = logging.getLogger('Reportek')
logger.manager.disable = logging.CRITICAL
# logger.disable()

BASIC_TEMPLATE = """value:$value"""
TEMPLATE = """str:$str, num:$num, unicode:$unicode"""


class RepUtilsTestCase(BaseTest):

    def test_parse_template(self):
        """
            Test the parse_template function from RepUtils module.
            Basic test.
        """
        result = RepUtils.parse_template(TEMPLATE, dict={
            'str': 'European Environment Agency',
            'num': 12.23333,
            'unicode': u'Det Europæiske Miljøagentur'})
        self.assertEqual(
            result,
            '''str:European Environment Agency, num:12.23333, '''
            '''unicode:Det Europæiske Miljøagentur''')

    def test_parse_template_empty(self):
        """
            Test the parse_template function from RepUtils module with an empty
            dictionary
        """
        self.assertRaises(Exception, RepUtils.parse_template,
                          BASIC_TEMPLATE, dict={})

    def test_parse_template_msword(self):
        """
            Tests the parse_template function from RepUtils module.
            Test MSWord characters that are somewhat risky in HTML documents.
        """
        result = RepUtils.parse_template(
            BASIC_TEMPLATE, dict={'value': u',ƒ…^†“”‘’‰•Ÿæ©–'})
        self.assertEqual(result, 'value:,ƒ…^†“”‘’‰•Ÿæ©–')
