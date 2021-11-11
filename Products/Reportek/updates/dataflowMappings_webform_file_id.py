# this is meant to be run from instance debug
# >>> from Products.Reportek.updates import dataflowMappings_webform_file_id
# >>> dataflowMappings_webform_file_id.update(app)

import transaction
from Products.Reportek.DataflowMappingsRecord import DataflowMappingsRecord


def do_update(dmr):
    for schema in dmr._mappings:
        if 'webform_file_id' in schema:
            schema['has_webform'] = bool(schema['webform_file_id'])
            del schema['webform_file_id']
            dmr._mappings._p_changed = 1


def update(app):
    mappings = app.DataflowMappings
    for ob in mappings.objectValues(DataflowMappingsRecord.meta_type):
        trans = transaction.begin()
        try:
            trans.note('Update mapping record %s' % ob.id)
            do_update(ob)
            trans.commit()
        except Exception:
            trans.abort()
            raise
