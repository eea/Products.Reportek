## Script (Python) "collectionsICanSee"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
l_ret = []
l_user = context.REQUEST.AUTHENTICATED_USER
for col in context.objectValues('Report Collection'):
    if l_user.has_permission('View', col):
        l_ret.append(col)

l_ret.sort()

return l_ret
