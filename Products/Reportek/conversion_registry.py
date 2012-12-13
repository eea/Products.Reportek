import logging

getters_log = logging.getLogger(__name__ + '.extraparams')

def get_country_code():
    pass

def requested_params(keys):
    registry_getters = {
        'country_code': get_country_code,
    }
    params = []
    for key in keys:
        try:
            params.append(registry_getters[key]())
        except KeyError as err:
            getters_log.warning('Getter for {0} not implemented.'.format(key))
            raise NotImplementedError
    return params


