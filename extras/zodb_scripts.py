# import zodb_scripts; reload(zodb_scripts); zodb_scripts.dump_code(app)
from path import path
import codecs
import sys

meta_types = ['DTML Document', 'DTML Method',
              'Script (Python)', 'Page Template']
ext_map = {
    'DTML Document': '.dtml-doc',
    'DTML Method': '.dtml-meth',
    'Script (Python)': '.py',
    'Page Template': '.zpt',
}


repo = path(__file__).abspath().parent/'zodb_scripts'


def get_zodb_scripts(app):
    zodb_scripts = {}
    for ob_id, ob in app.ZopeFind(app, obj_metatypes=meta_types,
                                  search_sub=True):
        zodb_path = '/'.join(ob.getPhysicalPath()[1:])
        src = ob.document_src()
        try:
            src = codecs.decode(src, 'utf-8')
        except Exception:
            pass
        zodb_scripts[zodb_path] = (ob.meta_type, src)
    return zodb_scripts


def dump_code(app):
    zodb_scripts = get_zodb_scripts(app)
    if repo.exists():
        repo.rmtree()  # TODO keep files, change content, remove only extras
    repo.mkdir()
    for zodb_path, (meta_type, src) in zodb_scripts.items():
        ext = ext_map[meta_type]
        file_path = repo/(zodb_path + ext)
        if not file_path.parent.exists():
            file_path.parent.makedirs()
        f = codecs.open(file_path, 'w', encoding='utf-8')
        try:
            f.write(src)
        except Exception as e:
            sys.stderr.write(str(e) + '\n')
            pass
        f.close()
