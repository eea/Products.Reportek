from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE =  request.RESPONSE

print """<?xml version="1.0" encoding="utf-8" ?>
<urlset xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
   xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd"
   xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">"""

RESPONSE.setHeader('content-type', 'text/xml;charset=utf-8')

serverurl = html_quote(request.SERVER_URL)
for item in container.Catalog(meta_type='Report Envelope', released=1):
  try:
    print """<url><loc>%s%s</loc></url>""" % ( serverurl, html_quote(item.getPath()) )
  except:
    print """<!-- deleted envelope %s -->""" % item.id;




print """</urlset>"""
return printed
