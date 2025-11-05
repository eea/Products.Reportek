from App.special_dtml import DTMLFile
from Acquisition import ExplicitAcquirer
import logging

logger = logging.getLogger('Products.Reportek')

def patch_dtmlfile():
    """Patch DTMLFile to use object.__new__ instead of ExplicitAcquirer.__new__"""
    try:
        old_new = DTMLFile.__new__
        def safe_new(cls, *args, **kwargs):
            return object.__new__(cls)
        DTMLFile.__new__ = staticmethod(safe_new)
        logger.info("Successfully patched DTMLFile.__new__")
    except Exception as e:
        logger.error("Failed to patch DTMLFile.__new__: %s", str(e))

# Apply the patch immediately when this module is imported
patch_dtmlfile()

