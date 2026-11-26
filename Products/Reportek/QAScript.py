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
# Cornel Nitu, Finsiel Romania
"""Retired local QA script.

A QAScript's ``script_url`` was a command line run on the Zope host, which
let anyone allowed to add or edit one run any command there. Local QA
scripts were removed; QA runs only in the QA application (see
Products.Reportek.qa).

The class is kept only so that existing ZODB records, exports and history
still load. It cannot be added or edited and runs nothing.
"""

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from AccessControl.Permissions import view_management_screens
from OFS.SimpleItem import SimpleItem

from Products.Reportek.constants import METATYPE_QASCRIPT


class QAScript(SimpleItem):
    """Retired; kept so that old ZODB records still load."""

    meta_type = METATYPE_QASCRIPT

    security = ClassSecurityInfo()
    security.declareObjectProtected(view_management_screens)


InitializeClass(QAScript)
