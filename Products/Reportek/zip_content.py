# The contents of this file are subject to the Mozilla Public
# License Version 1.1 (the "License"); you may not use this file
# except in compliance with the License. You may obtain a copy of
# the License at http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS
# IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
# implied. See the License for the specific language governing
# rights and limitations under the License.
#
# The Original Code is Reportek version 1.0.
#
# The Initial Developer of the Original Code is European Environment
# Agency (EEA).  Portions created by Finsiel are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):
# Soren Roug, EEA
# Cornel Nitu, Finsiel Romania

from datetime import datetime
import struct
import urllib

from AccessControl import getSecurityManager
from AccessControl.Permissions import view
from Products.Reportek import constants
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED, BadZipfile
import zipfile

import RepUtils


METADATA_CONTENT = """Metadata for envelope "$envelope" at $link

Description: $description
Obligations: $obligations
Period: $period
Coverage: $coverage
Reported: $release_date
Status: $status
Files in this envelope: $documents $restricted

This archive was downloaded at $date
"""

METADATA_DOCUMENTS = """
    $id   uploaded on: $date,    size: $size"""

METADATA_RESTRICTED = """
    $id   uploaded on: $date,   size: $size  (file restricted from public view)
    """

README_CONTENT = """This directory contains the documents included in
 the envelope "$envelope" at $link.
Also contains the following files:

  metadata.txt - descriptive information about the envelope
  history.txt - log of activities executed since the envelope creation until
                the moment of the download

This archive was downloaded at $date
"""

HISTORY_HEADER = """Log history for envelope "$envelope" at $link

$history
This archive was downloaded at $date
"""

HISTORY_ACTIVITY = """
$no. Activity: $activity
   Status: $status
   User:   $user
   Eventlog: $eventlog
"""

HISTORY_ACTIVITY_EVENTS = """
            $date - $event $comment"""

AUTOMATIC_FEEDBACK_CONTENT = """
<dl>
<dt>Subject:</dt><dd>$subject</dd>
<dt>Posted automatically on:</dt><dd>$posted</dd>
<dt>Task:</dt><dd>$task</dd>
<dt>Referred file:</dt><dd>$file</dd>
<dd><span>$content</span></dd>
</dl>
"""


MANUAL_FEEDBACK_CONTENT = """
<dl>
<dt>Subject:</dt><dd>$subject</dd>
<dt>Envelope release</dt><dd>$posted</dd>
<dt>Attached files:</dt><dd>$file</dd>
<dd><span>$content</span></dd>
</dl>
"""

AUTOMATIC_FEEDBACKS_LIST = """
<dl>
<dt>Subject:</dt><dd>$subject</dd>
<dt>Posted automatically on:</dt><dd>$posted</dd>
<dt>Task:</dt><dd>$task</dd>
<dt>Referred file:</dt><dd>$file</dd>
</dl>
"""


MANUAL_FEEDBACKS_LIST = """
<dl>
<dt>Subject:</dt><dd>$subject</dd>
<dt>Envelope release</dt><dd>$posted</dd>
<dt>Attached files:</dt><dd>$file</dd>
</dl>
"""

FEEDBACK_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
    <title>$title</title>
    <style type="text/css">
    body {
        font-family:arial, verdana, sans-serif;
        font-size:0.8em;
    }
    h1 {
        color:#8be;
    }
    dl
    {
        margin: 0 0 1em 0;
        padding: 0;
    }

    dt
    {
        margin: 0;
        padding: 0;
        font-weight: bold;
    }

    dd
    {
        margin: 0 0 0.3em 0;
        padding: 0;
    }
    </style>
</head>
<body>
    <h1>$title</h1>
