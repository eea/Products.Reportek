# -*- coding: utf-8 -*-
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

""" Generic functions module """

import os
import sys
import re
import tempfile
import traceback
import string,base64,time
import operator
import json
import time
from path import path
from copy import deepcopy
from types import FunctionType
from urllib import FancyURLopener
from webdav.common import rfc1123_date
from AccessControl.SecurityManagement import getSecurityManager
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import setSecurityManager
from ComputedAttribute import ComputedAttribute
from DateTime import DateTime
from datetime import datetime
from Products.Reportek.config import XLS_HEADINGS
from Products.Reportek.config import ZIP_CACHE_PATH


def formatException(self, error):
     """
     Format and return the specified exception information as a string.

     This implementation builds the complete stack trace, combining
     traceback.format_exception and traceback.format_stack.
     """
     lines = traceback.format_exception(*error)
     if error[2]:
         lines[1:1] = traceback.format_stack(error[2].tb_frame.f_back)
     return ''.join(lines)

import logging
logger = logging.getLogger('Reportek.RepUtils')
#logger.setLevel(logging.DEBUG)
logging.Formatter.formatException = formatException

bad_chars = ' ,+&;()[]{}\xC4\xC5\xC1\xC0\xC2\xC3' \
    '\xE4\xE5\xE1\xE0\xE2\xE3\xC7\xE7\xC9\xC8\xCA\xCB' \
    '\xC6\xE9\xE8\xEA\xEB\xE6\xCD\xCC\xCE\xCF\xED\xEC' \
    '\xEE\xEF\xD1\xF1\xD6\xD3\xD2\xD4\xD5\xD8\xF6\xF3' \
    '\xF2\xF4\xF5\xF8\x8A\x9A\xDF\xDC\xDA\xD9\xDB\xFC' \
    '\xFA\xF9\xFB\xDD\x9F\xFD\xFF\x8E\x9E'

good_chars= '___________AAAAAA' \
    'aaaaaaCcEEEE' \
    'EeeeeeIIIIii' \
    'iiNnOOOOOOoo' \
    'ooooSssUUUUu' \
    'uuuYYyyZz'

TRANSMAP = string.maketrans(bad_chars, good_chars)

def copy_file(infile, outfile):
    """ Read binary data from infile and write it to outfile
        infile and outfile may be strings, in which case a file with that
        name is opened, or filehandles, in which case they are accessed
        directly.
    """
    if isinstance(infile, str):
        try:
            instream = open(infile, 'rb')
        except IOError:
            raise IOError, ("%s (%s)" %(self.id, infile))
        close_in = 1
    else:
        instream = infile
        close_in = 0

    if isinstance(outfile, str):
        try:
            outstream = open(outfile, 'wb')
        except IOError:
            raise IOError, ("%s (%s)" %(self.id, outfile))
        close_out = 1
    else:
        outstream = outfile
        close_out = 0

    try:
        blocksize = 2<<16
        block = instream.read(blocksize)
        outstream.write(block)
        while len(block)==blocksize:
            block = instream.read(blocksize)
            outstream.write(block)
    except IOError:
        raise IOError, ("%s (%s)" %(self.id, filename))
    if close_in: instream.close()
    if close_out: outstream.close()


def iter_file_data(in_file, chunk_size=131072):
    while True:
        chunk = in_file.read(chunk_size)
        if not chunk:
            break
        yield chunk

def read_file_chunked(in_file, chunk_size=131072):
    f = in_file.open("rb")
    while True:
        chunk = f.read(chunk_size)
        if not chunk:
            break
        yield chunk
    f.close()

def cleanup_id(name):
    """ Cleanup an id
        Should be more thorough and e.g. remove trailing dots/spaces
    """
    if type(name) is unicode:
        try:
            name = name.encode('ascii')
        except UnicodeEncodeError as e:
            name = name[:e.start].encode('ascii')
    return string.translate(name, TRANSMAP)

