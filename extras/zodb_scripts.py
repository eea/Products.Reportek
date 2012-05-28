# import zodb_scripts; reload(zodb_scripts); zodb_scripts.dump_code(app)
from path import path

meta_types = ['DTML Document', 'DTML Method', 'Script (Python)']
ext_map = {
    'DTML Document': '.dtml-doc',
    'DTML Method': '.dtml-meth',
    'Script (Python)': '.py',
}
src_attr = {
    'DTML Document': 'raw',
    'DTML Method': 'raw',
    'Script (Python)': '_body',
}


repo = path(__file__).abspath().parent/'zodb_scripts'


def get_zodb_scripts(app):
    zodb_scripts = {}
    for ob_id, ob in app.ZopeFind(app, obj_metatypes=meta_types, search_sub=True):
        zodb_path = '/'.join(ob.getPhysicalPath()[1:])
        src = getattr(ob, src_attr[ob.meta_type])
        zodb_scripts[zodb_path] = (ob.meta_type, src)
    return zodb_scripts


def dump_code(app):
    zodb_scripts = get_zodb_scripts(app)
    if repo.exists():
        repo.rmtree() # TODO keep files, change content, remove only the extras
    repo.mkdir()
    for zodb_path, (meta_type, src) in zodb_scripts.items():
        ext = ext_map[meta_type]
        file_path = repo/(zodb_path + ext)
        if not file_path.parent.exists():
            file_path.parent.makedirs()
        f = open(file_path, 'wb')
        f.write(src)
        f.close()
