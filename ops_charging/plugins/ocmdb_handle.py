# encoding=utf-8
import json

import ops_charging.log as logging
from ops_charging.options import get_options
from ops_charging.utils import get_http, post_http, put_http
from ops_charging.utils import get_token



LOG = logging.getLogger(__name__)

cmdb_opts = [
]
options = get_options()


class CMDBHandle(object):
    @staticmethod
    def get_physical_info(cmdb_uuid):
        try:
            admin_token = get_token()
            url = options.cmdb_ep + "/assets/" + cmdb_uuid
            headers = {'X-Auth-Token': admin_token.strip()}
            ret = get_http(url=url, headers=headers)
            if ret.status_code != 200:
                em = "get physical info from cmdb error...."
                LOG.exception(em)
                return False, ret.status_code
            return True, ret.json()
        except Exception as e:
            em = "get physical info from cmdb error. msg: <{0}>".format(e)
            LOG.exception(em)
            return False, 500

    @staticmethod
    def syncdata2cmdb(resouce_type, id):
        try:
            url = options.sync_api + "/sync/" + id
            data = {"resource_type": resouce_type}
            result = put_http(url=url, data=json.dumps(data))
            if result.status_code != 200:
                em = "sync data to cmdb error. resource type: <{0}>  resource id: <{1}>".format(resouce_type,
                                                                                                id)
                LOG.exception(em)
            return False
        except Exception as e:
            em = "sync data to cmdb error resour type: <{0}>  resource id: <{1}>".format(resouce_type, id)
            LOG.exception(em)
            return False

