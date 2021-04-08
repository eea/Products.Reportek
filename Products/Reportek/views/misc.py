from collections import defaultdict
from plone.memoize import ram
from Products.Five import BrowserView
from Products.Reportek import constants
import json
import time


class MiscAPI(BrowserView):
    """Miscellaneous API"""

    def __init__(self, *args, **kwargs):
        super(MiscAPI, self).__init__(*args, **kwargs)

        self._localities_rod = None
        self._dataflow_rod = None

    @property
    def localities_rod(self):
        if not self._localities_rod:
            engine = getattr(self.context, constants.ENGINE_ID)
            self._localities_rod = engine.localities_rod()
        return self._localities_rod

    @property
    def dataflow_rod(self):
        if not self._dataflow_rod:
            engine = getattr(self.context, constants.ENGINE_ID)
            self._dataflow_rod = engine.dataflow_rod()
        return self._dataflow_rod

    @ram.cache(lambda *args: time.time() // (60*60*12))
    def get_unique_uris(self):
        engine = getattr(self.context, constants.ENGINE_ID)
        return engine.getUniqueValuesFor('dataflow_uris')

    def get_obligations_raw(self, assigned_only=False):
        def is_requested(uri, assigned_only=False):
            res = False
            if not assigned_only:
                res = True
            else:
                if uri in self.get_unique_uris():
                    res = True
            return res

        return [{'oid': o['PK_RA_ID'],
                 'uri': o['uri'],
                 'title': o['TITLE'],
                 'terminated': o['terminated'],
                 'source_title': o['SOURCE_TITLE']} for o
                in self.dataflow_rod
                if is_requested(o['uri'], assigned_only=assigned_only)]

    @ram.cache(lambda *args: time.time() // (60*60*12))
    def get_obligations(self):
        """Returns all obligations."""
        obls = self.get_obligations_raw()
        grouped = defaultdict(list)
        for obl in obls:
            grouped[obl.get('source_title')].append(obl)

        return grouped

    @ram.cache(lambda *args: time.time() // (60*60*12))
    def get_obligations_json(self):
        obligations = self.get_obligations_raw()
        return json.dumps(obligations)

    @ram.cache(lambda *args: time.time() // (60*60*12))
    def get_assigned_obligations(self):
        """Returns obligations assigned to at least one Collection or Envelope.
        """
        obls = self.get_obligations_raw(assigned_only=True)
        grouped = defaultdict(list)
        for obl in obls:
            grouped[obl.get('source_title')].append(obl)

        return grouped
