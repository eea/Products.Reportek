## Script (Python) "ACreateCollections"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
from Products.PythonScripts.standard import html_quote
request = container.REQUEST

collections = [
( 'fgas30001', 'fr', 'GAZECHIM'),
( 'fgas30002', 'gr', 'TAIRIS AEVE'),
( 'fgas30003', 'it', 'LORENZI MICAELA'),

]

obllist = ['http://rod.eionet.europa.eu/obligations/669']

loccodes={ 'ad': '96', 'al': '2', 'am': '97', 'at': '3', 'az': '98',
 'ba': '6', 'be': '5', 'bg': '7', 'by': '4', 'ch': '37',
 'cy': '9', 'cz': '10', 'de': '15', 'dk': '11',
 'dz': '110', 'ee': '12', 'eg': '109', 'el': '16', 'es': '35', 'eu': '1',
 'fi': '13', 'fr': '14', 'gb': '40', 'ge': '99', 'gr': '16',
 'hr': '8', 'hu': '17', 'ie': '20', 'is': '18', 'it': '19',
 'kg': '101', 'kz': '100', 'li': '102', 'lt': '22', 'lu': '23',
 'lv': '21', 'ly': '111', 'ma': '112', 'mc': '103', 'md': '26',
 'me':'115',
 'mk': '24', 'mt': '25', 'nl': '27', 'no': '28', 'pl': '29',
 'pt': '30', 'ro': '31', 'rs': '41', 'ru': '32', 'se': '36', 'si': '34',
 'sk': '33', 'sm': '104', 'tj': '105', 'tm': '106', 'tn': '113',
 'tr': '38', 'ua': '39', 'uk': '40', 'uz': '107', 'xk': '42' }

for row in collections:
    c_id = row[1]
    country = getattr(container, c_id)
    user_id = row[0]
    print "%s -- %s" % (user_id, c_id)
    country.manage_addProduct['Reportek'].manage_addCollection(row[2],
'',
'','','',
'http://rod.eionet.eu.int/spatial/%s' % loccodes[row[1]],'',
obllist,
allow_collections=0,allow_envelopes=1,id=user_id)
    newcol = getattr(country, user_id)
    newcol.manage_setLocalRoles(user_id, ['Owner',])
    newcol.manage_permission('View', roles=['Owner','Manager','ClientFG'], acquire=0)
return printed
