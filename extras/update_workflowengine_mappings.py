import transaction

def update_wfengine(root, commit=False):
    from Products.Reportek import constants
    wf_eng = getattr(root, constants.WORKFLOW_ENGINE_ID)
    for key, value in wf_eng.process_mappings.iteritems():
        dataflows = value['dataflows']
        value['dataflows'] = [it.replace('eionet.eu.int', 'eionet.europa.eu') for it in dataflows]
    wf_eng._p_changed = 1
    if commit:
        transaction.commit()
