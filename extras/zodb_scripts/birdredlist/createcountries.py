## Script (Python) "createcountries"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
request = container.REQUEST
response =  request.response

obllist = ['http://rod.eionet.europa.eu/obligations/213']

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
 'tr': '38', 'ua': '39', 'uk': '40', 'uk_gb': '40', 'uz': '107', 'xk': '42' }

collections = [
 ['ad', 'ad', 'Andorra', 'n'],
 ['al', 'al', 'Albania', 'n'],
 ['am', 'am', 'Armenia', 'n'],
 ['at', 'at', 'Austria', 'y'],
 ['az', 'az', 'Azerbaijan', 'n'],
 ['ba', 'ba', 'Bosnia and Herzegovina', 'n'],
 ['be', 'be', 'Belgium', 'y'],
 ['bg', 'bg', 'Bulgaria', 'y'],
 ['by', 'by', 'Belarus', 'n'],
 ['ch', 'ch', 'Switzerland', 'n'],
 ['cy', 'cy', 'Cyprus', 'y'],
 ['cz', 'cz', 'Czech republic', 'y'],
 ['de', 'de', 'Germany', 'y'],
 ['dk', 'dk', 'Denmark', 'y'],
 ['ee', 'ee', 'Estonia', 'y'],
 ['es', 'es', 'Spain', 'y'],
 ['es', 'esic', 'Canary Islands (ES)', 'y'],
 ['fi', 'fi', 'Finland', 'y'],
 ['fo', 'fo', 'Faroe Islands', 'n'],
 ['fr', 'fr', 'France', 'y'],
 ['gb', 'gib', 'Gibraltar (UK)', 'y'],
 ['gb', 'uk', 'United Kingdom', 'y'],
 ['ge', 'ge', 'Georgia', 'n'],
 ['gl', 'gl', 'Greenland', 'n'], # New country?
 ['gr', 'gr', 'Greece', 'y'],
 ['hr', 'hr', 'Croatia', 'n'],
 ['hu', 'hu', 'Hungary', 'y'],
 ['ie', 'ie', 'Ireland', 'y'],
 ['im', 'im', 'Isle of Man', 'n'], # New country?
 ['is', 'is', 'Iceland', 'n'],
 ['it', 'it', 'Italy', 'y'],
 ['li', 'li', 'Liechtenstein', 'n'],
 ['lt', 'lt', 'Lithuania', 'y'],
 ['lu', 'lu', 'Luxembourg', 'y'],
 ['lv', 'lv', 'Latvia', 'y'],
 ['mc', 'mc', 'Monaco', 'n'],
 ['md', 'md', 'Moldova', 'n'],
 ['me', 'me', 'Montenegro', 'n'],
 ['mk', 'mk', 'Macedonia (FYR)', 'n'],
 ['mt', 'mt', 'Malta', 'y'],
 ['nl', 'nl', 'Netherlands', 'y'],
 ['no', 'no', 'Norway', 'n'],
 ['no', 'sj', 'Svalbard and Jan Mayen', 'n'],
 ['pl', 'pl', 'Poland', 'y'],
 ['pt', 'pt', 'Portugal', 'y'],
 ['pt', 'ptac', 'Azores (PT)', 'y'],
 ['pt', 'ptma', 'Madeira (PT)', 'y'],
 ['ro', 'ro', 'Romania', 'y'],
 ['rs', 'rs', 'Serbia', 'n'],
 ['ru', 'ru', 'Russia', 'n'],
 ['se', 'se', 'Sweden', 'y'],
 ['si', 'si', 'Slovenia', 'y'],
 ['sk', 'sk', 'Slovakia', 'y'],
 ['sm', 'sm', 'San Marino', 'n'],
 ['tr', 'tr', 'Turkey', 'n'],
 ['ua', 'ua', 'Ukraine', 'n'],
 ['uk', 'gg-je', 'Channel Islands', 'n'],
 ['va', 'va', 'Vatican City', 'n'],  # New country?
 ['xk', 'xk', 'Kosovo (UNSCR 1244/99)', 'n'],
]

for row in collections:
    c_id = row[1]
    country = getattr(container, c_id)
    user_id = row[0]
    print "%s -- %s" % (user_id, c_id)
    country.manage_addProduct['Reportek'].manage_addCollection(row[2],
'',
'','','',
'http://rod.eionet.europa.eu/spatial/%s' % loccodes[row[1]],'',
obllist,
allow_collections=0,allow_envelopes=1,id=user_id)
return printed

#    newcol = getattr(country, user_id)
#    newcol.manage_setLocalRoles(user_id, ['Owner',])
#    newcol.manage_permission('View', roles=['Owner','Manager','ClientODS'], acquire=0)
