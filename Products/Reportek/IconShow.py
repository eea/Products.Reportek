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
# Soren Roug, EEA


from os.path import join
import string
__doc__ = """
      Icon show mix-in module

      $Id$
"""
__version__ = '$Rev$'[6:-2]


class IconShow:
    "Iconshow mixin class"

    # MIME-Type Dictionary. To add a MIME-Type, add a file in the directory
    # icons/_category_/_subcategory-icon-file_
    # example: Icon tifficon.gif for the MIME-Type image/tiff goes to
    # icons/image/tifficon.gif and the dictionary must be updated like this:
    # 'image':{'tiff':'tifficon.gif','default':'default.gif'}, ...
    _types = {'image':
              {'default': 'default.gif'},
              'text':
              {'html': 'html.gif', 'xml': 'xml.gif', 'default': 'default.gif',
               'python': 'py.gif'},
              'application':
              {'pdf': 'pdf.gif', 'zip': 'zip.gif', 'tar': 'zip.gif',
               'msword': 'doc.gif', 'excel': 'xls.gif', 'powerpoint': 'ppt.gif',  # noqa
               'default': 'default.gif',
               'vnd.oasis.opendocument.text': 'openofficeorg-oasis-text.gif',
               'vnd.oasis.opendocument.presentation': 'openofficeorg-oasis-presentation.gif',  # noqa
               'vnd.oasis.opendocument.spreadsheet': 'openofficeorg-oasis-spreadsheet.gif',  # noqa
               'vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx.gif',  # noqa
               'vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx.gif'  # noqa
               },
              'video':
              {'default': 'default.gif'},
              'audio':
              {'default': 'default.gif'},
              'default': 'default.gif'
              }

    def getContentType(self):
        """ Get the content type of a file or image.
            Returns the content type (MIME type) of a file or image.
        """
        return self.content_type

    def getIconPath(self):
        """ Depending on the MIME Type of the file/image an icon
            can be displayed. This function determines which
            image in the lib/python/Products/Reportek/icons/...
            directory shold be used as icon for this file/image
        """
        cat, sub = self._getMIMECatAndSub(self.content_type)
        if cat in self._types:
            file = self._types[cat]['default']
            for item in self._types[cat].keys():
                if string.find(sub, item) >= 0:
                    file = self._types[cat][item]
                    break
            return join('icons', cat, file)
        else:
            return join('icons', self._types['default'])

    def _getMIMECatAndSub(self, mime_string):
        """ Split MIME String into Category and Subcategory """
        cat = mime_string[:string.find(mime_string, '/')]   # MIME-category
        sub = mime_string[string.find(mime_string, '/')+1:]  # sub-category
        return cat, sub


# --------
# h = IconShow()
# h.content_type = 'video/real'
# print h.getIconPath()
