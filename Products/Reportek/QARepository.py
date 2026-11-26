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
"""Retired QARepository.

/QARepository held local QA scripts that ran as commands on the Zope host,
and it found the QA application for envelopes. Local QA scripts were removed
(see Products.Reportek.qa) and finding the QA application moved there too.

The class is kept only so that existing ZODB records, exports and history
still load. It runs nothing, nothing can be added to it, and the u20261125
update removes /QARepository.
"""

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from AccessControl.Permissions import view_management_screens
from OFS.Folder import Folder

# old import path
from Products.Reportek.qa import QAResult  # noqa: F401


class QARepository(Folder):
    """Retired; kept so that old ZODB records still load."""

    meta_type = "Reportek QARepository"
    icon = "++resource++images/qarepo.gif"

    security = ClassSecurityInfo()
    security.declareObjectProtected(view_management_screens)

    # read by Products.Reportek.qa until the u20261125 update has run
    QA_application = ""

    meta_types = ()
    all_meta_types = ()


InitializeClass(QARepository)
