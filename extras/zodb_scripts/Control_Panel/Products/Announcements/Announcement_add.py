## Script (Python) "Announcement_add"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=redirect=1
##title=Announcement constructor
##
# Add a new instance of the ZClass
request = context.REQUEST
request.set('released', 1)
instance = container.Announcement.createInObjectManager(request['id'], request)


instance.propertysheets.Basic.manage_editProperties(request)
#instance.reindex_object()
# *****************************************************************

if redirect:
    # redirect to the management view of the instance's container
    request.RESPONSE.redirect(instance.aq_parent.absolute_url() + '/manage_main')
else:
    # If we aren't supposed to redirect (ie, we are called from a script)
    # then just return the ZClass instance to the caller
    return instance
