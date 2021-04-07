# Script (Python) "top_collection"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=obj
# title=Retrieves the top collection of an collection or envelope
##
topparent_id = obj.absolute_url(1).split('/')[0]  # noqa: F821
return getattr(context.restrictedTraverse('/'), topparent_id)  # noqa: F999
