# # -*- coding: utf-8 -*-
import itertools

from App.FactoryDispatcher import FactoryDispatcher, ProductDispatcher


def _patched_registered_objects(self):
    app = self.request.PARENTS[-1]
    # Ugly check to avoid issues when the parent is a *Dispatcher type
    if isinstance(app, FactoryDispatcher):
        app = self.request.PARENTS[-2]
        if isinstance(app, ProductDispatcher):
            app = self.request.PARENTS[-3]

    return list(itertools.chain.from_iterable([
        conn._registered_objects
        # skip the 'temporary' connection since it stores session objects
        # which get written all the time
        for name, conn in app._p_jar.connections.items()
        if name != 'temporary'
    ]))
