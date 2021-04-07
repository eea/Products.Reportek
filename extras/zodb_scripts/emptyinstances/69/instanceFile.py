# Script (Python) "instanceFile"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=Empty instance for the Sewage Sludge Directive 86/278
##
l_parent = context.xmlexports.sewagesludge  # noqa: F821
l_file = getattr(l_parent, 'emptyinstance_86278.xml')
return l_file  # noqa: F999
