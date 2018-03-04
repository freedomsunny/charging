# -*- coding:utf-8 -*-
from __future__ import unicode_literals
import json
import datetime
import tornado.web
import time

from ops_charging.plugins.JsonResponses import BaseHander
from ops_charging.plugins.users_plugins import UserOperate as users_api
from ops_charging.plugins.orders_tencent import TencentOrders
from ops_charging.api.auth import auth as Auth

url_map = {
    r"/order/tencent": "TencentOrderAPI",
}


class TencentOrderAPI(BaseHander, Auth.BaseAuth):
    def post(self):
        try:
            data = json.loads(self.request.body)
            if not data:
                em = "ValueError: no data found"
                self.write({"code": 1, "message": em})
                return
            # add user
            data["user_id"] = data.get("user_id")
            users_api.add_user(data)
            ret = TencentOrders.add_order(data=data)
            if ret.get("code") != 0:
                self.set_status(500)
                self.write(ret)
            else:
                self.write(ret)
        except ValueError:
            self.set_status(500)

    def put(self, **kwargs):
        try:
            resource_id = str(self.path_kwargs.get('rid', "")).strip()
        except:
            pass

