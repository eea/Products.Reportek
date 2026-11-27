import logging
import os
import time

import clamd
import requests
from OFS.SimpleItem import SimpleItem
from Products.Reportek.exceptions import UploadValidationException

logger = logging.getLogger(__name__)

# What happens to a file that could not be scanned: "open" accepts it, "closed"
# refuses the upload; either way it is logged
FAIL_OPEN = "open"
FAIL_CLOSED = "closed"
# clamd's own limit (StreamMaxLength, MaxFileSize) in the deployed ClamAV
DEFAULT_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024


def fail_mode():
    mode = os.environ.get("CLAMAV_FAIL_MODE", FAIL_OPEN).strip().lower()
    return FAIL_CLOSED if mode == FAIL_CLOSED else FAIL_OPEN


class AVService(SimpleItem):
    """AV Service"""

    def __init__(
        self,
        clamav_rest_host=None,
        clamd_host=None,
        clamd_port=3310,
        clamd_timeout=None,
        clam_max_file_size=None,
    ):
        self.clamav_rest_host = clamav_rest_host
        self.clamd_host = clamd_host
        self.clamd_port = clamd_port
        self.clamd_timeout = clamd_timeout
        self.clam_max_file_size = clam_max_file_size
        self.clamd = None
        self.scanning = None
        if clamav_rest_host:
            self.scanning = "rest"
        elif clamd_host:
            self.scanning = "clamd"
            self.clamd = clamd.ClamdNetworkSocket(
                host=self.clamd_host, port=self.clamd_port, timeout=self.clamd_timeout
            )

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
        f_name = getattr(file, "filename", None)
        if not f_name:
            f_name = getattr(file, "currentFilename", "n/a")

        return f_name

    def is_file_like(self, obj):
        return hasattr(obj, "read") and hasattr(obj, "seek")

    def scan(self, file, filesize=None, filename=None):
        """Refuse a file with a virus (UploadValidationException).

        A file that could not be scanned (the scanner cannot be reached or
        reports an error, or the file is bigger than clam_max_file_size) is
        accepted or refused as CLAMAV_FAIL_MODE says, and logged either way.
        Without a scanner configured nothing is scanned."""
        if not self.is_file_like(file) or not self.scanning:
            return
        file.seek(0)
        if not filesize:
            filesize = self.get_size(file)
        if not filename:
            filename = self.get_filename(file)

        max_size = getattr(self, "clam_max_file_size", None)
        if max_size and filesize > max_size:
            return self._not_scanned(
                filename,
                "it is bigger than %d bytes" % max_size,
                "The file is too big to be scanned for viruses.",
            )
        try:
            if self.scanning == "rest":
                status, detail = self._verdict_rest(self._check_file_rest(file))
            else:
                status, detail = self._verdict_clamd(self._check_file_clamd(file))
        except Exception as e:
            logger.exception("The virus scanner could not be reached")
            status, detail = "ERROR", "the scanner could not be reached (%s)" % e
        finally:
            file.seek(0)

        if status == "FOUND":
            log_message = 'Virus found: "{}" in the file "{}"'.format(detail, filename)
            logger.error(log_message)
            raise UploadValidationException(log_message)
        if status != "OK":
            return self._not_scanned(
                filename,
                detail,
                "The virus scanner is not available; please try again later.",
            )

    @staticmethod
    def _verdict_clamd(result):
        """(status, detail) of clamd's answer: OK, FOUND or ERROR"""
        if not result or "stream" not in result:
            return "ERROR", "the scanner gave no answer"
        status, reason = result["stream"]
        if status in ("OK", "FOUND"):
            return status, reason
        return "ERROR", "the scanner answered %s %s" % (status, reason)

    @staticmethod
    def _verdict_rest(response):
        if response is None or response.status_code != 200:
            code = getattr(response, "status_code", None)
            return "ERROR", "the scanner answered HTTP %s" % code
        if "Everything ok : true" in response.text:
            return "OK", None
        return "FOUND", "reported by the REST scanner"

    def _not_scanned(self, filename, reason, user_message):
        """A file that could not be scanned: accept it or refuse it."""
        message = 'The file "%s" was not scanned for viruses: %s' % (filename, reason)
        if fail_mode() == FAIL_CLOSED:
            logger.error(message + "; the upload is refused")
            raise UploadValidationException(user_message)
        logger.error(message + "; the upload is accepted")

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
        files = {"file": file.read()}
        data = {"name": getattr(file, "filename", "file")}
        try:
            return requests.post(
                "http://%s:8080/scan" % self.clamav_rest_host, files=files, data=data
            )
        except requests.exceptions.RequestException:
            checks += 1
            if checks == 3:
                raise
            time.sleep(0.5)
            file.seek(0)
            return self._check_file_rest(file, checks)
