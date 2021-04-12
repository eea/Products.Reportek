""" Patch manage_delObjects to allow for deletion of corresponding Application
folder when deleting a process
"""
from App.Dialogs import MessageDialog
from cgi import escape
from App.special_dtml import HTML
from Products.Reportek.interfaces import IProcess
from Products.Reportek.constants import APPLICATIONS_FOLDER_ID
from webdav.Lockable import ResourceLockedError
from zExceptions import BadRequest

del_apps = HTML("""
<HTML>
<HEAD>
<TITLE>&dtml-title;</TITLE>
</HEAD>
<BODY BGCOLOR="#FFFFFF">
<FORM ACTION="&dtml-action;" METHOD="post" <dtml-if
 target>TARGET="&dtml-target;"</dtml-if>>
<TABLE BORDER="0" WIDTH="100%" CELLPADDING="10">
<TR>
  <TD VALIGN="TOP">
  <BR>
  <CENTER><B><FONT SIZE="+6" COLOR="#77003B">!</FONT></B></CENTER>
  </TD>
  <TD VALIGN="TOP">
  <BR><BR>
  <CENTER>
  &dtml-message;
  </CENTER>
  </TD>
</TR>
<TR>
  <TD VALIGN="TOP">
  </TD>
  <TD VALIGN="TOP">
  <CENTER>
  <dtml-in ids>
    <input type="checkbox" name="ids:list" value="<dtml-var sequence-item>" /><dtml-var sequence-item>
    <br>
  </dtml-in>
  <input class="form-element" type="submit" name="manage_delObjects:method" value="Delete">
  <a href="&dtml-previous;">
     <input type="button" value="Cancel" />
  </a>
  </CENTER>
  </TD>
</TR>
</TABLE>
</FORM>
</BODY></HTML>""", target='', action='manage_main', title='Changed', ids=[], previous='', message='')


def patched_manage_delObjects(self, ids=[], REQUEST=None):
    """Delete a subordinate object

    The objects specified in 'ids' get deleted.
    """
    if type(ids) is str:
        ids = [ids]
    if not ids:
        return MessageDialog(title='No items specified',
                             message='No items were specified!',
                             action='./manage_main',)
    try:
        p = self._reserved_names
    except:
        p = ()
    processes = []
    for n in ids:
        if n in p:
            return MessageDialog(title='Not Deletable',
                                 message='<EM>%s</EM> cannot be deleted.' % escape(
                                     n),
                                 action='./manage_main',)

    while ids:
        id = ids[-1]
        v = self._getOb(id, self)
        if v.wl_isLocked():
            raise ResourceLockedError, (
                'Object "%s" is locked via WebDAV' % v.getId())

        if v is self:
            raise BadRequest, '%s does not exist' % escape(ids[-1])

        if IProcess.providedBy(v):
            processes.append(v.getId())

        self._delObject(id)
        del ids[-1]

    if REQUEST is not None:
        if processes:
            app_folder = getattr(self.getPhysicalRoot(),
                                 APPLICATIONS_FOLDER_ID,
                                 None)
            app_ids = app_folder.objectIds()

            if app_folder:
                p_ids = [proc for proc in processes if proc in app_ids]

            return del_apps(title='Delete corresponding Application folders?',
                            action=app_folder.absolute_url(),
                            ids=p_ids,
                            previous='./manage_main',
                            message='Selected processes have been deleted. Do you also want to delete the corresponding /Application folders for these processes?')

        return self.manage_main(self, REQUEST, update_menu=1)
