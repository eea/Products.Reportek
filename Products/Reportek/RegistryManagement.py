import Products
from zope.interface import implementer
from OFS.Folder import Folder
from AccessControl import ClassSecurityInfo

from interfaces import IRegistryManagement


@implementer(IRegistryManagement)
class RegistryManagement(Folder):

    security = ClassSecurityInfo()

    def __init__(self, id, title):
        self.id = id
        self.title = title

    def all_meta_types(self):
        types = ['Script (Python)', 'Folder', 'Page Template']
        return [ t for t in Products.meta_types if t['name'] in types ]
