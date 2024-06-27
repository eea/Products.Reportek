from zope.interface import Attribute, Interface
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.interface.interfaces import IObjectEvent


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
    id = Attribute('id')
    activity_id = Attribute('activity_id')
    event_log = Attribute('event_log')
    status = Attribute('status')


class IQAApplication(Interface):
    """ Marker interface for QA Applications
    """


class IWkMetadata(IAttributeAnnotatable):
    """ Marker interface for metadata wk """

class IFeedbackHistory(IAttributeAnnotatable):
    """ Marker interface for feedback history """

class IEnvelopeEvent(IObjectEvent):
    """ All Envelope events should inherit from this """


class IEnvelopeReleasedEvent(IEnvelopeEvent):
    """An envelope was released thrown"""


class IEnvelopeUnReleasedEvent(IEnvelopeEvent):
    """An envelope was unreleased thrown"""


class IIndexing(Interface):
    """ interface for indexing operations, used both for the queue and
        the processors, which perform the actual indexing;  the queue gets
        registered as a utility while the processors (portal catalog, solr)
        are registered as named utilties """

    def index(obj, attributes=None):
        """ queue an index operation for the given object and attributes """

    def reindex(obj, attributes=None):
        """ queue a reindex operation for the given object and attributes """

    def unindex(obj):
        """ queue an unindex operation for the given object """


class IIndexQueue(IIndexing):
    """ a queue for storing and optimizing indexing operations """

    def setHook(hook):
        """ set the hook for the transaction manager;  this hook must be
            called whenever an indexing operation is added to the queue """

    def getState():
        """ get the state of the queue, i.e. its contents """

    def setState(state):
        """ set the state of the queue, i.e. its contents """

    def process():
        """ process the contents of the queue, i.e. start indexing;
            returns the number of processed queue items """

    def clear():
        """ clear the queue's contents in an ordered fashion """


class IIndexQueueProcessor(IIndexing):
    """ a queue processor, i.e. an actual implementation of index operations
        for a particular search engine, e.g. the catalog, solr etc """

    def begin():
        """ called before processing of the queue is started """

    def commit():
        """ called after processing of the queue has ended """

    def abort():
        """ called if processing of the queue needs to be aborted """


class IPortalCatalogQueueProcessor(IIndexQueueProcessor):
    """ an index queue processor for the standard portal catalog via
        the `CatalogMultiplex` and `CMFCatalogAware` mixin classes """


class InvalidQueueOperation(Exception):
    pass


class IReportekCatalog(Interface):

    # searchResults inherits security assertions from ZCatalog.
    def searchResults(**kw):
        """ Decorate ZCatalog.searchResults() with extra arguments

        o The extra arguments that the results to what the user would be
          allowed to see.
        """

    # __call__ inherits security assertions from ZCatalog.
    def __call__(**kw):
        """Alias for searchResults().
        """

    def unrestrictedSearchResults(REQUEST=None, **kw):
        """Calls ZCatalog.searchResults() without any CMF-specific processing.

        o Permission:  Private (Python only)
        """

    def indexObject(object):
        """ Add 'object' to the catalog.

        o Permission:  Private (Python only)
        """

    def unindexObject(object):
        """ Remove 'object' from the catalog.

        o Permission:  Private (Python only)
        """

    def reindexObject(object, idxs=[], update_metadata=True):
        """ Update 'object' in catalog.

        o 'idxs', if passed, is a list of specific indexes to update
          (by default, all indexes are updated).

        o If 'update_metadata' is True, then update the metadata record
          in the catalog as well.

        o Permission:  Private (Python only)
        """


class IReportekCatalogAware(Interface):

    """ Interface for notifying the catalog tool.
    """

    def indexObject():
        """ Index the object in the portal catalog.
        """

    def unindexObject():
        """ Unindex the object from the portal catalog.
        """

    def reindexObject(idxs=[]):
        """ Reindex the object in the portal catalog.

        If idxs is present, only those indexes are reindexed. The metadata is
        always updated.

        Also update the modification date of the object, unless specific
        indexes were requested.
        """

    def reindexObjectSecurity(skip_self=False):
        """ Reindex security-related indexes on the object.

        Recurses in the children to reindex them too.

        If skip_self is True, only the children will be reindexed. This is a
        useful optimization if the object itself has just been fully
        reindexed, as there's no need to reindex its security twice.
        """
