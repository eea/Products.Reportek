import transaction
from ZODB.PersistentList import PersistentList

def bad_uri(obj):
    if validate_meta_type(obj):
        for uri in obj.dataflow_uris:
            if 'eu.int' in uri:
                return True

def validate_meta_type(obj):
    if obj.meta_type in ['Report Collection', 'Report Envelope']:
        return True

def validate(obj, validators):
    if all(map(lambda(validator): validator(obj), validators)):
        return True

def filter_objects(root, filter_level=0):
    """
    Get all child objects of root that pass validation.
    filter_level=0 returns child objects with corresp. meta_type
                   ('Report Collection' or 'Report Envelope')
    filter_level=1 returns child objects with corresp. meta_type and
                                              old dataflow_uris format
    """
    nodes = root.ZopeFind(root, search_sub=0)
    if filter_level<1:
        validators = [validate_meta_type]
    else:
        validators = [validate_meta_type, bad_uri]
    for node_id, node in nodes:
        if validate(node, validators):
            yield node
        if (getattr(node, 'allow_collections', None) or
            getattr(node, 'allow_envelopes', None)):
            for sub_node in filter_objects(node, filter_level):
                if validate(sub_node, validators):
                    yield sub_node

def update_dataflow_uris(root, commit=False):
    candidates = filter_objects(root, filter_level=0)
    counter = 0
    for obj in candidates:
        corrected_uris = PersistentList()
        for uri in obj.dataflow_uris:
            corrected_uris.append(uri.replace('rod.eionet.eu.int', 'rod.eionet.europa.eu'))
        assert(obj._p_changed==False)
        obj.dataflow_uris = corrected_uris
        assert(obj._p_changed)
        assert(type(obj.dataflow_uris) == type(PersistentList()))
        counter+=1
        if counter % 1000 == 0:
            transaction.savepoint()
    if commit:
        transaction.commit()