"""

FEEDBACK_FOOTER = """
</body>
</html>
"""


def _get_today():
    return datetime.now().isoformat(' ')

# ----------------  history log --------------------------------


def _get_user(ob):
    if ob.actor:
        return ob.actor
    return '(Not assigned)'


def get_history_content(ob):
    """ Return the history associated with this envelope.
        Example:
        |   Log history for envelope Test Envelope
        |
        |   1. Activity: Draft
        |      Route: From Start To Draft
        |      Status: complete
        |      User:   johndoe
        |      Eventlog:
        |               2005/02/24 - creation
        |               2005/02/24 - assigned to johndoe
        |               2005/02/24 - active
        |   ---
        |   [other activities]
    """

    parsed_template = RepUtils.parse_template
    i = 1
    activities = []

    for item in ob.objectValues('Workitem'):

        # first we generate the event log for each activity
        events = []
        for log in item.event_log:
            if isinstance(log['event'], unicode):
                log['event'] = log['event'].encode('utf-8')
            events.append(parsed_template(
                HISTORY_ACTIVITY_EVENTS,
                {'date': str(log['time'].ISO()),
                 'event': log['event'],
                 'comment': log['comment'],
                 }))
        log_events = ''.join(events)

        # last_activity = item.lastActivityDate().rfc822()

        # generate the activity related information
        activities.append(parsed_template(
            HISTORY_ACTIVITY,
            {'no':  i,
             'activity': item.getActivityDetails('title'),
             'status':  item.status,
             'user': _get_user(item),
             'eventlog': log_events}))
        i += 1  # increment the workitem number
    log_activities = ''.join(activities)

    # finally, generate the entire history log
    return parsed_template(
        HISTORY_HEADER,
        {'envelope': ob.title,
         'link': ob.absolute_url(),
         'history': log_activities,
         'date': _get_today()
         })

# ----------------  metadata log --------------------------------


def _get_descriptions(ob):
    if ob.descr:
        return ob.descr
    else:
        return "n/a"


def _get_engine(app):
    return getattr(app, constants.ENGINE_ID)


def _get_obligations(ob):
    res = []
    app = ob.getPhysicalRoot()
    engine = _get_engine(app)
    for uri in ob.dataflow_uris:
        df = engine.dataflow_lookup(uri)
        if df.get('terminated', '0') == '1':
            res.append("%s -- TERMINATED" % df['details_url'])
        else:
            res.append("%s" % df['details_url'])
    return ",".join(res)


def _get_period(ob):
    if ob.endyear == '':
        return "%s - %s" % (ob.year, ob.partofyear)
    return "%s to %s" % (ob.year, ob.endyear)


def _get_status(ob):
    if ob.status:
        return ob.status
    return '(No status)'


def _get_coverage(ob):
    if ob.locality:
        return "%s: %s" % (ob.getCountryName(), ob.locality)
    if not ob.getCountryName():
        return "n/a"
    return "%s" % (ob.getCountryName())


def _get_release_date(ob):
    if ob.released:
        return ob.reportingdate.ISO()  # DateTime
    else:
        return "Not released"


def _get_documents(ob):
    return [doc for doc in ob.objectValues('Report Document')]


def _get_feedbacks(ob):
    return [feedback for feedback in ob.objectValues('Report Feedback')]


def get_metadata_content(ob):
    """ Return the metadata associated with this envelope.

        Example::
            Description: some description
            Obligations: http://example.com/envelope
            Period: 1980 - Whole Year
            Coverage: Austria
            Reported: 2006-06-19 11:09:56
            Status: running
            Files in this envelope:
            |   dummy.doc   uploaded on: 16 Jun 2006,    size: 99.7 KB
            |   ----
            |   [other files]

    """
    parsed_template = RepUtils.parse_template

    # first generate the documents log
    documents = []
    restricted = []
    for doc in _get_documents(ob):
        upload_date = doc.upload_time().strftime('%d %b %Y')
        if getSecurityManager().checkPermission(view, doc):
            documents.append(parsed_template(
                METADATA_DOCUMENTS,
                {'id': doc.id,
                 'date': upload_date,
                 'size': doc.size()}))
        else:
            restricted.append(parsed_template(
                METADATA_RESTRICTED,
                {'id': doc.id,
                 'date': upload_date,
                 'size': doc.size()}))

    log_documents = ''.join(documents)
    log_restricted = ''.join(restricted)

    if log_documents == '' and log_restricted == '':
        log_documents = 'None'

    return parsed_template(
        METADATA_CONTENT,
        {'envelope': ob.title,
         'link': ob.absolute_url(),
         'description': _get_descriptions(ob),
         'obligations': _get_obligations(ob),
         'period':      _get_period(ob),
         'coverage':    _get_coverage(ob),
         'status':      _get_status(ob),
         'release_date': _get_release_date(ob),
         'documents': log_documents,
         'restricted': log_restricted,
         'date': _get_today(),
         })


def get_feedback_content(ob):
    """ Returns feedback items associated with this envelope.
        Example:

        * (for automatic feedbacks)
          Subject: Feedback item
          Posted automatically on: 09 Sep 2008
          Task: Automatic quality assessment
          Referred file: file.xml

          [ Feedback text ]

        * (for manual feedbacks)
          Subject: Feedback item
          Envelope release: 11 Sep 2008
          Attached files: file.doc

          [ Feedback text ]
    """
    parsed_template = RepUtils.parse_template
    header = parsed_template(FEEDBACK_HEADER,
                             {'title': 'Feedbacks for envelope %s' % ob.title})
    footer = parsed_template(FEEDBACK_FOOTER,
                             {})
    if ob.automatic:
        try:
            task_name = ob.getActivityDetails('title')
        except (AttributeError, KeyError):
            task_name = ob.activity_id

        if ob.document_id and ob.document_id != 'xml':
            refered_file = ob.document_id
        else:
            refered_file = ''
        content = parsed_template(
            AUTOMATIC_FEEDBACK_CONTENT,
            {'subject': ob.title,
             'posted': ob.postingdate.strftime('%d %b %Y %H:%M'),
             'task': task_name,
             'file': refered_file,
             'content': ob.feedbacktext})
    else:
        files = ['<a href="%s" title="%s">%s</a>' % (file.getId(),
                                                     'Open %s' % file.getId(
        ), file.getId()) for file in ob.objectValues(['File', 'File (Blob)'])]
        content = parsed_template(MANUAL_FEEDBACK_CONTENT,
                                  {'subject': ob.title,
                                   'posted': ob.releasedate,
                                   'file': ', '.join(files),
                                   'content': ob.feedbacktext})
    # finally, generate the entire feedback log
    return "%s%s%s" % (header, content, footer)


def get_feedback_list(ob):
    """ Returns feedback items associated with this envelope.

        Example:

            Feedbacks for envelope Test Envelope

            1. Subject: Feedback item[link]
               Posted automatically on: 09 Sep 2008
               Task: Automatic quality assessment
               Referred file: file.xml

            2. Subject: Feedback item[link]
               Envelope release: 11 Sep 2008
               Attached files: file.doc

            ...
    """
    feedbacks = []
    parsed_template = RepUtils.parse_template
    header = parsed_template(
        FEEDBACK_HEADER, {'title': 'Feedbacks for envelope %s' % ob.title})
    footer = parsed_template(FEEDBACK_FOOTER, {})
    for feedback in _get_feedbacks(ob):
        if getSecurityManager().checkPermission(view, feedback):
            files = ['<a href="%s" title="%s">%s</a>' % (
                file.getId(),
                'Open %s' % file.getId(),
                file.getId())
                for file in feedback.objectValues(['File', 'File (Blob)'])]
            if feedback.automatic:
                try:
                    task_name = feedback.getActivityDetails('title')
                except (AttributeError, KeyError):
                    task_name = feedback.activity_id

                if feedback.document_id and feedback.document_id != 'xml':
                    refered_file = feedback.document_id
                else:
                    refered_file = ''
                feedbacks.append(parsed_template(
                    AUTOMATIC_FEEDBACKS_LIST,
                    {'subject': '<a href="%s.html" title="%s">%s</a>' % (
                        feedback.id, feedback.title, feedback.title),
                     'posted': feedback.postingdate.strftime('%d %b %Y %H:%M'),
                     'task': task_name,
                     'file': refered_file}))
            else:
                feedbacks.append(parsed_template(
                    MANUAL_FEEDBACKS_LIST,
                    {'subject': '<a href="%s.html" title="%s">%s</a>' % (
                        feedback.id, feedback.title, feedback.title),
                     'posted': feedback.releasedate,
                     'file': ', '.join(files)}))
    # finally, generate the entire feedback log
    return "%s%s%s" % (header, '\n'.join(feedbacks), footer)

# ----------------  readme log --------------------------------


def get_readme_content(ob):
    """ Return the README.txt content """
    return RepUtils.parse_template(
        README_CONTENT,
        {'envelope': ob.title,
         'link': ob.absolute_url(),
         'date': _get_today(),
         })

#
# Support class to provide more similarity with Zope upload files.
# Sometimes the calling program will make a read() with a maxsize.
# This class will simply deliver what is available even if it is bigger.
# On some occasions though, the size of the content will be exactly the
# amount request and the calling function will assume that there is more
# to read. Therefore we allow only one read to work.
#


class ZZipFile(ZipFile):

    # for the __del__ mechanics (? see python2.7/zipfile.py)
    zef_file = None

    def __init__(self, file, mode="r", compression=ZIP_STORED,
                 allowZip64=False):
        ZipFile.__init__(self, file, mode=mode,
                         compression=compression, allowZip64=allowZip64)
        self.currentFilename = None
        self.zef_file = None
        self.should_close = False

    def __del__(self):
        fp = self.zef_file
        self.zef_file = None
        if self.should_close:
            self.should_close = False
            fp.close()
        ZipFile.__del__(self)

    def close(self):
        try:
            if self.should_close:
                self.zef_file.close()
        finally:
            self.zef_file = None
            self.should_close = False
            ZipFile.close(self)

    def setcurrentfile(self, filename, pwd=None):
        self.bytesRead = 0
        self.currentFilename = filename
        self.pwd = pwd
        # ZipFile does the open at read.
        # Since we always expect setcurent file to be called prior to any
        # other operation we call open/seek here
        # no need to close, every open just seeks in the same opened file.
        # see (the bloody) zipfile.py
        # zipfile always opens
        self.zef_file = self.open(self.currentFilename, pwd=self.pwd)
        if not self._filePassed:
            self.should_close = True

    def read(self, size=-1):
        # read manually from ZipExtFile
        # since the decompressor takes care of where the file inside the
        # container ends
        # (uses an intermediary _readbuffer) we don't care about reading
        # 'too much'
        return self.zef_file.read(size)

    def seek(self, pos=0):
        """ Use this only for rewind purposes, as the base class does
        not provide a seek mechanism. Thus, `pos` should always be 0."""
        if pos != 0:
            raise ValueError("(Z)ZipFile can only seek for start.")
        self.zef_file.close()
        self.zef_file = self.open(self.currentFilename, pwd=self.pwd)

    def tell(self):
        return self.getinfo(self.currentFilename).file_size


def encode_zip_name(name, key):
    return urllib.quote('%s-%s' % (name, key), '')


class ZZipFileRaw(ZZipFile):
    """ This class extends the reading of zip files inside a zip archive
    to support raw retrieving of data + necessary metadata for transplanting
    a raw deflated content from zip container to other container, say gzip.
    This is only for reading!
    """

    zef_file_raw = None
    ENCRYPTED_FLAG = 0x1
    SKIP_RAW_THRESHOLD = 300

    def __init__(self, file, mode="r", compression=ZIP_STORED,
                 allowZip64=False):
        ZZipFile.__init__(self, file, mode=mode,
                          compression=compression, allowZip64=allowZip64)
        self.bytesRead = 0
        self.zef_file_raw = None
        self.should_close_raw = False

    def __del__(self):
        fp = self.zef_file_raw
        self.zef_file_raw = None
        if self.should_close_raw:
            self.should_close_raw = False
            fp.close()
        ZZipFile.__del__(self)

    # setcurrentfile should be always called in advance
    def setcurrentfile(self, filename, pwd=None):
        ZZipFile.setcurrentfile(self, filename, pwd)
        self.zinfo = self.getinfo(self.currentFilename)
        self.allowRaw = True
        if not self.zef_file_raw:
            self.zef_file_raw = self.openRaw()
        self.rewindRaw()
        if self.zinfo.compress_type != ZIP_DEFLATED:
            self.allowRaw = False
            return
        # check if encrypted
        if self.zinfo.flag_bits & self.ENCRYPTED_FLAG:
            self.allowRaw = False
            return

    # only open for read
    def openRaw(self):
        ''' This is a nonstandard open.
        It is only for read.
        '''
        # open raw
        if not self.zef_file_raw:
            if self._filePassed:
                zef_file_raw = self.fp
                self.should_close_raw = False
            else:
                # open the main filename (the one on file system)
                zef_file_raw = open(self.filename, 'rb')
                self.should_close_raw = True

        return zef_file_raw

    def close(self):
        try:
            if self.should_close_raw:
                self.zef_file_raw.close()
        finally:
            self.zef_file_raw = None
            self.should_close_raw = None
            ZZipFile.close(self)

    @property
    def compressed_size(self):
        return self.zinfo.compress_size

    @property
    def orig_size(self):
        return self.zinfo.file_size

    @property
    def CRC(self):
        return self.zinfo.CRC

    def seekRaw(self, pos=0):
        # seek to the start of deflated data
        if pos:
            raise IOError(
                '''Can only seek at the begining of a file inside '''
                '''a zip archive (pos=0)''')
        try:
            if not self.zef_file_raw:
                self.zef_file_raw = self.openRaw()
            self.zef_file_raw.seek(self.zinfo.header_offset, 0)

            # Skip the file header:
            fheader = self.zef_file_raw.read(zipfile.sizeFileHeader)
            if len(fheader) != zipfile.sizeFileHeader:
                raise BadZipfile("Truncated file header")
            fheader = struct.unpack(zipfile.structFileHeader, fheader)
            if fheader[zipfile._FH_SIGNATURE] != zipfile.stringFileHeader:
                raise BadZipfile("Bad magic number for file header")

            fname = self.zef_file_raw.read(
                fheader[zipfile._FH_FILENAME_LENGTH])
            if fheader[zipfile._FH_EXTRA_FIELD_LENGTH]:
                self.zef_file_raw.read(fheader[zipfile._FH_EXTRA_FIELD_LENGTH])

            if fname != self.zinfo.orig_filename:
                raise BadZipfile('File name in directory "%s" and \
                    header "%s" differ.' % (self.zinfo.orig_filename, fname))
        except Exception:
            if self.should_close_raw:
                self.zef_file_raw.close()
                self.zef_file_raw = None
                self.should_close_raw = False
            raise

    def rewindRaw(self):
        return self.seekRaw(0)

    def read(self, nbytes=-1, skipRawThreshold=SKIP_RAW_THRESHOLD):
        """ Read `nbytes` from the zip file.
        If the requestet chunk size is -1 then read the whole file.
        If it is below `skipRawThreshold` (but not whole file, -1) then read
        those bytes uncompressed
        (for peeking at a part of the file, see determining content type
        in Document.py)
        The nbytes are decompressed buffer length
        In all other cases read `nbytes` of compressed data.
        If the file is not opened it will be opened for reading.
        """
        if not self.allowRaw or (0 < nbytes < skipRawThreshold):
            return ZZipFile.read(self, nbytes)

        # else fetch the raw content
        bytesLeft = self.compressed_size - self.bytesRead
        nbytes = nbytes if nbytes < bytesLeft else bytesLeft
        if not nbytes:
            return ""
        self.bytesRead += nbytes
        return self.zef_file_raw.read(nbytes)
