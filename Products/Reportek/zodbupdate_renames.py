"""ZODB update rename rules for obsolete Zope 2 classes.

This module defines rename rules for zodbupdate to handle migration
from Zope 2 to Zope 4, removing obsolete persistent classes.

Obsolete classes are mapped to a simple RemovedObject placeholder
that can be safely deleted later.
"""

from persistent import Persistent

# Shorthand for the replacement class path
_REMOVED = "Products.Reportek.zodbupdate_renames RemovedObject"


class RemovedObject(Persistent):
    """Placeholder for obsolete Zope 2 classes that have been removed.

    This class is used during ZODB migration to replace references to
    obsolete classes. Objects of this type can be safely deleted later.
    """

    pass


# Format: 'old.module.path ClassName': 'new.module.path NewClassName'
RENAMES = {
    # Remove SiteRoot from Products.SiteAccess
    "Products.SiteAccess.SiteRoot SiteRoot": _REMOVED,
    "Products.SiteAccess.SiteRoot.SiteRoot": _REMOVED,
    "Products.SiteAccess.SiteRoot": _REMOVED,
    # Remove other obsolete Zope 2 classes
    "Products.SiteErrorLog.SiteErrorLog.SiteErrorLog": _REMOVED,
    "Products.TemporaryFolder.TemporaryFolder.MountedTemporaryFolder": (_REMOVED),
    # Remove obsolete App.Product classes
    "App.Product ProductFolder": _REMOVED,
    "App.Product Product": _REMOVED,
    "App.Factory Factory": _REMOVED,
    "App.Permission Permission": _REMOVED,
    # Remove obsolete HelpSys classes
    "HelpSys.HelpSys ProductHelp": _REMOVED,
    "HelpSys.HelpTopic STXTopic": _REMOVED,
    "HelpSys.APIHelpTopic APIHelpTopic": _REMOVED,
    "HelpSys.APIHelpTopic APIDoc": _REMOVED,
    "HelpSys.APIHelpTopic MethodDoc": _REMOVED,
    "HelpSys.APIHelpTopic AttributeDoc": _REMOVED,
    # Remove obsolete ZCatalog and SearchIndex classes
    "Products.ZCatalog.Vocabulary Vocabulary": _REMOVED,
    "SearchIndex.GlobbingLexicon GlobbingLexicon": _REMOVED,
    "SearchIndex.UnTextIndex UnTextIndex": _REMOVED,
    "SearchIndex.UnKeywordIndex UnKeywordIndex": _REMOVED,
    "Products.ZCatalog.CatalogPathAwareness CatalogAware": _REMOVED,
    "Products.ZCatalog.CatalogPathAwareness CatalogPathAware": _REMOVED,
    "Products.ZCatalog CatalogPathAwareBase": _REMOVED,
    # Remove obsolete PluginIndexes.TextIndex classes
    "Products.PluginIndexes.TextIndex.Vocabulary Vocabulary": _REMOVED,
    "Products.PluginIndexes.TextIndex.GlobbingLexicon GlobbingLexicon": (_REMOVED),
    "Products.PluginIndexes.TextIndex.TextIndex TextIndex": _REMOVED,
    "Products.PluginIndexes.TextIndex.Splitter.ZopeSplitter.ZopeSplitter "
    "ZopeSplitter": _REMOVED,
    "Products.PluginIndexes.TextIndex.Splitter.ZopeSplitter Splitter": (_REMOVED),
    "Products.PluginIndexes.TextIndex.Lexicon Lexicon": _REMOVED,
    # Remove obsolete ZClasses classes
    "ZClasses.ZClass ZClass": _REMOVED,
    "ZClasses.ZClass ZObject": _REMOVED,
    "ZClasses.ZClass PersistentClass": _REMOVED,
    "ZClasses._pmc ZClassPersistentMetaClass": _REMOVED,
    "ZClasses.Property ZInstanceSheets": _REMOVED,
    "ZClasses.ZClass ZClassSheets": _REMOVED,
    "ZClasses.Method ZClassMethodsSheet": _REMOVED,
    "ZClasses.Property ZInstanceSheetsSheet": _REMOVED,
    "ZClasses.Property ZCommonSheet": _REMOVED,
    "ZClasses.Property ZInstanceSheet": _REMOVED,
    "ZClasses.Method MWp": _REMOVED,
    # Remove obsolete ZopeTutorial classes
    "Products.ZopeTutorial.TutorialTopic TutorialTopic": _REMOVED,
    "Products.ZopeTutorial.TutorialTopic GlossaryTopic": _REMOVED,
    # Remove obsolete ExternalMethod classes
    "Products.ExternalMethod.ExternalMethod ExternalMethod": _REMOVED,
    # Remove problematic DTMLFile instances
    # (these cause Python 3 unpickling errors)
    "App.special_dtml DTMLFile": _REMOVED,
    "Globals DTMLFile": _REMOVED,
    "DocumentTemplate.DT_HTML DTMLFile": _REMOVED,
}


def renames():
    """Return rename rules for zodbupdate."""
    return RENAMES


def decode_app_before_traverse(state):
    """
    Clean up broken BeforeTraverse hooks from Application objects.

    This decode rule removes BeforeTraverse hooks that reference
    RemovedObjects, particularly the obsolete SiteRoot hooks from
    Products.SiteAccess.

    Returns True if the state was modified, False otherwise.
    """
    if not isinstance(state, dict):
        return False

    modified = False

    # Check for __before_traverse__ attribute
    if "__before_traverse__" in state:
        bt = state["__before_traverse__"]

        if isinstance(bt, dict):
            # Remove hooks that reference RemovedObject
            hooks_to_remove = []

            for priority, value in list(bt.items()):
                # Handle both tuple format (name, hook) and direct hook
                if isinstance(value, tuple) and len(value) == 2:
                    name, hook = value
                else:
                    # Value is the hook itself
                    hook = value

                # Check if hook is a RemovedObject
                if isinstance(hook, RemovedObject):
                    hooks_to_remove.append(priority)
                # Check by class name in case it's not loaded yet
                elif hasattr(hook, "__class__"):
                    class_name = hook.__class__.__name__
                    if class_name == "RemovedObject":
                        hooks_to_remove.append(priority)

                # For NameCaller hooks, check if they reference a
                # RemovedObject. This handles the case where
                # NameCaller.name points to a RemovedObject
                if (
                    hasattr(hook, "__class__")
                    and hook.__class__.__name__ == "NameCaller"
                ):
                    if hasattr(hook, "name"):
                        # Mark for removal if it's trying to call SiteRoot
                        # (which was converted to RemovedObject)
                        if hook.name == "SiteRoot":
                            hooks_to_remove.append(priority)

            # Remove the broken hooks
            for priority in hooks_to_remove:
                del bt[priority]
                modified = True

            # If __before_traverse__ is now empty, remove it entirely
            if not bt and "__before_traverse__" in state:
                del state["__before_traverse__"]
                modified = True

    return modified


# Decode rules: these are applied to object state during unpickling
# Format: (module, classname): [decode_function, ...]
DECODES = {
    ("OFS.Application", "Application"): [decode_app_before_traverse],
}


def decodes():
    """Return decode rules for zodbupdate."""
    return DECODES
