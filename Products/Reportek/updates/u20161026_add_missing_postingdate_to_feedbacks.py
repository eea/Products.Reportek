# -*- coding: utf-8 -*-
# Add missing postingdates to feedbacks
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20161026_add_missing_postingdate_to_feedbacks; u20161026_add_missing_postingdate_to_feedbacks.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import DEPLOYMENT_MDR
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.ZCatalog.ZCatalog import ZCatalog
import logging
import transaction

logger = logging.getLogger(__name__)
VERSION = 7
APPLIES_TO = [
    DEPLOYMENT_BDR,
    DEPLOYMENT_CDR,
    DEPLOYMENT_MDR
]


def get_last_qa(obj):
    qas = obj.get_qa_workitems()
    if qas:
        return qas[-1]


def get_last_evtlog_time(wk):
    evt_log = getattr(wk, 'event_log')
    end_time = evt_log[-1].get('time')
    return end_time


def get_posting_date(obj):
    postingdate = None
    if obj.id.startswith('AutomaticQA'):
        last_qa = get_last_qa(obj)
        if last_qa:
            postingdate = get_last_evtlog_time(last_qa)
        logger.info('{} looks like an AutomaticQA feedback, getting postingdate from the last Automatic QA workitem'.format(obj.absolute_url()))
    elif not obj.automatic:
        last_wk = obj.getListOfWorkitems()[-1]
        postingdate = get_last_evtlog_time(last_wk)
        logger.info('{} looks like a manual feedback, getting postingdate from the last workitem'.format(obj.absolute_url()))
    else:
        drafts = [wk for wk in obj.getListOfWorkitems()
                  if wk.activity_id == 'Draft']
        last_draft = drafts[-1]
        postingdate = get_last_evtlog_time(last_draft)
        logger.info('{} looks like a conversion log, getting postingdate from the last draft workitem'.format(obj.absolute_url()))
    return postingdate


def add_indexes(tempc):
    logger.info('Step 1.5: Adding indexes')
    tempc.addIndex('meta_type', 'FieldIndex')
    tempc.addIndex('postingdate', 'FieldIndex')
    tempc.addColumn('meta_type')
    tempc.addColumn('postingdate')
    logger.info('Step 1.5: Done')


def get_temp_catalog(app):
    try:
        tempc = getattr(app, 'u20161026tempcatalog')
    except AttributeError:
        logger.info('Step 1: Creating a temporary catalog')
        tempc = ZCatalog('u20161026tempcatalog', 'Reportek Temporary Catalog')
        app._setObject('u20161026tempcatalog', tempc)
        tempc = app.unrestrictedTraverse('/u20161026tempcatalog')
        add_indexes(tempc)
        transaction.commit()
        logger.info('Step 1: Done')
    return tempc


def rebuild_tempc(app, tempc):
    catalog = getattr(app, 'Catalog')
    brains = catalog({'meta_type': 'Report Feedback'})

    count = 0
    logger.info('Step 3: Indexing in the temporary catalog')
    for brain in brains:
        try:
            fb = brain.getObject()
        except Exception as e:
            logger.error('Unable to retrieve object: {} due to {}'.format(brain.getURL(), str(e)))
        if fb:
            tempc.catalog_object(fb, '/'.join(fb.getPhysicalPath()))
        if count % 10000 == 0:
            transaction.savepoint()
            logger.info('savepoint at %d records', count)
        count += 1
    logger.info('Step 3: Done')
    transaction.commit()


def add_missing_postingdate(app):
    tempc = get_temp_catalog(app)
    tempc.manage_catalogClear()
    rebuild_tempc(app, tempc)
    obj = None
    brains = tempc({'meta_type': 'Report Feedback'})

    logger.info('Step 4: Comparing and updating postingdate')
    count = 0
    for brain in brains:
        try:
            obj = brain.getObject()
        except Exception as e:
            logger.error('Unable to retrieve object: {} due to {}'.format(brain.getURL(), str(e)))
        if obj:
            if obj.postingdate != brain.postingdate:
                new_postingdate = get_posting_date(obj)
                logger.info('Update postingdate for: {} from: {}'
                            ' to: {}.'.format(obj.absolute_url(),
                                              obj.postingdate,
                                              new_postingdate))
                obj.postingdate = new_postingdate
                if count % 10000 == 0:
                    transaction.savepoint()
                    logger.info('savepoint at %d records', count)
        count += 1
    logger.info('Step 4: Done')
    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    if not add_missing_postingdate(app):
        return
    app.manage_delObjects('u20161026tempcatalog')
    transaction.commit()
    logger.info('Postingdate migration complete')
    return True
