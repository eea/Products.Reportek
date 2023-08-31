#!/usr/bin/env python

""" A script to cleanup envelopes older than inactive_for.

* Call it with its exported console script main():

    bin/instance run bin/auto_env_cleanup --inactive_for 30 --limit 30

"""
from Products.Reportek.scripts import get_zope_site
from Products.Reportek.RepUtils import getToolByName
from Products.Reportek.constants import DEFAULT_CATALOG
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

    brains = catalog.searchResults(query)

    return brains


def do_cleanup(site, inactive_for=30, limit=None):
    catalog = getToolByName(site, DEFAULT_CATALOG, None)
    engine = site.ReportekEngine
    b_envs = get_envelopes(catalog, inactive_for, limit)
    env_count = 0
    col_count = 0
    cols_removed = []
    processed = []
    envs_removed = []
    for b in b_envs:
        try:
            env = b.getObject()
        except Exception as e:
            print "Unable to retrieve envelope object"
        processed.append(env.absolute_url())
        col = env.getParentNode()
        if col.getPhysicalPath() not in cols_removed:
            terminated = [df for df in col.dataflow_uris
                          if engine.dataflow_lookup(df).get(
                            'terminated') == '1']
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
                    cols_removed.append(col.getPhysicalPath())
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
                    envs_removed.append(env.absolute_url())
                    col.manage_delObjects(env.getId())
                    if changed:
                        del col.can_move_released
                    env_count += 1
                except Exception as e:
                    print "Something went wrong: {}".format(str(e))
        else:
            print "Parent collection for: {} already deleted".format(
                env.absolute_url())
            env_count += 1

    transaction.commit()
    print "Removed {} collections and {} envelopes".format(col_count,
                                                           env_count)
    print "Processed: \n{}\nRemoved: \n{}".format(processed, envs_removed)


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
