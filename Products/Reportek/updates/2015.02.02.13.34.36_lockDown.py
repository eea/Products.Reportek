# from Products.Reportek.updates.2015.02.02.13.34.36_lockDown import update
import transaction

def update(app):
    eng = app.ReportekEngine
    # this will be recreated on next access
    delattr(eng, '_authMiddlewareApi')
    transaction.commit()
