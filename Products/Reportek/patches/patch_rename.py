security.declareProtected(view_management_screens, 'manage_renameForm')
manage_renameForm = DTMLFile('dtml/renameForm', globals())

security.declareProtected(view_management_screens, 'manage_renameObjects')
def manage_renameObjects(self, ids=[], new_ids=[], REQUEST=None):
    """Rename several sub-objects"""
    if len(ids) != len(new_ids):
        raise BadRequest('Please rename each listed object.')
    for i in range(len(ids)):
        if ids[i] != new_ids[i]:
            self.manage_renameObject(ids[i], new_ids[i], REQUEST)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)
    return None
