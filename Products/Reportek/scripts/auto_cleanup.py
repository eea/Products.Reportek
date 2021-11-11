#!/usr/bin/env python

""" A script to cleanup old versions of an object.

* Call it with its exported console script main():

    bin/instance run bin/auto_cleanup --container \
    /xmlexports/prefills/designation_types --recursive true \
    --c_type File --prefix copy --threshold 4

"""
from OFS.interfaces import IFolder
from Products.Reportek.scripts import get_zope_site
import transaction
import sys
import argparse


def do_cleanup(container, c_type, prefix, threshold):
    objs = [obj for obj in container.objectValues(c_type)
            if obj.getId().startswith(prefix)]
    objs.sort(key=lambda obj: obj.bobobase_modification_time(), reverse=True)
    if len(objs) > threshold:
        delete_ids = [obj.getId() for obj in objs[threshold:]]
        for d_id in delete_ids:
            print "Removing {}: {}".format(c_type,
                                           '/'.join([
                                               container.absolute_url(1),
                                               d_id
                                           ]))
        container.manage_delObjects(delete_ids)
        transaction.commit()


def main():
    """ cleanup old files in a pre-defined container
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--container',
                        help='Folder path',
                        dest='container')
    parser.add_argument('--recursive',
                        help='Recurse through all subfolderish containers',
                        dest='recursive')
    parser.add_argument('--c_type',
                        help='Content type',
                        dest='c_type')
    parser.add_argument('--prefix',
                        help='Content type id prefix',
                        dest='prefix')
    parser.add_argument('--threshold',
                        help='Threshold for the number of old c_type objects',
                        dest='threshold')
    args = parser.parse_args(sys.argv[3:])
    if (args.container is None or args.recursive is None
            or args.c_type is None or args.prefix is None
            or args.threshold is None):
        parser.print_help()
        sys.exit()
    site = get_zope_site()
    container = site.unrestrictedTraverse(args.container)
    do_cleanup(container, args.c_type, args.prefix, int(args.threshold))
    if args.recursive.lower() in ['true', '1', 'on']:
        folderish = [obj for obj in container.objectValues()
                     if IFolder.providedBy(obj)]
        for folder in folderish:
            do_cleanup(folder, args.c_type, args.prefix, int(args.threshold))
    print "Operations completed."
