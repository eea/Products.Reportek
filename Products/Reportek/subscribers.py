"""Event subscribers
"""


def handle_env_status_changed(obj, event):
    if obj.status == 'complete':
        for node in obj.objectValues():
            if node.meta_type == 'Report Feedback':
                for subnode in node.objectValues():
                    if subnode.meta_type == 'File (Blob)':
                        node.unrestrictFileAttachment(subnode.getId())
