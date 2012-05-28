## Script (Python) "update_document_schema"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
print "Documents found and updated:"
for item in context.Catalog.searchResults({'meta_type':'Report Document'}):
    obj = context.Catalog.getobject(item.data_record_id_)
    try:
        obj.update_schema()
        print "%s - done" % obj.absolute_url(1)
    except:
        print "%s - error" % obj.absolute_url(1)
return printed
