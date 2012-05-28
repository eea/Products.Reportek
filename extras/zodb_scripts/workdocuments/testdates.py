from Products.PythonScripts.standard import html_quote
dow = context.ZopeTime().dow()
print dow
backtime = context.ZopeTime() - 360 - dow
print backtime
print backtime.dow()
print context.ZopeTime() - dow
return printed
