#!/usr/bin/env python

""" A script to fallin envelopes from a specific activity to another

It has multiple entry points that all do different things:
* Call it with its exported console script main():

    bin/instance run bin/auto_fallin 

"""
from Products.Reportek.constants import ENGINE_ID, DEFAULT_CATALOG
from Products.Reportek.scripts import get_zope_site
from DateTime import DateTime
import sys
import transaction
import argparse


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
                        nargs = '*')
    parser.add_argument('--act_from',
                        help='Activity from which to forward, e.g. FinalFeedback',
                        dest='act_from')
    parser.add_argument('--act_to',
                        help='Activity to which to forward, e.g. TechnicallyAccepted',
                        dest='act_to')
    parser.add_argument('--workflow',
                        help='Workflow of the envelopes',
                        dest='act_wf')
    parser.add_argument('--env_year',
                        help='Envelope year, e.g. 2017, default=current year',
                        dest='env_year',
                        default=DateTime().year())
    args = parser.parse_args(sys.argv[3:])
    if (args.obligations == None or args.act_from == None or args.act_to == None) or args.act_wf == None:
        parser.print_help()
        sys.exit()
    obls = args.obligations
    df_prefix = 'http://rod.eionet.europa.eu/obligations/{}'
    obls = [df_prefix.format(obl) if not obl.startswith('http') else obl
            for obl in obls]
    site = get_zope_site()
    catalog = site.unrestrictedTraverse(DEFAULT_CATALOG, None)
    results = get_envelopes(catalog, obls, args.act_from, args.act_to)
    savepoint = transaction.savepoint()
    try:
        for key, value in results.iteritems():
            entry_savepoint = transaction.savepoint()
            wk = value.get('wk')
            env = value.get('envelope')
            env_wf = env.getProcess()
            activity = getattr(env_wf, args.act_to, None)
            if str(env.year) == str(args.env_year) and args.act_wf == env_wf.id and activity:
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
        transaction.commit()
    except Exception as error:
        savepoint.rollback()
        print "Error while attempting to forward envelopes: {}".format(str(error))
