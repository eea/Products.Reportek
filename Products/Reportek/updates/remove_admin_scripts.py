import transaction
from Products.Reportek.updates.migrate_scripts_from_db import (
    create_dataflow_rpc_call, create_localities_rpc_call, delete_objects,
)

__all__ = ['update']


def update(app):
    if getattr(app, 'ReportekEngine', None):
        if not getattr(app.ReportekEngine, 'xmlrpc_dataflow', None):
            app.ReportekEngine.xmlrpc_dataflow = create_dataflow_rpc_call()
            transaction.commit()
        if not getattr(app.ReportekEngine, 'xmlrpc_localities', None):
            app.ReportekEngine.xmlrpc_localities = create_localities_rpc_call()
            transaction.commit()

    objects_to_delete = ['admin']
    delete_objects(app, objects_to_delete)
