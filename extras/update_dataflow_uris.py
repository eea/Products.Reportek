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
    nodes = root.ZopeFind(root, search_sub=0)
    if filter_level<1:
        validators = [validate_meta_type]
    else:
        validators = [validate_meta_type, bad_uri]
    for node_id, node in nodes:
        if validate(node, validators):
            yield node
        if getattr(node, 'allow_collections', None):
            for sub_node in filter_objects(node):
                if validate(sub_node, validators):
                    yield sub_node
