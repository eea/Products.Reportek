class CannotPickProcess(Exception):
    """ Used to replace deprecated raise 'CannotPickProcess' """


class NoProcessAvailable(Exception):
    """ Used to replace deprecated raise 'NoProcessAvailable' """


class InvalidPartOfYear(Exception):
    """ Raised when the Envelope part of year is not in the valid values list
    """


class LocalConversionException(Exception):
    """ Raised when Local Conversion Service is not responding """


class EnvelopeReleasedException(Exception):
    """ Raised by saveXML when the Envelope is released and the document
        cannot be saved.
    """


class ApplicationException(Exception):
    """Raised when an Zope Python Application fails"""


class UploadValidationException(Exception):
    """Raised when a file contains a virus"""
