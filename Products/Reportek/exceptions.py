class CannotPickProcess(Exception):
    """ Used to replace deprecated raise 'CannotPickProcess' """

class NoProcessAvailable(Exception):
    """ Used to replace deprecated raise 'NoProcessAvailable' """

class InvalidPartOfYear(Exception):
    """ Raised when the Envelope part of year is not in the valid values list """

class LocalConversionException(Exception):
    """ Raised when Local Conversion Service is not responding """

class ApplicationNameException(Exception):
    """
    Raised when the new name of the application does not match an activity id
    in the current process
    """

    def __init__(self, message=None):
        super(ApplicationNameException, self).__init__(message)
