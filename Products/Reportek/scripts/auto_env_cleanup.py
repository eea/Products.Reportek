#!/usr/bin/env python

""" A script to cleanup envelopes older than inactive_for.

* Call it with its exported console script main():

    bin/instance run bin/auto_env_cleanup --inactive_for 30 --limit 30

"""
from Products.Reportek.scripts import get_zope_site
from Products.Reportek.catalog import searchResults
from DateTime import DateTime
import transaction
import sys
import argparse


def get_envelopes(catalog, inactive_for, limit):
    if limit:
        limit = int(limit)
    query = {
        'meta_type': 'Report Envelope',
        'bobobase_modification_time': {
            'range': 'max',
            'query': DateTime() - int(inactive_for)
        },
        '_limit': limit
    }

    brains = searchResults(catalog, query)

    return [brain.getObject() for brain in brains]


def do_cleanup(site, inactive_for=30, limit=None):
    catalog = site.Catalog
    engine = site.ReportekEngine
    envs = get_envelopes(catalog, inactive_for, limit)
    env_count = 0
    col_count = 0
    for env in envs:
        col = env.getParentNode()
        terminated = [df for df in col.dataflow_uris
                      if engine.dataflow_lookup(df).get('terminated') == '1']
        if terminated and len(terminated) == len(col.dataflow_uris):
            print "Removing {}. Terminated obligations: {}".format(
                    col.absolute_url(),
                    terminated)
            col_par = col.getParentNode()
            changed = False
            if not getattr(col_par, 'can_move_released', False):
                col_par.can_move_released = True
                changed = True
            print "Parent collection: {}".format(col_par.absolute_url())
            try:
                col_par.manage_delObjects(col.getId())
                if changed:
                    del col_par.can_move_released
                col_count += 1
            except Exception as e:
                print "Unable to delete collection: {}: {}".format(
                    col.absolute_url(), str(e))
        else:
            print "Removing {}. Last modified date: {}".format(
                env.absolute_url(),
                env.bobobase_modification_time())
            changed = False
            if not getattr(col, 'can_move_released', False):
                col.can_move_released = True
                changed = True
            try:
                col.manage_delObjects(env.getId())
                if changed:
                    del col.can_move_released
                env_count += 1
            except Exception as e:
                print "Something went wrong: {}".format(str(e))
    transaction.commit()
    print "Removed {} collections and {} envelopes".format(col_count,
                                                           env_count)


def main():
    """ cleanup old files in a pre-defined container
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--inactive_for',
        help='Inactive for how many days. Default: 30 days',
        dest='inactive_for',
        default=30)
    parser.add_argument(
        '--limit',
        help='Limit deletions to how many results. Default: 0 (unlimited)',
        dest='limit',
        default=None)
    args = parser.parse_args(sys.argv[3:])
    site = get_zope_site()
    do_cleanup(site, inactive_for=args.inactive_for, limit=args.limit)
    print "Operations completed."
