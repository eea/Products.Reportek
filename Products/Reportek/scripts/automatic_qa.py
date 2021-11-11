#!/usr/bin/env python

""" A script to run the automatic qa process

It has multiple entry points that all do different things:
* Call it with its exported console script main():

    bin/instance run bin/automatic_qa

"""


def main():
    """ Run the automatic_qa process
    This should be run through the zope client script running machinery,
    like so:
    bin/instance run bin/automatic_qa
    """

    from Products.Reportek.scripts import get_zope_site
    from Products.Reportek.constants import ENGINE_ID
    site = get_zope_site()
    engine = site.unrestrictedTraverse(ENGINE_ID, None)
    if engine:
        engine.runAutomaticApplications('AutomaticQA')
