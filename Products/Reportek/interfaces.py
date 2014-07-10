from zope.interface import Interface, Attribute

class IDocument(Interface):
    """ Reportek Document."""
    id = Attribute('id')
    title = Attribute('title')
    content_type = Attribute('content_type')
    xml_schema_location = Attribute('needed for XML files')

class IEnvelope(Interface):
    """ Reportek Envelope."""
    id = Attribute('id')
    title = Attribute('title')
    released = Attribute('released')
    partofyear= Attribute('partofyear')
    country= Attribute('country')
    locality= Attribute('locality')
    descr= Attribute('descr')
    dataflow_uris = Attribute('dataflow_uris')
    year = Attribute('year')
    endyear = Attribute('endyear')

class IReportekEngine(Interface):
    """ Reportek Engine """
    pass


class IReportekUtilities(Interface):
    """ Reportek Utilities
    """
