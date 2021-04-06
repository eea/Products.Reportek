# Script (Python) "getCountryBoundingBox"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=country_uri=''
# title=
##
countries_dict = {'au': {'minx': '3226724.13793103', 'miny': '2710937.5', 'maxx': '5676724.13793103', 'maxy': '4835937.5'}, 'be': {
    'minx': '3226724.13793103', 'miny': '2710937.5', 'maxx': '5676724.13793103', 'maxy': '4835937.5'}}

if not country_uri:
    country_uri = context.country

return countries_dict[country_uri]
