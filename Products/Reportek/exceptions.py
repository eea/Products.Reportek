class CannotPickProcess(Exception):
    """ Used to replace deprecated raise 'CannotPickProcess' """

class NoProcessAvailable(Exception):
    """ Used to replace deprecated raise 'NoProcessAvailable' """

class InvalidPartOfYear(Exception):
    """ Raised when the Envelope part of year is not in the valid values list """

class LocalConversionException(Exception):
    """ Raised when Local Conversion Service is not responding """
