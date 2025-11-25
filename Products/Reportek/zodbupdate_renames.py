"""
ZODB update rename rules for obsolete Zope 2 classes.

This module defines rename rules for zodbupdate to handle migration
from Zope 2 to Zope 4, removing obsolete persistent classes.

Obsolete classes are mapped to a simple RemovedObject placeholder
that can be safely deleted later.
"""

from persistent import Persistent


class RemovedObject(Persistent):
    """Placeholder for obsolete Zope 2 classes that have been removed.

    This class is used during ZODB migration to replace references to
    obsolete classes. Objects of this type can be safely deleted later.
    """

    pass


# Format: 'old.module.path ClassName': 'new.module.path NewClassName'
RENAMES = {
    # Remove SiteRoot from Products.SiteAccess
    "Products.SiteAccess.SiteRoot SiteRoot": "Products.Reportek.zodbupdate_renames RemovedObject",
    "Products.SiteAccess.SiteRoot.SiteRoot": "Products.Reportek.zodbupdate_renames RemovedObject",
    "Products.SiteAccess.SiteRoot": "Products.Reportek.zodbupdate_renames RemovedObject",
    # Remove other obsolete Zope 2 classes
    "Products.SiteErrorLog.SiteErrorLog.SiteErrorLog": "Products.Reportek.zodbupdate_renames RemovedObject",
    "Products.TemporaryFolder.TemporaryFolder.MountedTemporaryFolder": "Products.Reportek.zodbupdate_renames RemovedObject",
    # Remove obsolete App.Product classes
    "App.Product ProductFolder": "Products.Reportek.zodbupdate_renames RemovedObject",
    "App.Product Product": "Products.Reportek.zodbupdate_renames RemovedObject",
    "App.Factory Factory": "Products.Reportek.zodbupdate_renames RemovedObject",
    "App.Permission Permission": "Products.Reportek.zodbupdate_renames RemovedObject",
    # Remove obsolete HelpSys classes
    "HelpSys.HelpSys ProductHelp": "Products.Reportek.zodbupdate_renames RemovedObject",
    "HelpSys.HelpTopic STXTopic": "Products.Reportek.zodbupdate_renames RemovedObject",
    "HelpSys.APIHelpTopic APIHelpTopic": "Products.Reportek.zodbupdate_renames RemovedObject",
    "HelpSys.APIHelpTopic APIDoc": "Products.Reportek.zodbupdate_renames RemovedObject",
    "HelpSys.APIHelpTopic MethodDoc": "Products.Reportek.zodbupdate_renames RemovedObject",
    "HelpSys.APIHelpTopic AttributeDoc": "Products.Reportek.zodbupdate_renames RemovedObject",
    # Remove obsolete ZCatalog and SearchIndex classes
    "Products.ZCatalog.Vocabulary Vocabulary": "Products.Reportek.zodbupdate_renames RemovedObject",
    "SearchIndex.GlobbingLexicon GlobbingLexicon": "Products.Reportek.zodbupdate_renames RemovedObject",
    "SearchIndex.UnTextIndex UnTextIndex": "Products.Reportek.zodbupdate_renames RemovedObject",
    "SearchIndex.UnKeywordIndex UnKeywordIndex": "Products.Reportek.zodbupdate_renames RemovedObject",
    "Products.ZCatalog.CatalogPathAwareness CatalogAware": "Products.Reportek.zodbupdate_renames RemovedObject",
    "Products.ZCatalog.CatalogPathAwareness CatalogPathAware": "Products.Reportek.zodbupdate_renames RemovedObject",
    "Products.ZCatalog CatalogPathAwareBase": "Products.Reportek.zodbupdate_renames RemovedObject",
    # Remove obsolete PluginIndexes.TextIndex classes
    "Products.PluginIndexes.TextIndex.Vocabulary Vocabulary": "Products.Reportek.zodbupdate_renames RemovedObject",
    "Products.PluginIndexes.TextIndex.GlobbingLexicon GlobbingLexicon": "Products.Reportek.zodbupdate_renames RemovedObject",
    "Products.PluginIndexes.TextIndex.TextIndex TextIndex": "Products.Reportek.zodbupdate_renames RemovedObject",
    "Products.PluginIndexes.TextIndex.Splitter.ZopeSplitter.ZopeSplitter ZopeSplitter": "Products.Reportek.zodbupdate_renames RemovedObject",
    "Products.PluginIndexes.TextIndex.Splitter.ZopeSplitter Splitter": "Products.Reportek.zodbupdate_renames RemovedObject",
    "Products.PluginIndexes.TextIndex.Lexicon Lexicon": "Products.Reportek.zodbupdate_renames RemovedObject",
    # Remove obsolete ZClasses classes
    "ZClasses.ZClass ZClass": "Products.Reportek.zodbupdate_renames RemovedObject",
    "ZClasses.ZClass ZObject": "Products.Reportek.zodbupdate_renames RemovedObject",
    "ZClasses.ZClass PersistentClass": "Products.Reportek.zodbupdate_renames RemovedObject",
    "ZClasses._pmc ZClassPersistentMetaClass": "Products.Reportek.zodbupdate_renames RemovedObject",
    "ZClasses.Property ZInstanceSheets": "Products.Reportek.zodbupdate_renames RemovedObject",
    "ZClasses.ZClass ZClassSheets": "Products.Reportek.zodbupdate_renames RemovedObject",
    "ZClasses.Method ZClassMethodsSheet": "Products.Reportek.zodbupdate_renames RemovedObject",
    "ZClasses.Property ZInstanceSheetsSheet": "Products.Reportek.zodbupdate_renames RemovedObject",
    "ZClasses.Property ZCommonSheet": "Products.Reportek.zodbupdate_renames RemovedObject",
    "ZClasses.Property ZInstanceSheet": "Products.Reportek.zodbupdate_renames RemovedObject",
    "ZClasses.Method MWp": "Products.Reportek.zodbupdate_renames RemovedObject",
    # Remove obsolete ZopeTutorial classes
    "Products.ZopeTutorial.TutorialTopic TutorialTopic": "Products.Reportek.zodbupdate_renames RemovedObject",
    "Products.ZopeTutorial.TutorialTopic GlossaryTopic": "Products.Reportek.zodbupdate_renames RemovedObject",
    # Remove obsolete ExternalMethod classes
    "Products.ExternalMethod.ExternalMethod ExternalMethod": "Products.Reportek.zodbupdate_renames RemovedObject",
    # Remove problematic DTMLFile instances that cause Python 3 unpickling errors
    "App.special_dtml DTMLFile": "Products.Reportek.zodbupdate_renames RemovedObject",
    "Globals DTMLFile": "Products.Reportek.zodbupdate_renames RemovedObject",
    "DocumentTemplate.DT_HTML DTMLFile": "Products.Reportek.zodbupdate_renames RemovedObject",
}


def renames():
    """Return rename rules for zodbupdate."""
    return RENAMES


def decode_app_before_traverse(state):
    """
    Clean up broken BeforeTraverse hooks from Application objects.

    This decode rule removes BeforeTraverse hooks that reference RemovedObjects,
    particularly the obsolete SiteRoot hooks from Products.SiteAccess.

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
                # Handle both tuple format (name, hook) and direct hook format
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

                # For NameCaller hooks, check if they reference a RemovedObject
                # This handles the case where NameCaller.name points to a RemovedObject
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
