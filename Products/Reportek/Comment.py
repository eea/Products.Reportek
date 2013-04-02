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
# Cornel Nitu, Eau de Web


# $Id$

__version__='$Rev$'[6:-2]

import StringIO

from DateTime import DateTime
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from OFS.ObjectManager import ObjectManager
from OFS.PropertyManager import PropertyManager

from AccessControl import ClassSecurityInfo, getSecurityManager, Unauthorized
from AccessControl.Permissions import view
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from OFS.Image import manage_addFile

from RepUtils import cleanup_id, generate_id, getFilename
from Products.Reportek import constants

ADD_PERMISSION = 'Add Feedback Comments'
EDIT_PERMISSION = 'Edit Feedback Comments'
MANAGE_PERMISSION = 'Manage Feedback Comments'

class CommentItem(ObjectManager, SimpleItem, PropertyManager):
    """ class that implements a comment """

    meta_type='Report Feedback Comment'
    icon = 'misc_/Reportek/feedback_comment_png'

    security = ClassSecurityInfo()

    # what management options are there?
    manage_options = (
        (ObjectManager.manage_options[0],)+
        PropertyManager.manage_options+
        ({'label':'View',  'action':'index_html'}, )+
        SimpleItem.manage_options
    )

    def __init__(self, id, title, body, author, date, in_reply):
        self.id = id
        self.title = title
        self.body = body
        self.author = author
        self.date = date
        self.in_reply = in_reply
        self.modified_by = None
        self.modification_date = None

    def all_meta_types( self, interfaces=None ):
        """ Called by Zope to determine what kind of object the envelope can contain
        """
        y = [{'name': 'File', 'action': 'manage_addProduct/OFSP/fileAdd', 'permission': 'Add Envelopes'}]
        return y

    security.declarePrivate('edit')
    def edit(self, title, body, modified_by, modification_date):
        self.title = title
        self.body = body
        self.modified_by = modified_by
        self.modification_date = modification_date

    def editFileComment(self, file_id='', file='', REQUEST=None):
        """ Replace the content of an existing attachment """
        if self.checkPermissionEditComments():
            if file:
                file_ob = self._getOb(file_id)
                file_ob.manage_upload(file=file)
                if REQUEST:
                    return REQUEST.RESPONSE.redirect('%s/comment_edit' % self.absolute_url())
            if REQUEST:
                return REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)
        else:
            raise Unauthorized, "You are not authorized to access this resource"

    def uploadFileComment(self, file='', REQUEST=None):
        """ Upload an attachment to a comment. """
        if self.checkPermissionEditComments():
            filename = getFilename(file.filename)
            if filename:
                manage_addFile(self, filename, file)
            if REQUEST:
                return REQUEST.RESPONSE.redirect('%s/comment_edit' % self.absolute_url())
        else:
            raise Unauthorized, "You are not authorized to access this resource"

    def deleteFileComment(self, file_id='', REQUEST=None):
        """ Delete an attachment """
        if self.checkPermissionEditComments():
            if REQUEST.has_key('delete'):
                self.manage_delObjects(file_id)
            if REQUEST is not None:
                return REQUEST.RESPONSE.redirect('%s/comment_edit' % self.absolute_url())
        else:
            raise Unauthorized, "You are not authorized to access this resource"

    def updateComment(self, title='', body='', notif=True, REQUEST=None):
        """ Add a comment for this object. """
        if self.checkPermissionEditComments():
            author = self.REQUEST.AUTHENTICATED_USER.getUserName()
            date = DateTime()
            tmp = StringIO.StringIO(body)
            convs = getattr(self.getPhysicalRoot(), constants.CONVERTERS_ID, None)
            # if Local Conversion Service is down
            # the next line of code will raise an exception
            # because we don't want to save unsecure html
            sanitizer = convs['safe_html']
            body = sanitizer.convert(tmp, sanitizer.id).text
            self.edit(title, body, author, date)
            if notif:
                # Send notification to UNS
                engine = self.getEngine()
                envelope = self.getMySelf()
                if engine.UNS_server and not self.automatic:
                    engine.sendNotificationToUNS(envelope, \
                                                'Comment to feedback updated', \
                                                'Comment for the feedback %s was updated (%s#%s)' % (self.title_or_id(), self.absolute_url(), id), \
                                                self.REQUEST.AUTHENTICATED_USER.getUserName())
            if REQUEST:
                return REQUEST.RESPONSE.redirect(self.absolute_url())
        else:
            raise Unauthorized, "You are not authorized to access this resource"

    def checkPermissionEditComments(self):
        """ Check for edit comments permission """
        owner = self.getOwner()
        return getSecurityManager().checkPermission(EDIT_PERMISSION, self) or self.REQUEST.AUTHENTICATED_USER.getUserName() == owner.getId()

    comment_upload = PageTemplateFile('zpt/comment_upload', globals())
    comment_delete_file = PageTemplateFile('zpt/comment_delete_file', globals())

