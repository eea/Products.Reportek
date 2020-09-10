from zope.interface import Attribute, Interface


class IDocument(Interface):
    """ Reportek Document."""
    id = Attribute('id')
    title = Attribute('title')
    content_type = Attribute('content_type')
    xml_schema_location = Attribute('needed for XML files')


class ICollection(Interface):
    """ Reportek Collection marker interface"""


class IBaseDelivery(Interface):
    """BaseDelivery Interface."""


class IEnvelope(Interface):
    """ Reportek Envelope."""
    id = Attribute('id')
    title = Attribute('title')
    released = Attribute('released')
    partofyear = Attribute('partofyear')
    country = Attribute('country')
    locality = Attribute('locality')
    descr = Attribute('descr')
    dataflow_uris = Attribute('dataflow_uris')
    year = Attribute('year')
    endyear = Attribute('endyear')


class IReportekEngine(Interface):
    """ Reportek Engine """
    pass


class IReportekUtilities(Interface):
    """ Reportek Utilities
    """


class IReportekAPI(Interface):
    """ Reportek API
    """


class IRegistryManagement(Interface):
    """ Registry Management
    """


class IProcess(Interface):
    """ Process marker interface
    """


class IFeedback(Interface):
    """ Feedback marker interface
    """


class IReportekContent(Interface):
    """ Marker interface for Reportek Content-ish
    """


class IWorkitem(Interface):
    """ Marker interface for workitems
    """
