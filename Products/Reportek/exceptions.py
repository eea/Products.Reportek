from ZPublisher.HTTPResponse import status_codes


class CannotPickProcess(Exception):
    """Used to replace deprecated raise 'CannotPickProcess'"""


class NoProcessAvailable(Exception):
    """Used to replace deprecated raise 'NoProcessAvailable'"""


class InvalidPartOfYear(Exception):
    """Raised when the Envelope part of year is not in the valid values list"""


class LocalConversionException(Exception):
    """Raised when Local Conversion Service is not responding"""


class EnvelopeReleasedException(Exception):
    """Raised by saveXML when the Envelope is released and the document
    cannot be saved.
    """


class ApplicationException(Exception):
    """Raised when an Zope Python Application fails"""


class UploadValidationException(Exception):
    """Raised when an upload is refused: a virus, a file that could not be
    scanned, a zip file bigger once unpacked than it says"""


# Zope takes the status of an error from the name of its class: answer this
# one with 400 (Bad Request), not 500
status_codes[UploadValidationException.__name__.lower()] = 400
