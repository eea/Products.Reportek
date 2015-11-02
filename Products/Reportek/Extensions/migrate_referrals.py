import logging
import transaction

logger = logging.getLogger("Products.Reportek.Extensions")
info = logger.info


def migrate_referrals(self):
    catalog = self.Catalog
    brains = catalog(meta_type='Repository Referral')
    total = len(brains)
    info('INFO: Start reindexing')
    info('INFO: reindexing %s brains', total)

    for index, brain in enumerate(brains):
        try:
            obj = brain.getObject()
            obj.released = 1
            obj._p_changed = True
            if index % 100 == 0:
                transaction.commit()
                msg = 'INFO: Subtransaction committed to zodb (%s/%s)'
                info(msg, index, total)
        except Exception:
            info('ERROR: error during reindexing of %s', brain.getURL(1))

    transaction.commit()
