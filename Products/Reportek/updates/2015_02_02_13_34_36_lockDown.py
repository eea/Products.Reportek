# from Products.Reportek.updates.2015_02_02_13_34_36_lockDown import update
import transaction

def update(app):
    eng = app.ReportekEngine
    # this will be recreated on next access
    delattr(eng, '_authMiddlewareApi')
    transaction.commit()
