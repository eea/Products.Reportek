#this is meant to be run from instance debug
#>>> from Products.Reportek.updates import add_auditor_to_view_for_documents
#>>> add_auditor_to_view_for_documents.update(app)

import transaction
from AccessControl.Permission import Permission


def update(app):
    catalog = getattr(app, 'Catalog')
    brains = catalog(meta_type='Report Document')

    for brain in brains:
        doc = brain.getObject()
        valid_roles = doc.valid_roles()

        if 'Auditor' in valid_roles:
            permissions = doc.ac_inherited_permissions(1)
            for perm in permissions:
                name, value = perm[:2]
                if name == 'View':
                    p = Permission(name, value, doc)
                    roles = list(p.getRoles())
                    if 'Auditor' not in roles:
                        roles.append('Auditor')
                        roles = tuple(roles)
                        try:
                            p.setRoles(roles)
                            print "Added Auditor to View permission for %s" % doc.absolute_url()
                        except:
                            print "Failed"

    transaction.commit()
