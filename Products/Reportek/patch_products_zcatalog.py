def patched_manage_beforeDelete(self, item, container):
    self.unindex_object()
