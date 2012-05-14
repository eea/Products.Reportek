# The contents of this file are subject to the Mozilla Public
# License Version 1.1 (the "License"); you may not use this file
# except in compliance with the License. You may obtain a copy of
# the License at http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS
# IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
# implied. See the License for the specific language governing
# rights and limitations under the License.
#
# The Original Code is ICQuiz version 0.1
#
# The Initial Owner of the Original Code is European Environment
# Agency (EEA).  Portions created by Finsiel Romania are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Authors(s):
# Dragos Chirila, Finsiel Romania
# Cornel Nitu, Finsiel Romania
# Anton Cupcea, Finsiel Romania
#
#$Id$

#Python imports
import string
import xmlrpclib
import httplib
from base64 import encodestring

#Zope imports

#Product imports

#def Server(url, username, password):
#    t = BasicAuthTransport(username, password)
#    return xmlrpclib.Server(url, t)

class BasicAuthTransport(xmlrpclib.Transport):
    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.verbose = None
        self.has_ssl = httplib.__dict__.has_key("HTTPConnection")

    def request(self, host, handler, request_body, verbose=None):
        # issue XML-RPC request
        if self.has_ssl:
            if host.startswith("https:"): h = httplib.HTTPSConnection(host)
            else: h = httplib.HTTPConnection(host)
        else: h = httplib.HTTP(host)        

        h.putrequest("POST", handler)

        # required by HTTP/1.1
        if not self.has_ssl: # HTTPConnection already does 1.1
            h.putheader("Host", host)
        h.putheader("Connection", "close")

        # required by XML-RPC
        h.putheader("User-Agent", self.user_agent)
        h.putheader("Content-Type", "text/xml")
        h.putheader("Content-Length", str(len(request_body)))

        # basic auth
        if self.username is not None and self.password is not None:
            h.putheader("AUTHORIZATION", "Basic %s" % string.replace(
                    encodestring("%s:%s" % (self.username, self.password)),
                    "\012", ""))
        h.endheaders()

        if request_body: h.send(request_body)
        if self.has_ssl:
            response = h.getresponse()
            if response.status != 200:
                raise xmlrpclib.ProtocolError(host + handler,
                                              response.status, 
                                              response.reason,
                                              response.msg)
            file = response.fp
        else:
            errcode, errmsg, headers = h.getreply()
            if errcode != 200:
                raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

            file = h.getfile()

        return self.parse_response(file) 
