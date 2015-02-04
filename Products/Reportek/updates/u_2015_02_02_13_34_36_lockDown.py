# from Products.Reportek.updates.2015_02_02_13_34_36_lockDown import update

# FIXME: this will not work, because zope wants to wake child object
# in order to delete it, dna he cannot do so, becasuse it's class parents changed
# will have to do this manualy

import transaction

def update(app):
    eng = app.ReportekEngine
    # this will be recreated on next access
    delattr(eng, '_authMiddlewareApi')
    transaction.commit()