def generate_id(template):
    """ Generate a unique string
    """
    if template != '' and template is not None:
        template = cleanup_id(template)
    else:
        template = ''
    k = int(time.time())
    id = ''
    for x in range(4):
        id = chr(k & 0xff) + id
        k >>= 8
    id= base64.encodestring(id)
    return template + string.translate(string.lower(id),TRANSMAP,"/=\n")

def xmlEncode(p_string):
    """ Encode the XML reserved chars """
    if isinstance(p_string, unicode): l_tmp = p_string.encode('utf-8')
    else: l_tmp = str(p_string)
    l_tmp = l_tmp.replace('&', '&amp;')
    l_tmp = l_tmp.replace('<', '&lt;')
    l_tmp = l_tmp.replace('"', '&quot;')
    l_tmp = l_tmp.replace('\'', '&apos;')
    l_tmp = l_tmp.replace('>', '&gt;')
    return l_tmp

#encode to UTF-8 from user encoding
def utGMLEncode(p_str, p_str_enc):
    """ Giving a string and an encoding, returns the string encoded to UTF-8
        If no encoding is provided it will assume as input encoding UTF-8

        Also special characters that might appear in GML files are escaped
    """
    if p_str_enc == '':
        l_tmp = unicode(str(p_str), errors='replace')
    else:
         l_tmp = unicode(str(p_str),'%s' % p_str_enc, errors='replace')
    l_tmp = l_tmp.encode('utf8', 'replace')

    #xml entities
    l_tmp = l_tmp.replace('&', '&amp;')
    l_tmp = l_tmp.replace('<', '&lt;')
    l_tmp = l_tmp.replace('"', '&quot;')
    l_tmp = l_tmp.replace('\'', '&apos;')
    l_tmp = l_tmp.replace('>', '&gt;')

    #Microsoft Word entities
    l_tmp = l_tmp.replace('—', '-')
    l_tmp = l_tmp.replace('–', '-')
    l_tmp = l_tmp.replace('‘', "'")
    l_tmp = l_tmp.replace('’', "'")
    l_tmp = l_tmp.replace(' ', " ")
    l_tmp = l_tmp.replace('´', "'")
    l_tmp = l_tmp.replace('“', '&quot;')
    l_tmp = l_tmp.replace('”', '&quot;')
    l_tmp = l_tmp.replace('§', "-")
    l_tmp = l_tmp.replace('¤', " ")
    l_tmp = l_tmp.replace('«', "&quot;")
    l_tmp = l_tmp.replace('»', "&quot;")
    l_tmp = l_tmp.replace('…', "...")
    l_tmp = l_tmp.replace('•', "* ")

    return l_tmp

def asciiEncode(p_value):
    """ Gets a value and returns a string """
    if p_value is not None:
        return unicode(str(p_value), 'latin-1').encode('ascii', 'replace')
    else:
        return ''

def utRead(file):
    """ Open file on local or remote system. """
    if 'http' in file:
        opener = FancyURLopener()
        f = opener.open(file)
    else:
        f = open(file,'rb+')
    return f

def utf8Encode(p_str):
    """ encodes a string to UTF-8 """
    return p_str.encode('utf8')

def to_utf8(s):
    """ converts Unicode to UTF-8"""
    if isinstance(s, unicode):
        return s.encode('utf-8')
    else:
        return s

def utConvertToList(something):
    """ Convert to list """
    ret = something
    if not something:
        return []
    if type(something) is type(''):
        ret = [something]
    return ret

def utConvertListToLines(values):
    """ Takes a list of values and returns a value for a textarea control """
    if len(values) == 0: return ''
    else: return '\r\n'.join(values)

def utConvertLinesToList(value):
    """ Takes a value from a textarea control and returns a list of values """
    if type(value) == type([]): return value
    elif not value: return []
    else:
        values = []
        for v in value.split('\r\n'):
            if v != '': values.append(v)
    return values

def utIsSubsetOf(first_list, second_list):
    """ returns true if the first list is a subset of the second """
    for l_element in utConvertToList(first_list):
        if l_element not in second_list:
            return 0
    return 1

