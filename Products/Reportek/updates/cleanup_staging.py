# this is meant to be run from instance debug
# Cleanup CDR staging instance of envelopes that have modification time prior to
# 2015.01.01
# >>> from Products.Reportek.updates import cleanup_staging
# >>> cleanup_staging.update(app)

import transaction
import DateTime
from Acquisition import aq_parent
from Testing.makerequest import makerequest


def update(app):
    app = makerequest(app)
    catalog = getattr(app, 'Catalog')
    count = 0
    query = {
        'meta_type': 'Report Envelope',
    }
    start_date = DateTime.DateTime('1980-01-01')
    end_date = DateTime.DateTime(2015, 1, 1)
    query['bobobase_modification_time'] = {
        'range': 'min:max',
        'query': (start_date, end_date)
    }
    brains = catalog(query)
    total = len(brains)

    for brain in brains:
        envelope = brain.getObject()
        parent = aq_parent(envelope)

        # Unindex all children
        children = catalog(path=envelope.getPath())
        for child in children:
            obj = child.getObject()
            obj.unindex_object()

        envelope.unindex_object()
        # In order not to check for can_move_released attribute, we suppress_events
        parent._delObject(envelope.getId(), suppress_events=True)

        count += 1
        if count % 200 == 0:
            transaction.commit()
            print "Deleting %s envelopes. Transaction commit." % count

    transaction.commit()

    print "All done! Cleaned up %s envelopes from a total of %s" % (count, total)
