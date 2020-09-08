import os

from plone.caching.interfaces import ICacheSettings
from plone.registry import Record, field


def get_bool_env(value):
    if value.lower() in ('true', 'yes', 'y', '1'):
        return True
    return False

# To be set via environment variables
CACHE_SETTINGS_ENABLED = get_bool_env(os.environ.get('CACHE_SETTINGS_ENABLED', 'false'))
CACHE_PURGING_ENABLED = get_bool_env(os.environ.get('CACHE_PURGING_ENABLED', 'false'))
CACHE_PURGING_PROXY = os.environ.get('CACHE_PURGING_PROXY', '')
CACHE_PURGING_PROXY_PORT = os.environ.get('CACHE_PURGING_PROXY_PORT', '')
CACHE_PURGING_VHOST = get_bool_env(os.environ.get('CACHE_PURGING_VHOST', 'false'))
CACHE_PURGING_DOMAIN = os.environ.get('CACHE_PURGING_DOMAIN', '')

CACHE_PROXY = (u"{}:{}".format(CACHE_PURGING_PROXY, CACHE_PURGING_PROXY_PORT),) if CACHE_PURGING_PROXY and CACHE_PURGING_PROXY_PORT else ()
# ('http://example.com:80`, 'http://www.example.com:80',)
CACHE_DOMAINS = (u"http://{}:80".format(CACHE_PURGING_DOMAIN), u"https://{}:443".format(CACHE_PURGING_DOMAIN),) if CACHE_PURGING_DOMAIN else ()


def registry_setup(registry):
    registry.registerInterface(ICacheSettings)

    # Set registry records and fields for ICachePurgingSettings
    cp_enabled = field.Bool(title=u'enabled')
    cpe_record = Record(cp_enabled)

    c_proxies = field.Tuple(title=u"cachingProxies", value_type=field.TextLine(title=u"Value"))
    cp_record = Record(c_proxies)

    # plone.cachepurging.interfaces.ICachePurgingSettings.virtualHosting
    # need to set this to True to incorporate virtual host tokens in the PURGE paths
    cp_vh = field.Bool(title=u"virtualHosting")
    cp_vh_record = Record(cp_vh)

    # plone.cachepurging.interfaces.ICachePurgingSettings.domains
    cp_domains = field.Tuple(title=u"domains", value_type=field.TextLine(title=u"Value"))
    cp_domains_record = Record(cp_domains)
    # In case we use plone.caching.operations.chain
    # op_chain = field.List(title=u"Operations", value_type=field.DottedName())
    # opc_record = Record(opc_record)

    registry.records['plone.cachepurging.interfaces.ICachePurgingSettings.enabled'] = cpe_record
    registry.records['plone.cachepurging.interfaces.ICachePurgingSettings.cachingProxies'] = cp_record
    registry.records['plone.cachepurging.interfaces.ICachePurgingSettings.virtualHosting'] = cp_vh_record
    registry.records['plone.cachepurging.interfaces.ICachePurgingSettings.domains'] = cp_domains_record

    # Turn on Caching engine
    registry['plone.caching.interfaces.ICacheSettings.enabled'] = CACHE_SETTINGS_ENABLED

    # Set caching operation
    settings = registry.forInterface(ICacheSettings)
    if settings.operationMapping is None: # initialise if not set already
        settings.operationMapping = {}
    settings.operationMapping['plone.contentTypes'] = 'Products.Reportek.caching.moderateCaching'
    # registry_setup(registry)
    # import transaction; transaction.commit()
    # import pdb;pdb.set_trace()
        # registry['plone.caching.operations.chain.plone.contentTypes.operations'] = \
    # ['plone.caching.tests.maxage']

    # Turn on Cache Purging Settings
    registry['plone.cachepurging.interfaces.ICachePurgingSettings.enabled'] = CACHE_PURGING_ENABLED

    # Configure the caching proxy server e.g.:varnish
    registry['plone.cachepurging.interfaces.ICachePurgingSettings.cachingProxies'] = CACHE_PROXY

    # Configure cache purging virtualhost
    registry['plone.cachepurging.interfaces.ICachePurgingSettings.virtualHosting'] = CACHE_PURGING_VHOST

    # Configure the domain for caching purging
    registry['plone.cachepurging.interfaces.ICachePurgingSettings.domains'] = CACHE_DOMAINS
