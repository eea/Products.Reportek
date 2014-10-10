##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Utility functions

These functions are designed to be imported and run at
module level to add functionality to the test environment.

$Id$
"""

import os
import sys
import time
import random
import json
import tempfile
import shutil
from StringIO import StringIO
import transaction
import ZODB, ZODB.MappingStorage, ZODB.blob
from OFS.Folder import Folder
from mock import Mock, patch

import lxml.html
import lxml.cssselect


class HtmlElementList(list):

    def text(self):
        return ' '.join(e.text_content() for e in self)


class HtmlPage(object):

    def __init__(self, html):
        self._doc = lxml.html.fromstring(html)

    def select(self, css_selector):
        sel = lxml.cssselect.CSSSelector(css_selector)
        return HtmlElementList(sel(self._doc))


def setupCoreSessions(app=None):
    '''Sets up the session_data_manager e.a.'''
    from Acquisition import aq_base
    commit = 0

    if app is None:
        return appcall(setupCoreSessions)

    if not hasattr(app, 'temp_folder'):
        from Products.TemporaryFolder.TemporaryFolder import MountedTemporaryFolder
        tf = MountedTemporaryFolder('temp_folder', 'Temporary Folder')
        app._setObject('temp_folder', tf)
        commit = 1

    if not hasattr(aq_base(app.temp_folder), 'session_data'):
        from Products.Transience.Transience import TransientObjectContainer
        toc = TransientObjectContainer('session_data',
                    'Session Data Container',
                    timeout_mins=3,
                    limit=100)
        app.temp_folder._setObject('session_data', toc)
        commit = 1

    if not hasattr(app, 'browser_id_manager'):
        from Products.Sessions.BrowserIdManager import BrowserIdManager
        bid = BrowserIdManager('browser_id_manager',
                    'Browser Id Manager')
        app._setObject('browser_id_manager', bid)
        commit = 1

    if not hasattr(app, 'session_data_manager'):
        from Products.Sessions.SessionDataManager import SessionDataManager
        sdm = SessionDataManager('session_data_manager',
                    title='Session Data Manager',
                    path='/temp_folder/session_data',
                    requestName='SESSION')
        app._setObject('session_data_manager', sdm)
        commit = 1

    if commit:
        transaction.commit()


def setupZGlobals(app=None):
    '''Sets up the ZGlobals BTree required by ZClasses.'''
    if app is None:
        return appcall(setupZGlobals)

    root = app._p_jar.root()
    if not root.has_key('ZGlobals'):
        from BTrees.OOBTree import OOBTree
        root['ZGlobals'] = OOBTree()
        transaction.commit()


def setupSiteErrorLog(app=None):
    '''Sets up the error_log object required by ZPublisher.'''
    if app is None:
        return appcall(setupSiteErrorLog)

    if not hasattr(app, 'error_log'):
        try:
            from Products.SiteErrorLog.SiteErrorLog import SiteErrorLog
        except ImportError:
            pass
        else:
            app._setObject('error_log', SiteErrorLog())
            transaction.commit()


def load_json(name):
    with open(os.path.join(os.path.dirname(__file__), name), "rb") as f:
        return json.load(f)


def importObjectFromFile(container, filename, quiet=0):
    '''Imports an object from a (.zexp) file into the given container.'''
    from ZopeLite import _print, _patched
    quiet = quiet or not _patched
    start = time.time()
    if not quiet: _print("Importing %s ... " % os.path.basename(filename))
    container._importObjectFromFile(filename, verify=0)
    transaction.commit()
    if not quiet: _print('done (%.3fs)\n' % (time.time() - start))


_Z2HOST = None
_Z2PORT = None

def startZServer(number_of_threads=1, log=None):
    '''Starts an HTTP ZServer thread.'''
    global _Z2HOST, _Z2PORT
    if _Z2HOST is None:
        _Z2HOST = '127.0.0.1'
        _Z2PORT = random.choice(range(55000, 55500))
        from ZServer import setNumberOfThreads
        setNumberOfThreads(number_of_threads)
        from threadutils import QuietThread, zserverRunner
        t = QuietThread(target=zserverRunner, args=(_Z2HOST, _Z2PORT, log))
        t.setDaemon(1)
        t.start()
        time.sleep(0.1) # Sandor Palfy
    return _Z2HOST, _Z2PORT


def makerequest(app, stdout=sys.stdout, environ={}):
    '''Wraps the app into a fresh REQUEST.'''
    from ZPublisher.BaseRequest import RequestContainer
    from ZPublisher.Request import Request
    from ZPublisher.Response import Response
    response = Response(stdout=stdout)
    new_environ = {}
    new_environ['SERVER_NAME'] = _Z2HOST or 'nohost'
    new_environ['SERVER_PORT'] = '%d' % (_Z2PORT or 80)
    new_environ['REQUEST_METHOD'] = 'GET'
    new_environ.update(environ)
    request = Request(sys.stdin, new_environ, response)
    request._steps = ['noobject'] # Fake a published object
    request['ACTUAL_URL'] = request.get('URL') # Zope 2.7.4
    return app.__of__(RequestContainer(REQUEST=request))


def appcall(function, *args, **kw):
    '''Calls a function passing 'app' as first argument.'''
    from base import app, close
    app = app()
    args = (app,) + args
    try:
        return function(*args, **kw)
    finally:
        transaction.abort()
        close(app)


def makelist(arg):
    '''Turns arg into a list. Where arg may be
       list, tuple, or string.
    '''
    if type(arg) == type([]):
        return arg
    if type(arg) == type(()):
        return list(arg)
    if type(arg) == type(''):
       return filter(None, [arg])
    raise ValueError('Argument must be list, tuple, or string')


class FakeRootObject(Folder):
    def manage_page_header(self):
        return 'manage header'
    def manage_page_footer(self):
        return 'manage footer'
    def manage_page_tabs(self):
        return 'manage tabs'

    def getPhysicalPath(self):
        return ('',)
    def getPhysicalRoot(self):
        return self


def create_fake_root():
    return FakeRootObject()


def create_catalog(app):
    from Products.ZCatalog.ZCatalog import ZCatalog
    from Products.PluginIndexes.FieldIndex.FieldIndex import FieldIndex
    from Products.ZCTextIndex.ZCTextIndex import ZCTextIndex
    from Products.PluginIndexes.DateIndex.DateIndex import DateIndex
    from Products.PluginIndexes.KeywordIndex.KeywordIndex import KeywordIndex
    from Products.PluginIndexes.PathIndex.PathIndex import PathIndex
    from Products.Reportek import create_reportek_indexes

    app._setObject('Catalog', ZCatalog('Catalog'))
    catalog = app.Catalog

    catalog.meta_types = [
            {'name': 'FieldIndex', 'instance': FieldIndex},
            {'name': 'ZCTextIndex', 'instance': ZCTextIndex},
            {'name': 'DateIndex', 'instance': DateIndex},
            {'name': 'KeywordIndex', 'instance': KeywordIndex},
            {'name': 'PathIndex', 'instance': PathIndex}]

    create_reportek_indexes(catalog)
    return catalog


def create_temp_reposit():
    tmp_dir = tempfile.mkdtemp()
    instance_home_patch = patch.dict(__builtins__, {'CLIENT_HOME': tmp_dir})
    instance_home_patch.start()
    os.makedirs(os.path.join(tmp_dir, 'reposit'))
    original_tempdir = tempfile.tempdir
    tempfile.tempdir = tmp_dir

    def cleanup():
        tempfile.tempdir = original_tempdir
        shutil.rmtree(tmp_dir)
        instance_home_patch.stop()
    return cleanup


def create_upload_file(data='', filename='testfile.txt'):
    f = StringIO(data)
    f.filename = filename
    return f


def chase_response(target, environ={}, user=None):
    from utils import publish_view
    response = publish_view(target, environ=environ, user=user)
    while response.status == 302:
        redirect_url = response.headers['location']
        target_url = redirect_url.replace(
                         target.absolute_url(), '').split('?')[0]
        target = target.unrestrictedTraverse(target_url, None)
        response = publish_view(target, environ=environ, user=user)
    return response


def publish_view(view, environ={}, user=None):
    from ZPublisher.WSGIPublisher import publish
    from AccessControl.SecurityManagement import noSecurityManager

    name = view.__name__
    new_environ = {
        'PATH_INFO': '/' + name,
        '_stdout': StringIO(),
    }
    new_environ.update(environ)

    root = create_fake_root()
    user = Mock() if not user else user
    root.__allow_groups__ = Mock(validate=Mock(return_value=user))
    request = makerequest(root, new_environ['_stdout'], new_environ).REQUEST
    view.__doc__ = 'non-empty documentation'
    setattr(root, name, view)

    module_info = (Mock(), # before
                   None, #after
                   root, #object
                   'TESTING', #realm
                   True, #debug_mode
                   Mock(), #err_hook
                   None, #validated_hook
                   Mock()) #tm
    try:
        return publish(request, 'Zope2', Mock(return_value=module_info))
    finally:
        noSecurityManager()


def create_envelope(parent, id='envelope'):
    from Products.Reportek.Envelope import Envelope
    process = Mock()
    process.absolute_url.return_value = '/mock-process'
    process.begin = 'mock-process-begin'
    e = Envelope(process, '', '', '', '', '', '', '', '')
    e.id = id
    parent._setObject(id, e)
    e.dataflow_uris = []

    return parent[id]


def simple_addEnvelope(parent, *args, **kwargs):
    """
    def manage_addEnvelope(self, title, descr, year, endyear, partofyear, locality,
            REQUEST=None, previous_delivery=''):
    """
    from Products.Reportek.Envelope import manage_addEnvelope
    params = [ kwargs.get('title', ''),
               kwargs.get('descr', ''),
               kwargs.get('year', '2011'),
               kwargs.get('endyear', '2012'),
               kwargs.get('partofyear', 'Whole Year'),
               kwargs.get('locality'),
               kwargs.get('REQUEST', None),
               kwargs.get('previous_delivery','') ]
    for i, arg in enumerate(args):
        if arg:
            params[i] = arg
    result = manage_addEnvelope(parent, *params)
    envelope = parent.unrestrictedTraverse(result.split('/')[-1], None)

    return envelope


def add_document(envelope, upload_file, restricted=False, id=''):
    from Products.Reportek.Document import manage_addDocument
    with patch.object(envelope, 'REQUEST', create=True) as mock_request:
        mock_request.physicalPathToVirtualPath = lambda x: x
        restricted_str = 'on' if restricted else ''
        doc_id = manage_addDocument(envelope, file=upload_file,
                                    restricted=restricted_str, id=id)
    return envelope[doc_id]


def add_feedback(envelope, feedbacktext, feedbackId=None, restricted=False, idx=0):
    from Products.Reportek.Feedback import manage_addFeedback
    restricted_str = 'on' if restricted else ''
    manage_addFeedback(envelope, feedbacktext=feedbacktext, id=feedbackId,
                       restricted=restricted_str)

    return envelope.objectValues('Report Feedback')[idx]


def add_hyperlink(envelope, hyperlink):
    from Products.Reportek.Hyperlink import manage_addHyperlink
    manage_addHyperlink(envelope, hyperlinkurl=hyperlink)
    return envelope.objectValues('Report Hyperlink')[0]


class MockDatabase(object):

    def __init__(self):
        storage = ZODB.MappingStorage.MappingStorage()
        self._blob_dir = tempfile.mkdtemp()
        storage = ZODB.blob.BlobStorage(self._blob_dir, storage)
        self.db = ZODB.DB(storage)

    @property
    def root(self):
        return self.db.open().root()

    def cleanup(self):
        transaction.abort()
        shutil.rmtree(self._blob_dir)


class MockRedis(object):
    def __init__(self):
        self._store = {}

    def hget(self, hname, hkey):
        name = self._store.get(hname)
        if name is None:
            return name
        return self._store[hname].get(hkey)

    def hset(self, hname, hkey, hval):
        ret = 0
        if hname not in self._store:
            self._store[hname] = {}
            ret = 1
        name = self._store[hname]
        if hkey not in name:
            ret = 1
        name[hkey] = hval
        return ret

    def hkeys(self, hname):
        name = self._store.get(hname)
        if name is None:
            return name
        return name.keys()


def break_document_data_file(doc):
    b = doc.data_file._blob
    b._p_activate()
    os.unlink(b._p_blob_committed or b._p_blob_uncommitted)


# differentiate real and thread sleeping from sleeping inside the test
def _mysleep():
    from time import sleep as s
    sleep = s
    def inner(t):
        sleep(t)
    return inner
mysleep = _mysleep()


__all__ = [
    'setupCoreSessions',
    'setupSiteErrorLog',
    'setupZGlobals',
    'startZServer',
    'importObjectFromFile',
    'appcall',
    'mysleep',
]
