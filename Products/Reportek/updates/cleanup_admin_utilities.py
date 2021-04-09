# this is meant to be run from instance debug
# >>> from Products.Reportek.updates import cleanup_admin_utilities
# >>> cleanup_admin_utilities.update(app)
import transaction

__all__ = ['update']

# WARNING: The objects with the following id's will be removed
TO_REMOVE = [
    'admin',
    'Assign_client',
    'Assign_client_form',
    'ReportekUtilities',
    'aq1dem_upload',
    'aq1dem_uploadf',
    'aq1dem_uploadform'
]


def do_cleanup(app):
    for obj_id in TO_REMOVE:
        if hasattr(app, obj_id):
            print 'Removing %s' % obj_id
            app._delObject(obj_id, suppress_events=True)


def update(app):
    trans = transaction.begin()
    try:
        do_cleanup(app)
        trans.note('Cleanup admin utilities %s' % app.absolute_url(1))
        trans.commit()
    except:
        trans.abort()
        raise
