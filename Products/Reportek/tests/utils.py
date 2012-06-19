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
import tempfile
import shutil
from StringIO import StringIO
import transaction
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
    def getPhysicalPath(self):
        return ('',)
    def getPhysicalRoot(self):
        return self


def create_fake_root():
    return FakeRootObject()


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


def publish_view(view, environ={}):
    from ZPublisher.Publish import publish
    from AccessControl.SecurityManagement import noSecurityManager

    name = view.__name__
    new_environ = {
        'PATH_INFO': '/' + name,
        '_stdout': StringIO(),
    }
    new_environ.update(environ)

    root = create_fake_root()
    request = makerequest(root, new_environ['_stdout'], new_environ).REQUEST
    root.__allow_groups__ = Mock()
    view.__doc__ = 'non-empty documentation'
    setattr(root, name, view)

    try:
        with patch('Zope2.bobo_application', root):
            return publish(request, 'Zope2', [None])
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


def add_document(envelope, upload_file):
    from Products.Reportek.Document import manage_addDocument
    with patch.object(envelope, 'REQUEST', create=True) as mock_request:
        mock_request.physicalPathToVirtualPath = lambda x: x
        doc_id = manage_addDocument(envelope, file=upload_file)
    return envelope[doc_id]


def break_document_data_file(doc):
    doc._deletefile(doc.physicalpath())


__all__ = [
    'setupCoreSessions',
    'setupSiteErrorLog',
    'setupZGlobals',
    'startZServer',
    'importObjectFromFile',
    'appcall',
]
