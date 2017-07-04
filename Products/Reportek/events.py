from zope.interface import implements
from Products.Reportek.interfaces import IZipStreamCompleted


class ZipStreamCompleted(object):
    """The zipstream has completed event"""
    implements(IZipStreamCompleted)

    def __init__(self, env_id):
        self.envelope_id = env_id