def utSortByAttr(p_obj_list, p_attr, p_sort_order=0):
    """ Sort a list of objects by one of the attributes """
    l_temp = map(None, map(getattr, p_obj_list, (p_attr,)*len(p_obj_list)), xrange(len(p_obj_list)), p_obj_list)
    l_temp.sort()
    if p_sort_order:
        l_temp.reverse()
    return map(operator.getitem, l_temp, (-1,)*len(l_temp))

def utSortListByAttr(p_obj_list, p_attr, p_sort_order=0):
    """ Sort a list of objects by one of the attributes """
    l_temp = map(None, (p_obj_item[p_attr] for p_obj_item in p_obj_list), p_obj_list)
    l_temp.sort()
    if p_sort_order:
        l_temp.reverse()
    return map(operator.getitem, l_temp, (-1,)*len(l_temp))

def utTruncString(s, p_size=50):
    #get a string and returns only a number of size characters
    if len(s)>p_size: return '%s...' % s[:p_size]
    else: return s

def utSortObjsListByMethod(p_list, p_method, p_desc=1):
    """Sort a list of objects by an attribute values"""
    l_len = len(p_list)
    l_temp = map(None, map(lambda x, y: getattr(x, y)(), p_list, (p_method,)*l_len), xrange(l_len), p_list)
    l_temp.sort()
    if p_desc: l_temp.reverse()
    return map(operator.getitem, l_temp, (-1,)*l_len)

def utSortByMethod(p_obj_list, p_attr, p_date, p_sort_order=0):
    """ Sort a list of objects by the result of one of their functions """
    l_temp = map(None, map(lambda x,y:getattr(x, y)(), p_obj_list, (p_attr,)*len(p_obj_list)), xrange(len(p_obj_list)), p_obj_list, (p_date,)*len(p_obj_list))
    l_temp = filter(lambda x: x[0] < x[3], l_temp)
    l_temp.sort()
    if p_sort_order:
        l_temp.reverse()
    return map(operator.getitem, l_temp, (-2,)*len(l_temp))

def utGrabFromUrl(p_url):
    """ Takes a file from a remote server """
    from urllib import URLopener
    try:
        l_opener = URLopener()
        l_file = l_opener.open(p_url)
        ctype = l_file.headers['Content-Type']
        l_opener.close()
        return (l_file.read(), ctype)
    except:
        return (None, 'text/x-unknown-content-type')

def parse_template(template, dict={}):
    """ Make some text from a template file. """
    if dict is not None:
        try:
            text = string.Template(template)
            result = text.substitute(dict)
            return to_utf8(result)
        except (TypeError, ValueError, KeyError), error:
            logger.exception(error)
            raise Exception, "An error occurred while generating this file"

def utGetTemp():
    """ return the system temp dir """
    if sys.platform == "win32":
        return os.getenv('TEMP')
    else:
        return '/tmp'

def getFilename(filename):
    """ return only the filename, removing the path """
    return filename.split('\\')[-1]

def createTempFile(p_file, p_filename=''):
    """ create a file in system temp dir """
    if hasattr(p_file, 'filename'):
        l_data = p_file.read()
        l_filename = cookId(p_file)
    else:
        l_data = p_file
        l_filename = p_filename
    file_temp = open(os.path.join(utGetTemp(), l_filename), "wb")
    file_temp.write(l_data)
    file_temp.close()

def deleteTempFile(filename):
    """ delete a file from the system temp dir """
    os.unlink(os.path.join(utGetTemp(), '%s' % filename))

def cookId(file):
    """ generate a file ID """
    if hasattr(file,'filename'):
        filename = file.filename
        id = filename[max(filename.rfind('/'),
                        filename.rfind('\\'),
                        filename.rfind(':'),
                        )+1:]
        return id
    return file

def extractURLs(s):
    """ find all the URLs from a string """
    return re.findall('(?P<url>http[s]?://[-_&;,?:~=%#+/.0-9a-zA-Z]+)', s)


