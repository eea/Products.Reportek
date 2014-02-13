## Script (Python) "test_is_blocked"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
print context.getMySelf()
if context.is_blocked:
    print 'IS BLOCKED'
else:
    print 'is NOT BLOCKED'
return printed
