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
# The Original Code is Reportek version 2.0.
#
# The Initial Developer of the Original Code is European Environment
# Agency (EEA).  Portions created by Eau de Web are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):

from StringIO import StringIO

class FileUploadMock(StringIO):
    """ This is an object to mock up FileUpload in ZPublisher/HTTPRequest.py
        It is much simpler and does not have the next method
    """
    def __init__(self, filename, content):
        StringIO.__init__(self, content)
        self.filename = filename

