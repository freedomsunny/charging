# -*- coding:utf-8 -*-
from __future__ import unicode_literals
import json
import datetime
import tornado.web

from ops_charging.plugins.users_plugins import UserOperate as users_api
from ops_charging.plugins.JsonResponses import BaseHander
from ops_charging.api.auth import auth as Auth


url_map = {
    r"/user/changeuserstatus$": 'ChangeUserResourceStatus',
    r"/user/getalreadyexceeduser$": "GetAlreadyExceedUser",
    r"/user/(?P<rid>.+)$": "GetUserInfo"
}


class ChangeUserResourceStatus(BaseHander, Auth.BaseAuth):
    def post(self):
        data = json.loads(self.request.body)
        if not data:
            self.set_status(400)
        user_id = data.get("user_id")
        status = data.get("status")
        ret = users_api.change_user_resource_status(user_id, status)
        if not ret[0]:
            self.set_status(ret[1])


class GetAlreadyExceedUser(BaseHander, Auth.BaseAuth):
    def get(self):
        start_time = self.get_argument('start_time', None)
        end_time = self.get_argument('end_time', None)
        user_id = self.get_argument("user_id", None)
        ret = users_api.get_already_exceed_user(start_time, end_time, user_id)
        if not ret[0]:
            self.set_status(400)
            return
        self.json_response(0, result=ret)


class GetUserInfo(BaseHander, Auth.BaseAuth):
    def get(self, **kwargs):
        # 如果参数传了user_id不是admin role则不通过
        if not self.context.get("user").get("admin"):
            self.set_status(401)
            self.write({"code": 1, "message": "权限拒绝"})
            return
        user_id = str(self.path_kwargs.get('rid', "")).strip()
        ret = users_api.get_user_info(user_id)
        self.json_response(0, result=ret)

