topparent_id = obj.absolute_url(1).split('/')[0]
return getattr(context.restrictedTraverse('/'), topparent_id)
