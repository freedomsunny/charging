# -*- coding:utf-8 -*-
from __future__ import unicode_literals
import json
import datetime
import tornado.web
import uuid
import urllib2

import ops_charging.log as logging
from ops_charging.db.models import get_uuid
from ops_charging.options import get_options
from ops_charging.plugins.JsonResponses import BaseHander
from ops_charging.api.auth import auth as Auth
from ops_charging.api.auth.auth import auth_by_keystone


url_map = {
    r"/file$": 'FileAPI',
    }

options = get_options()
LOG = logging.getLogger(__name__)



# class FileAPI(BaseHander, Auth.BaseAuth):
class FileAPI(BaseHander):
    def get(self):
        """get file"""
        token = self.get_argument("token", "")
        if not token:
            em = "need token"
            LOG.exception(em)
            self.set_status(500)
            return
        file_path = self.get_argument('path', "")
        # 只允许获取指定目录内的文件
        if not file_path or not file_path.startswith(options.upload_file_path):
            em = "file path error"
            LOG.exception(em)
            self.set_status(400)
            return
        # auth by keystone
        user_info = auth_by_keystone(token)
        if not user_info[0]:
            em = "auth error"
            LOG.exception(em)
            self.set_status(401)
            return
        # 只允许财务角色查看
        # result = [True for role in user_info[1].get("roles") if role.get("name") == "finance"]
        # if not result:
        #     em = "auth error"
        #     LOG.exception(em)
        #     self.set_status(401)
        #     return
        with open(file_path, "r") as f:
            self.set_header("Content-type", "image/png")
            self.write(f.read())

    def delete(self):
        """delete file"""
        invoice_uuid = self.get_argument('invoice_uuid', "")
        if not invoice_uuid:
            self.set_status(400)
            return
