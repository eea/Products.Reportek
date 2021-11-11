# Thanks to Ulrick Eck for the support

import Globals
from Globals import Persistent
from AccessControl import ClassSecurityInfo
from Products.PageTemplates.Expressions import getEngine
try:
    # Up to Zope 2.9
    from Products.PageTemplates.Expressions import _SecureModuleImporter
except Exception:
    # Zope 2.10
    from Products.PageTemplates.ZRPythonExpr import _SecureModuleImporter

SecureModuleImporter = _SecureModuleImporter()


class Expression (Persistent):
    text = ''
    _v_compiled = None

    security = ClassSecurityInfo()

    def __init__(self, text):
        self.text = text
        self._v_compiled = getEngine().compile(text)

    def __call__(self, econtext):
        compiled = self._v_compiled
        if compiled is None:
            compiled = self._v_compiled = getEngine().compile(self.text)
        # ?? Maybe expressions should manipulate the security
        # context stack.
        res = compiled(econtext)
        if isinstance(res, Exception):
            raise res
        # print 'returning %s from %s' % (`res`, self.text)
        return res


Globals.InitializeClass(Expression)


def exprNamespace(instance, workitem=None, activity=None, process=None,
                  openflow=None):
    c = {'instance': instance,
         'workitem': workitem,
         'activity': activity,
         'process': process,
         'openflow': openflow,
         'here': instance,
         'nothing': None,
         'options': {},
         'request': getattr(instance, 'REQUEST', None),
         'modules': SecureModuleImporter
         }
    return getEngine().getContext(c)
