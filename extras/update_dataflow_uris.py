import logging

import transaction
from ZODB.PersistentList import PersistentList

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)-15s '
                           '%(message)s'
                    )
changes_log = logging.getLogger(__name__ + '.logger')
changes_log.setLevel(logging.DEBUG)
fh = logging.FileHandler('dataflow_uris_changes.log', mode='w')
fh.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
changes_log.addHandler(fh)
changes_log.addHandler(ch)


def bad_uri(obj):
    if validate_meta_type(obj):
        for uri in getattr(obj, 'dataflow_uris', []):
            if '.eu.int' in uri:
                return True
        if '.eu.int' in getattr(obj, 'dataflow_uri', ''):
            return True


def validate_meta_type(obj):
    if obj.meta_type in ['Report Collection',
                         'Report Envelope',
                         'Reportek Dataflow Mapping Record',
                         'Repository Referral']:
        return True


def validate(obj, validators):
    if all(map(lambda(validator): validator(obj), validators)):
        return True


def filter_objects(root, filter_level=0):
    """
    Get all child objects of root that pass validation.
    filter_level=0 returns child objects with corresp. meta_type
                   ('Report Collection' or 'Report Envelope' or 'Reportek
                   Dataflow Mapping Record')
    filter_level=1 returns child objects with corresp. meta_type and
                                              old dataflow_uris format
    """
    nodes = root.objectValues()
    if filter_level < 1:
        validators = [validate_meta_type]
    else:
        validators = [validate_meta_type, bad_uri]
    for node in nodes:
        if validate(node, validators):
            yield node
        if node.meta_type in ['Report Collection',
                              'Reportek Dataflow Mappings']:
            for sub_node in filter_objects(node, filter_level):
                if validate(sub_node, validators):
                    yield sub_node


def update_dataflow_uris(root, commit=False):
    candidates = filter_objects(root, filter_level=0)
    counter = 0
    changes_log.info('DATAFLOW URIS UPDATES')
    transaction.savepoint()
    for obj in candidates:
        dataflow_uris = getattr(obj, 'dataflow_uris', None)
        dataflow_uri = ''
        corrected_uris = PersistentList()
        corrected_uri = ''
        message = ''
        message += ('{type:21}: {url}'.format(
            type=(obj.meta_type[:17]+'... ' if len(obj.meta_type) > 20
                  else obj.meta_type),
            url=obj.absolute_url_path()))
        for uri in getattr(obj, 'dataflow_uris', []):
            corrected_uris.append(uri.replace(
                'rod.eionet.eu.int', 'rod.eionet.europa.eu'))
        if not(getattr(obj, 'dataflow_uris', None) is None):
            obj.dataflow_uris = corrected_uris
            if not dataflow_uris == corrected_uris:
                message += '\n{attr:21}: {before} -> {after}'.format(
                    attr='dataflow_uris',
                    before=dataflow_uris,
                    after=obj.dataflow_uris)

        if getattr(obj, 'dataflow_uri', None):
            dataflow_uri = obj.dataflow_uri
            corrected_uri = dataflow_uri.replace(
                'rod.eionet.eu.int', 'rod.eionet.europa.eu')
            obj.dataflow_uri = corrected_uri
            if not dataflow_uri == corrected_uri:
                message += '\n{attr:21}: {before} -> {after}'.format(
                    attr='dataflow_uri',
                    before=dataflow_uri,
                    after=corrected_uri)

        if getattr(obj, 'country', None):
            country_uri = obj.country
            corrected_country = country_uri.replace(
                'rod.eionet.eu.int', 'rod.eionet.europa.eu')
            obj.country = corrected_country
            if not country_uri == corrected_country:
                message += '\n{attr:21}: {before} -> {after}'.format(
                    attr='country',
                    before=country_uri,
                    after=corrected_country)
        if not obj._p_changed:
            message += "\nno changes made"
        message += "\n"
        changes_log.info(message)
        counter += 1
        if counter % 1000 == 0:
            transaction.savepoint()
    if commit:
        transaction.commit()
        changes_log.info('ALL CHANGES COMMITED TO ZODB!')
