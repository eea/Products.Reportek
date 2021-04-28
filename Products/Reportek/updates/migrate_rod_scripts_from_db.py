from Products.Reportek.XMLRPCMethod import XMLRPCMethod
import transaction

__all__ = ['update']


def create_dataflow_rpc_call():
    return XMLRPCMethod(
        title='Get activities from ROD',
        url='http://rod.eionet.europa.eu/rpcrouter',
        method_name='WebRODService.getActivities',
        timeout=10.0
    )


def create_localities_rpc_call():
    return XMLRPCMethod(
        title='Get countries from ROD',
        url='http://rod.eionet.europa.eu/rpcrouter',
        method_name='WebRODService.getCountries',
        timeout=5.0
    )


def delete_objects(app, objects):
    for obj in objects:
        if getattr(app, obj, None):
            app._delObject(obj, suppress_events=True)
            transaction.commit()


def update(app):
    if getattr(app, 'ReportekEngine', None):
        if not getattr(app.ReportekEngine, 'xmlrpc_dataflow', None):
            app.ReportekEngine.xmlrpc_dataflow = create_dataflow_rpc_call()
            transaction.commit()
        if not getattr(app.ReportekEngine, 'xmlrpc_localities', None):
            app.ReportekEngine.xmlrpc_localities = create_localities_rpc_call()
            transaction.commit()

    objects_to_delete = ['dataflow_rod', 'dataflow_dict', 'dataflow_table',
                         'dataflow_lookup', 'localities_rod',
                         'localities_dict', 'localities_iso_dict',
                         'localities_table', 'recent_etc']
    delete_objects(app, objects_to_delete)
