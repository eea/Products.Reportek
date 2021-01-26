import logging
import os

import requests
from Products.Reportek.exceptions import UploadValidationException

logger = logging.getLogger(__name__)


def check_file(file):
    """POST the file to the clamav-rest service"""
    clamav_host = os.environ.get('CLAMAV_HOST')
    if clamav_host:
        files = {'file': getattr(file, 'filename', 'file')}
        data = {'name': getattr(file, 'filename', 'file')}
        response = requests.post('http://%s:8080/scan' % clamav_host,
                                 files=files, data=data)

        if 'Everything ok : true' not in response.text:
            logger.info('File %s is dangerous, preventing upload' % file.name)
            raise UploadValidationException('Virus found in the file')
