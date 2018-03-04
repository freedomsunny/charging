# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import datetime
import json
import tornado.web

import ops_charging.log as logging
from ops_charging.api.auth import auth as Auth
from ops_charging.options import get_options
from ops_charging.plugins.JsonResponses import BaseHander
from ops_charging.plugins.pay.alipay import AliPayPlugins
from ops_charging.plugins.users_plugins import UserOperate as users_api

url_map = {
    r"/wechatpay/asyncnotify$": 'WchatPayRes',
}
LOG = logging.getLogger(__name__)

options = get_options()


class WchatPayRes(BaseHander):
   pass






