#!/usr/bin/env python

""" A script to fallin envelopes from a specific activity to another

It has multiple entry points that all do different things:
* Call it with its exported console script main():

    bin/instance run bin/auto_fallin 

"""
import argparse
import math
import os
import sys

import transaction
from DateTime import DateTime
from Products.Reportek.constants import DEFAULT_CATALOG
from Products.Reportek.scripts import get_zope_site

SCHEDULE_START = os.environ.get('SCHEDULE_START', DateTime())
SCHEDULE_PERIOD = os.environ.get('SCHEDULE_PERIOD', 'daily')
try:
    SCHEDULE_START = DateTime(SCHEDULE_START)
except Exception:
    SCHEDULE_START = DateTime()
try:
    from raven import Client
    client = Client(os.environ.get('SENTRY'))
except Exception:
    client = None

now = DateTime()
should_run = False
print "Now: {}".format(now.HTML4())
print "Scheduled start: {}".format(SCHEDULE_START.HTML4())
if SCHEDULE_PERIOD == 'weekly':
    if int(math.ceil(now.earliestTime() - SCHEDULE_START.earliestTime())) % 7 == 0:
        should_run = True
        print "Weekly run condition evaluates to: {}".format(int(math.ceil(now - SCHEDULE_START)) % 7)
        print "Triggered weekly run"
elif SCHEDULE_PERIOD == 'monthly':
    if (SCHEDULE_START.month() != now.month() or (SCHEDULE_START.month() == now.month() and SCHEDULE_START.year() != now.year())) and SCHEDULE_START.day() == now.day():
        should_run = True
        print "Triggered monthly run"
elif SCHEDULE_PERIOD == 'yearly':
    if SCHEDULE_START.day() == now.day() and SCHEDULE_START.month() == now.month():
        should_run = True
        print "Triggered yearly run"
elif SCHEDULE_PERIOD == 'daily':
    should_run = True
    print "Triggered daily run"


def get_envelopes(catalog, df_uris, act_from, act_to):
    query = {'meta_type': 'Workitem',
             'dataflow_uris': df_uris,
             'activity_id': act_from,
             'status': ['active', 'inactive']}
    brains = catalog(query)
    results = {}
    for brain in brains:
        wk = brain.getObject()
        env = wk.getParentNode()
        results[env.getPath()] = {'envelope': env,
                                  'wk': wk}
    return results


def main():
    """ fallin envelopes from a specific activity to another
    This should be run through the zope client script running machinery, like so:
    bin/instance run bin/auto_fallin --obligation <obligation_id> --act_from <ActivityID> --act_to <ActivityID> --env_year 2017
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--obligations',
                        help='Obligation(s), e.g. 673 or http://rod.eionet.europa.eu/obligations/673',
                        dest='obligations',
                        nargs='*')
    parser.add_argument('--act_from',
                        help='Activity from which to forward, e.g. FinalFeedback',
                        dest='act_from')
    parser.add_argument('--act_to',
                        help='Activity to which to forward, e.g. TechnicallyAccepted',
                        dest='act_to')
    parser.add_argument('--workflow',
                        help='Workflow of the envelopes',
                        dest='act_wf')
    parser.add_argument('--env_year_offset',
                        help='Envelope year offset, e.g. +1, meaning current year + 1, default=+0',
                        dest='env_year_offset',
                        default='+0')
    args = parser.parse_args(sys.argv[3:])

    if (args.obligations == None or args.act_from == None or args.act_to == None) or args.act_wf == None:
        parser.print_help()
        sys.exit()

    should_raise = False

    if should_run:
        obls = args.obligations
        df_prefix = 'http://rod.eionet.europa.eu/obligations/{}'
        obls = [df_prefix.format(obl) if not obl.startswith('http') else obl
                for obl in obls]
        site = get_zope_site()
        catalog = site.unrestrictedTraverse(DEFAULT_CATALOG, None)
        results = get_envelopes(catalog, obls, args.act_from, args.act_to)
        year_offset = args.env_year_offset
        env_year = DateTime().year()
        if year_offset.startswith('+'):
            env_year += int(year_offset[-1])
        elif year_offset.startswith('-'):
            env_year -= int(year_offset[-1])
        savepoint = transaction.savepoint()
        try:
            for key, value in results.iteritems():
                entry_savepoint = transaction.savepoint()
                wk = value.get('wk')
                env = value.get('envelope')
                env_wf = env.getProcess()
                activity = getattr(env_wf, args.act_to, None)
                if str(env.year) == str(env_year) and args.act_wf == env_wf.id and activity:
                    try:
                        env.falloutWorkitem(wk.id)
                        env.fallinWorkitem(wk.id, args.act_to)
                        env.endFallinWorkitem(wk.id)
                        print "{} moved from {} to {}".format(env.absolute_url(1),
                                                              args.act_from,
                                                              args.act_to)
                    except Exception as e:
                        entry_savepoint.rollback()
                        print "Error while attempting to forward {}: {}".format(env.absolute_url(1), str(e))
                        should_raise = True
                        if client:
                            client.captureException()
            transaction.commit()
        except Exception as error:
            savepoint.rollback()
            print "Error while attempting to forward envelopes: {}".format(str(error))
            should_raise = True
            if client:
                client.captureException()
    else:
        print "Defined SCHEDULE date is not today, aborting..."

    if should_raise and client:
        client.captureMessage(
            'CRON-AUTO-FALLIN: Scheduled auto-fallin job failed')