class TmpFile:

    def __init__(self, data):
        self.fname = tempfile.mktemp()
        open(self.fname,'w+b').write(data)

    def __str__(self): return self.fname
    __repr__ = __str__

    def __del__(self):
        os.unlink(self.fname)


def temporary_named_copy(source_file):
    tmp_file = tempfile.NamedTemporaryFile()
    for chunk in iter_file_data(source_file):
        tmp_file.write(chunk)
    tmp_file.flush()
    return tmp_file


def http_response_with_file(request, response, data_file, content_type,
                            file_size, file_mtime):
    # HTTP If-Modified-Since header handling.
    header=request.get_header('If-Modified-Since', None)
    if header is not None:
        header=string.split(header, ';')[0]
        # Some proxies seem to send invalid date strings for this
        # header. If the date string is not valid, we ignore it
        # rather than raise an error to be generally consistent
        # with common servers such as Apache (which can usually
        # understand the screwy date string as a lucky side effect
        # of the way they parse it).
        # This happens to be what RFC2616 tells us to do in the face of an
        # invalid date.
        try:    mod_since=long(DateTime(header).timeTime())
        except: mod_since=None
        if mod_since is not None:
            last_mod = long(file_mtime)
            if last_mod > 0 and last_mod <= mod_since:
                # Set header values since apache caching will return Content-Length
                # of 0 in response if size is not set here
                response.setHeader('Last-Modified', rfc1123_date(file_mtime))
                response.setHeader('Content-Type', content_type)
                response.setHeader('Content-Length', file_size)
                response.setStatus(304)
                return

    response.setHeader('Last-Modified', rfc1123_date(file_mtime))
    response.setHeader('Content-Type', content_type)
    response.setHeader('Content-Length', file_size)

    for chunk in iter_file_data(data_file):
        response.write(chunk)


def iter_ofs_file_data(ofs_file):
    data = ofs_file.data

    if isinstance(data, str):
        yield data

    else:
        while data is not None:
            yield data.data
            data = data.next


def ofs_file_content_tmp(ofs_file):
    tmp_data = tempfile.NamedTemporaryFile()
    if ofs_file.meta_type == "File (Blob)":
        with ofs_file.data_file.open() as f:
            for chunk in iter_file_data(f):
                tmp_data.write(chunk)
    elif ofs_file.meta_type == "File":
        for chunk in iter_ofs_file_data(ofs_file):
            tmp_data.write(chunk)
    else:
        raise ValueError("Unknown meta_type %r" % ofs_file.meta_type)
    tmp_data.seek(0)
    return tmp_data


def _mime_types():
    mime_types = _load_json("mime_types.json")
    return mime_types


def extension(accepted_mime_types):
    for ext, mimes in mime_types.iteritems():
        for mime in mimes:
            if mime in accepted_mime_types:
                return ext


def _load_json(name):
    with open(os.path.join(os.path.dirname(__file__), name), "rb") as f:
        return json.load(f)


def inline_replace(x):
    x['uri'] = x['uri'].replace('eionet.eu.int', 'eionet.europa.eu')
    return x

mime_types = _mime_types()

def discard_utf8_bom(body):
    bom = '\xef\xbb\xbf'
    if body.startswith(bom):
        return body[3:]
    else:
        return body

def replace_keys(replace_items, obj):
    """
    Replace keys of a dict
    :param replace_items: dict with keys and replacements
    :param obj: dict where to replace
    :return: modified dict
    """
    if obj:
        for key, replacement in replace_items.iteritems():
            if key in obj:
                obj[replacement] = obj.pop(key)
    return obj


