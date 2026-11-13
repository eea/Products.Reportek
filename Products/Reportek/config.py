# -*- coding: UTF-8 -*-
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
# Author(s):
# Daniel Mihai Bărăgan, Eau de Web

import os

from App.config import getConfiguration
from Products.Reportek.permissions import change_collections, change_envelopes

__all__ = [
    "REPORTEK_DEPLOYMENT",
    "DEPLOYMENT_BDR",
    "DEPLOYMENT_CDR",
    "DEPLOYMENT_MDR",
    "permission_manage_properties_collections",
    "permission_manage_properties_envelopes",
    "LOCAL_CONVERTERS_PORT",
    "LOCAL_CONVERTERS_HOST",
    "LOCAL_CONVERTERS_SCHEME",
    "ENVELOPES_LISTING_PAGE_SIZE",
    "XLS_HEADINGS",
    "BDR_XLS_HEADINGS",
    "CDR_XLS_HEADINGS",
]

DEPLOYMENT_CDR = "CDR"
DEPLOYMENT_BDR = "BDR"
DEPLOYMENT_MDR = "MDR"

BDR_XLS_HEADINGS = [
    ("Company ID", "company_id"),
    ("Country", "country"),
    ("Company", "company"),
    ("User ID", "userid"),
    ("Title", "title"),
    ("URL", "path"),
    ("Years", "years"),
    ("Obligation", "obligation"),
    ("Reported", "reported"),
    ("Files", "files"),
    ("Accepted", "accepted"),
    ("Activities", "activities"),
    ("Reported Gases", "gases"),
    ("Issued authorisations", "i_authorisations"),
    ("Available authorisations", "a_authorisations"),
]

CDR_XLS_HEADINGS = [
    ("Country", "country"),
    ("Title", "title"),
    ("Years", "years"),
    ("Obligation", "obligation"),
    ("Reported", "reported"),
]

XLS_HEADINGS = CDR_XLS_HEADINGS

REPORTEK_DEPLOYMENT = os.environ.get("REPORTEK_DEPLOYMENT", DEPLOYMENT_MDR)
LOCAL_CONVERTERS_PORT = os.environ.get("LOCAL_CONVERTERS_PORT", "5000")
LOCAL_CONVERTERS_HOST = os.environ.get("LOCAL_CONVERTERS_HOST", "localhost")
LOCAL_CONVERTERS_SCHEME = os.environ.get("LOCAL_CONVERTERS_SCHEME", "http")
ZIP_CACHE_THRESHOLD = int(os.environ.get("ZIP_CACHE_THRESHOLD", 100000000))


def _int_from_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _listing_page_size(value):
    """The pager of the listing is only shown for more than 25 envelopes, so
    the pages cannot be smaller than that; 0 lists all the envelopes."""
    if value <= 0:
        return 0
    return max(value, 25)


# Number of envelopes per page in the listing of a collection
ENVELOPES_LISTING_PAGE_SIZE = _listing_page_size(
    _int_from_env("ENVELOPES_LISTING_PAGE_SIZE", 100)
)
ZIP_CACHE_ENABLED = os.environ.get("ZIP_CACHE_ENABLED", "True").lower() in (
    "true",
    "yes",
    "on",
    "1",
)
ZIP_CACHE_PATH = os.environ.get("ZIP_CACHE_PATH", None)
if not ZIP_CACHE_PATH:
    try:
        ZIP_CACHE_PATH = getattr(getConfiguration(), "clienthome", None)
    except Exception:
        ZIP_CACHE_PATH = CLIENT_HOME  # noqa

if REPORTEK_DEPLOYMENT in (DEPLOYMENT_CDR, DEPLOYMENT_MDR):
    permission_manage_properties_collections = change_collections
    permission_manage_properties_envelopes = change_envelopes

elif REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
    permission_manage_properties_collections = "Manage properties"
    permission_manage_properties_envelopes = "Manage properties"
    XLS_HEADINGS = BDR_XLS_HEADINGS