InitializeClass(CommentItem)


class CommentsManager:
    """ Class that handles the validation operation for a single object. """

    security = ClassSecurityInfo()

    def getComment(self, id):
        """ """
        if id:  return self._getOb(id, None)

    def listComments(self):
        """ Returns the list of comments sorted by date. """
        t = [(x.date, x) for x in self.objectValues('Report Feedback Comment')]
        t.sort()
        return [val for (key, val) in t]

    def hasComments(self):
        """ Returns the number of comments. """
        return len(self.objectValues('Report Feedback Comment')) > 0

    def countComments(self):
        """ Returns the number of comments. """
        return len(self.objectValues('Report Feedback Comment'))

    def checkPermissionAddComments(self):
        """ Check for adding comments permission """
        return getSecurityManager().checkPermission(ADD_PERMISSION, self)

    def checkPermissionManageComments(self):
        """ Check for managing comments permission """
        return getSecurityManager().checkPermission(MANAGE_PERMISSION, self)

    security.declareProtected(ADD_PERMISSION, 'addComment')
    def addComment(self, id='', title='', body='', author=None, file=None, date=None, in_reply=None, notif=True, REQUEST=None):
        """ Add a comment for this object. """
        id = cleanup_id(id)
        if not id: id = generate_id(template='')
        if author is None: author = self.REQUEST.AUTHENTICATED_USER.getUserName()
        if date is None: date = DateTime()
        else: date = DateTime(date)
        tmp = StringIO.StringIO(body)
        convs = getattr(self.getPhysicalRoot(), constants.CONVERTERS_ID, None)
        # if Local Conversion Service is down
        # the next line of code will raise an exception
        # because we don't want to save unsecure html
        sanitizer = convs['safe_html']
        body = sanitizer.convert(tmp, sanitizer.id).text
        ob = CommentItem(id, title, body, author, date, in_reply)
        if file:
            filename = getFilename(file.filename)
            manage_addFile(ob, filename, file)
        self._setObject(id, ob)
        if notif:
            # Send notification to UNS
            engine = self.getEngine()
            envelope = self.getMySelf()
            if engine.UNS_server and not self.automatic:
                engine.sendNotificationToUNS(envelope, \
                                            'Comment to feedback posted', \
                                            'Comment was posted for the feedback %s (%s#%s)' % (self.title_or_id(), self.absolute_url(), id), \
                                            self.REQUEST.AUTHENTICATED_USER.getUserName())
        if REQUEST:
            return REQUEST.RESPONSE.redirect(self.absolute_url())

    security.declareProtected(MANAGE_PERMISSION, 'deleteComment')
    def deleteComment(self, id='', REQUEST=None):
        """ Deletes a comment. """
        self.manage_delObjects([id])
        if REQUEST:
            return REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)

    def showDateTime(self, date):
        """ @param date: a DateTime object 
            @returns: string 'dd month_name yyyy hh:mm:ss'
        """
        return date.strftime('%d %b %Y %H:%M:%S')

    security.declareProtected(view, 'comments_box')
    comments_box = PageTemplateFile('zpt/comments_box', globals())

    security.declareProtected(ADD_PERMISSION, 'comment_add_html')
    comment_add_html = PageTemplateFile('zpt/comment_add', globals())

    comment_edit = PageTemplateFile('zpt/comment_edit', globals())

InitializeClass(CommentsManager)
