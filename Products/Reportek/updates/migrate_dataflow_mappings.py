# this is meant to be run from instance debug
# >>> from Products.Reportek.updates import migrate_dataflow_mappings
# >>> migrate_dataflow_mappings.update(app)

import transaction
from Products.Reportek.DataflowMappingsRecord import DataflowMappingsRecord

from string import ascii_uppercase
from random import choice


def do_update(app):
    mappings = app.DataflowMappings
    dataflows = {}
    for ob in mappings.objectValues('Reportek Dataflow Mapping Record'):
        data = {
            'title': ob.title,
            'schema': ob.allowedSchemas,
            'webform': ob.webformSchemas}
        if ob.dataflow_uri in dataflows:
            dataflows[ob.dataflow_uri].append(data)
        else:
            dataflows[ob.dataflow_uri] = [data]

    for k, v in dataflows.items():
        oid = (''.join(choice(ascii_uppercase) for i in range(12)))
        ob = DataflowMappingsRecord(
            oid,
            v[0]['title'],
            k)
        mappings._setObject(oid, ob)
        schemas = []
        for data in v:
            if isinstance(data['schema'], list):
                if len(data['schema']) > 0:
                    schema = data['schema'][0]
                else:
                    schema = ''
            else:
                schema = data['schema']
            if schema:
                schemas.append({
                    'url': schema,
                    'name': data['title'],
                    'has_webform': False})
                mappings[oid].mapping = {'schemas': schemas}


def update(app):
    trans = transaction.begin()
    try:
        do_update(app)
        trans.note('Update site %s' % app.absolute_url(1))
        trans.commit()
    except Exception:
        trans.abort()
        raise