def fix_json_from_id(obj_original):
    """
    Replace keys from json to set the right json format, used in SatelliteRegistryManagement class
    :param obj_original: python dict
    :return: the dict in the corect format
    """
    if not obj_original:
        return {}

    obj = deepcopy(obj_original)

    # Replace keys to set the right json format
    obj = replace_keys({
        'oldcompany_account': 'Former_Company_no_2007-2010',
        'company_id': 'id',
        'representative': 'euLegalRepresentativeCompany',
        'users': 'contactPersons',
        'businessprofile': 'businessProfile',
        'undertaking_type': '@type'
    }, obj)

    # Replace legal representative format
    if obj['euLegalRepresentativeCompany']:
        obj['euLegalRepresentativeCompany'] = replace_keys({
            'vatnumber': 'vatNumber',
            'contact_last_name': 'contactPersonLastName',
            'contact_first_name': 'contactPersonFirstName',
            'contact_email': 'contactPersonEmailAddress'
        }, obj['euLegalRepresentativeCompany'])

    # Replace legal representative address format
    if obj['euLegalRepresentativeCompany']:
        obj['euLegalRepresentativeCompany']['address'] = replace_keys({
            'zipcode': 'zipCode'
        }, obj['euLegalRepresentativeCompany']['address'])

    # Replace address format
    obj['address'] = replace_keys({
        'zipcode': 'zipCode'
    }, obj['address'])

    # Replace contact persons format
    for person in obj['contactPersons']:
        replace_keys({
            'username': 'userName',
            'first_name': 'firstName',
            'last_name': 'lastName',
            'email': 'emailAddress'
        }, person)

    # Replace businessProfile
    obj['businessProfile'] = replace_keys({
        'highleveluses': 'highLevelUses'
    }, obj['businessProfile'])

    date_created = obj.get('date_created')
    if date_created:
        try:
            pr_date = datetime.strptime(date_created, '%d/%m/%Y').isoformat()
        except ValueError:
            pr_date = None

        obj['portal_registration_date'] = pr_date

    # Delete unused keys
    unused = ['country_code', 'date_created', 'date_updated', 'candidates',
              'collection_id', 'oldcompany_verified', 'oldcompany_extid']
    for key in unused:
        obj.pop(key, None)

    return obj


def write_xls_header(sheet):
    """ Write the xls header
    """
    for head in XLS_HEADINGS:
        column = XLS_HEADINGS.index(head)
        sheet.write(0, column, head[0])
        yield head[1], column


def write_xls_data(data, sheet, header, row):
    """ Write data to sheet
    """
    for key in header.keys():
        value = data.get(key)
        if isinstance(value, list):
            value = ",".join(value)
            if len(value) > 32000:
                value = (value[:32000] + '..') if len(value) > 32000 else value
        sheet.write(row, header.get(key), value)


def manage_as_owner(func):
    """Decorator to be used by Applications to call methods as
       owner.
    """
    def inner(*args, **kwargs):
        user_id = args[0].REQUEST['AUTHENTICATED_USER'].getUserName()
        if user_id != 'Anonymous User':
            smanager = getSecurityManager()
            owner = args[0].getOwner()
            newSecurityManager(args[0].REQUEST, owner)
            res = func(*args, **kwargs)
            setSecurityManager(smanager)
            return res
    return inner


def get_zip_cache():
    zc_path = ZIP_CACHE_PATH or CLIENT_HOME
    zip_cache = path(zc_path)/'zip_cache'
    if not zip_cache.isdir():
        zip_cache.mkdir()

    return zip_cache


def cleanup_zip_cache(days=7):
    """Cleanup the zip_cache"""
    zip_cache = get_zip_cache()
    removed = []
    # 60 minutes limit for temp files
    t_limit = time.time() - 3600
    # days limit for zip files
    z_limit = time.time() - int(days) * 86400
    for f in os.listdir(zip_cache):
        file_path = os.path.join(zip_cache, f)
        delete = os.stat(file_path).st_mtime < z_limit
        l_msg = 'Automatically removed file {} because '\
                'it was older than {} days'.format(f, days)
        if f.endswith('.temp'):
            delete = os.stat(file_path).st_mtime < t_limit
            l_msg = 'Automatically removed orphaned temp file {}'.format(f)
        if delete:
            try:
                os.unlink(file_path)
                removed.append(f)
                logger.info(l_msg)
            except OSError as e:
                logger.warning('Unable to remove file: {} ({})'.format(f,
                                                                       str(e)))
    return removed


class RemoteApplicationException(Exception):
    """Our own Remote Application exception."""
    pass
