import logging
getters_log = logging.getLogger(__name__ + '.extraparams')


def get_country_code(file_obj):
    return file_obj.getParentNode().getCountryCode()


def request_params(keys, obj=None):
    registry_getters = {
        'country_code': get_country_code,
        # 'xpath': get_xml_xpath,
    }
    params = []
    for key in keys:
        try:
            if obj:
                params.append(registry_getters[key](obj))
            else:
                params.append(registry_getters[key]())
        except KeyError as err:
            getters_log.warning('Getter for {0} not implemented.'.format(key))
            raise NotImplementedError
    return params
