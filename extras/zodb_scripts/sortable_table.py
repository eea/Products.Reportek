from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE =  request.RESPONSE

def changeQueryString(query_string, p_parameter, p_value):
    """ given the QUERY_STRING part of an URL, the function searches for the
        parameter p_parameter and gives it the value p_value
    """
    l_ret = ''
    try:
        l_encountered = 0
        for l_item in query_string.split('&'):
            l_param, l_value = l_item.split('=')
            if l_param == p_parameter:
                l_ret = query_string.replace(p_parameter + '=' + l_value, p_parameter +'=' + str(p_value))
                l_encountered = 1
        if l_encountered == 0:
            l_ret = query_string + '&' + p_parameter + '=' + p_value
    except:
        l_ret = p_parameter + '=' + str(p_value)
    return l_ret


for th in headers:
    qs = changeQueryString(request['QUERY_STRING'],'sort_on',th['id'])
    title = html_quote(th['title'])
    if th['sortable']:
        if sort_on == th['id']:
            if sort_order == '':
                qs = changeQueryString(qs,'sort_order','reverse')
                print """<th scope="col" class="sorted" title="Sorted A..Z"><a
                 href="%s?%s" rel="nofollow">%s<img
                 src="/styles/sortup.gif" width="12" height="12" alt=""/></a></th>""" % \
                 ( request['URL'], html_quote(qs), title)
            else:
                qs = changeQueryString(qs,'sort_order','')
                print """<th scope="col" class="sorted" title="Sorted Z..A"><a
                  href="%s?%s" rel="nofollow">%s<img
                 src="/styles/sortdown.gif" width="12" height="12" alt=""/></a></th>""" % \
                 ( request['URL'], html_quote(qs), title)
        else:
            print """<th scope="col" title="Sortable"><a
             href="%s?%s" rel="nofollow">%s<img
             src="/styles/sortnot.gif" width="12" height="12" alt=""/></a></th>""" % \
                 ( request['URL'], html_quote(qs), title)
    else:
        print """<th title="Not sortable" scope="col"><span>%s</span></th>""" % title

return printed
