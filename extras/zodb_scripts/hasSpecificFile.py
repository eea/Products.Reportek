# flake8: noqa
# Script (Python) "hasSpecificFile"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=schema
# title=Check if an envelope has an XML file with certain schema
##
# Check if an envelope has an XML file with certain schema
hasfile = 0
for f in context.objectValues('Report Document'):
    if f.xml_schema_location == schema:
        hasfile = 1
print hasfile
return int(printed)
