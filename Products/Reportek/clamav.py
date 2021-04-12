import logging
import os
import time

import clamd
import requests
from OFS.SimpleItem import SimpleItem
from Products.Reportek.exceptions import UploadValidationException

logger = logging.getLogger(__name__)


class AVService(SimpleItem):
    """AV Service"""

    def __init__(self, clamav_rest_host=None, clamd_host=None,
                 clamd_port=3310, clamd_timeout=None, clam_max_file_size=None):
        self.clamav_rest_host = clamav_rest_host
        self.clamd_host = clamd_host
        self.clamd_port = clamd_port
        self.clamd_timeout = clamd_timeout
        self.clam_max_file_size = clam_max_file_size
        self.clamd = None
        self.scanning = None
        if clamav_rest_host:
            self.scanning = 'rest'
        elif clamd_host:
            self.scanning = 'clamd'
            self.clamd = clamd.ClamdNetworkSocket(host=self.clamd_host,
                                                  port=self.clamd_port,
                                                  timeout=self.clamd_timeout)

    def get_size(self, file):
        try:
            file.seek(0, os.SEEK_END)
        except Exception:
            # Zip files can't seek to end
            file.seek(0)
        size = file.tell()
        file.seek(0)

        return size

    def get_filename(self, file):
        f_name = getattr(file, 'filename', None)
        if not f_name:
            f_name = getattr(file, 'currentFilename', 'n/a')

        return f_name

    def is_file_like(self, obj):
        return hasattr(obj, 'read') and hasattr(obj, 'seek')

    def scan(self, file, filesize=None, filename=None):
        if self.is_file_like(file):
            file.seek(0)
            result = None
            v_found = False

            if not filesize:
                filesize = self.get_size(file)

            if not filename:
                filename = self.get_filename(file)

            if self.clam_max_file_size and filesize <= self.clam_max_file_size:
                if self.scanning == 'rest':
                    try:
                        result = self._check_file_rest(file)
                    except requests.exceptions.RequestException as e:
                        logger.error(
                            'Unable to establish connection with the clamav rest service: {}'.format(str(e)))
                    if result and 'Everything ok : true' not in result.text:
                        log_message = 'Virus found in the file "{}"'.format(
                            filename)
                        v_found = True
                elif self.scanning == 'clamd':
                    try:
                        result = self._check_file_clamd(file)
                    except Exception as e:
                        logger.error(
                            'Connection to ClamD was lost: {}'.format(str(e)))
                    if result and result.get('stream')[0] == 'FOUND':
                        sig = result.get('stream')[1]
                        log_message = 'Virus found: "{}" in the file "{}"'.format(
                            sig, filename)
                        v_found = True
                file.seek(0)
                if v_found:
                    logger.error(log_message)
                    raise UploadValidationException(log_message)

    def _check_file_clamd(self, file, checks=0):
        """Check file with clamd server"""
        try:
            return self.clamd.instream(file)
        except Exception:
            checks += 1
            if checks == 3:
                raise
            time.sleep(0.5)
            file.seek(0)
            return self._check_file_clamd(file, checks)

    def _check_file_rest(self, file, checks=0):
        """POST the file to the clamav-rest service"""
        files = {'file': file.read()}
        data = {'name': getattr(file, 'filename', 'file')}
        try:
            return requests.post('http://%s:8080/scan' % self.clamav_rest_host,
                                 files=files, data=data)
        except requests.exceptions.RequestException:
            checks += 1
            if checks == 3:
                raise
            time.sleep(0.5)
            file.seek(0)
            return self._check_file_rest(file, checks)
