from App.Dialogs import MessageDialog
from Products.Reportek.interfaces import IProcess
from Products.Reportek.constants import APPLICATIONS_FOLDER_ID
# from App.special_dtml import DTMLFile
from zExceptions import BadRequest


def patched_manage_renameForm(self, REQUEST=None, RESPONSE=None):
    """ Patched manage_renameForm so that we can add extra form inputs for
        processes
    """
    processes = []

    if REQUEST:
        ids = REQUEST.get('ids')
        if not ids:
            return MessageDialog(title='No items specified',
                                 message='No items were specified!',
                                 action='',)
        for oid in ids:
            obj = self.get(oid)
            if IProcess.providedBy(obj):
                processes.append(oid)

    REQUEST.form['processes'] = processes
    import pdb;pdb.set_trace()
    # self.renameForm = DTMLFile('dtml/renameForm', globals())

    # return self.renameForm(self, REQUEST)


def patched_manage_renameObjects(self, ids=[], new_ids=[],
                                 renameapp_ids=[], REQUEST=None):
    """Rename several sub-objects"""
    if len(ids) != len(new_ids):
        raise BadRequest('Please rename each listed object.')
    app_folder = getattr(self.getPhysicalRoot(), APPLICATIONS_FOLDER_ID, None)

    for i in range(len(ids)):
        if ids[i] != new_ids[i]:
            self.manage_renameObject(ids[i], new_ids[i], REQUEST)
            # If checked, also rename the corresponding Application folders
            if ids[i] in renameapp_ids and app_folder:
                if ids[i] in app_folder.objectIds():
                    app_folder.manage_renameObject(ids[i], new_ids[i], REQUEST)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)
    return None
