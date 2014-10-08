# -*- coding: utf-8 -*-
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
# Vitalie Maldur, Eau de Web

""" Module that handles the call of a XMLRPC Method
"""

import xmlrpclib


class XMLRPCMethod(object):

    def __init__(self, title, url, method_name, timeout):
        self.title = title
        self.url = url
        self.method_name = method_name
        self.timeout = timeout

    def call_method(self):
        server = xmlrpclib.ServerProxy(self.url)
        method = getattr(server, self.method_name)
        return method()