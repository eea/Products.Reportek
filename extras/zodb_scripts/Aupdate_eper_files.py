# Script (Python) "Aupdate_eper_files"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
for xo in context.Catalog(meta_type='Report Document', xml_schema_location='eper.xsd'):
    x = xo.getObject()
    print x.absolute_url()

    x.manage_editDocument(
        title=x.title, xml_schema_location='http://dd.eionet.europa.eu/schemas/eper/eper.xsd')
    print x.xml_schema_location

return printed
