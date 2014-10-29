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


def update(app):
    if getattr(app, 'ReportekEngine', None):
        if not getattr(app.ReportekEngine, 'xmlrpc_dataflow', None):
            app.ReportekEngine.xmlrpc_dataflow = create_dataflow_rpc_call()
            transaction.commit()
        if not getattr(app.ReportekEngine, 'xmlrpc_localities', None):
            app.ReportekEngine.xmlrpc_localities = create_localities_rpc_call()
            transaction.commit()

    if getattr(app, 'dataflow_rod', None):
        app._delObject("dataflow_rod", suppress_events=True)
        transaction.commit()

    if getattr(app, 'dataflow_dict', None):
        app._delObject("dataflow_dict", suppress_events=True)
        transaction.commit()

    if getattr(app, 'dataflow_table', None):
        app._delObject("dataflow_table", suppress_events=True)
        transaction.commit()

    if getattr(app, 'dataflow_lookup', None):
        app._delObject("dataflow_lookup", suppress_events=True)
        transaction.commit()

    if getattr(app, 'localities_rod', None):
        app._delObject('localities_rod', suppress_events=True)
        transaction.commit()

    if getattr(app, 'localities_dict', None):
        app._delObject('localities_dict', suppress_events=True)
        transaction.commit()

    if getattr(app, 'localities_iso_dict', None):
        app._delObject('localities_iso_dict', suppress_events=True)
        transaction.commit()

    if getattr(app, 'localities_table', None):
        app._delObject('localities_table', suppress_events=True)
        transaction.commit()
