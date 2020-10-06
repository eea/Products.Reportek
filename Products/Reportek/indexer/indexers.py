from Products.Reportek.indexer import indexer
from Products.Reportek.interfaces import (ICollection, IDocument, IEnvelope,
                                          IFeedback, IReportekContent,
                                          IWorkitem)


@indexer(IReportekContent)
def dummy_released(obj):
    """ dummy to prevent indexing child objects
    """
    APPLIES = [IWorkitem, ICollection, IDocument, IFeedback]
    for i in APPLIES:
        if i.providedBy(obj):
            raise AttributeError("This field should not indexed here!")


@indexer(IEnvelope)
def envelope_released(obj):
    """
    :return: value of released
    """
    return obj.released


@indexer(IReportekContent)
def dummy_activity_id(obj):
    """ dummy to prevent indexing child objects
    """
    APPLIES = [ICollection, IDocument, IEnvelope]
    for i in APPLIES:
        if i.providedBy(obj):
            raise AttributeError("This field should not indexed here!")


# We need 2 distinct indexers here, because we can't chain the decorator and
# we get conflicting configuration if we register it for IReportekContent
@indexer(IFeedback)
def fb_activity_id(obj):
    """ return value of activity_id
    """
    return obj.activity_id


@indexer(IWorkitem)
def wk_activity_id(obj):
    """ return value of activity_id
    """
    return obj.activity_id
