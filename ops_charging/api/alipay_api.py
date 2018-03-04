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
    r"/alipay/notfiy$": 'AliPayRes',
    r"/alipay/notfiy_asyncnotify$": 'AliPayRes',
    r"/alipay/geturl$": 'PayURL',
    r"/test": "Test"
}
LOG = logging.getLogger(__name__)

options = get_options()


class Test(BaseHander, Auth.BaseAuth):
    def get(self):
        msg = "Hello world"
        self.write(msg)


class AliPayRes(BaseHander):
    def get(self):
        """Alipay to server sync notify method: get"""

        ret = AliPayPlugins.notify_verify(self.get_argument)
        if ret == 0:
            self.redirect(options.failure_url)
        else:
            self.redirect(options.success_url)

    def post(self):
        """Alipay to server async notify method: POST"""
        # verify notify is it available
        async_data = AliPayPlugins.asyncnotify_verify(self.get_argument)
        if async_data.get("error"):
            LOG.exception(async_data)
            self.write(async_data)
        ret = users_api.update_user_recharge(async_data)
        LOG.debug("alipay async notiry msg: <{0}>".format(async_data))
        if ret == 0:
            LOG.exception(ret)
            self.write(ret)
        else:
            # Alipay need `success`
            self.write("success")


class PayURL(BaseHander, Auth.BaseAuth):
    def get(self):
        out_trade_no = AliPayPlugins.generate_out_trade_no()
        user_name = self.context.get("user").get("user").get("name")
        user_id = self.context.get("user_id")
        project_id = self.context.get("tenant_id")
        subject = self.get_argument("subject", '')
        body = self.get_argument("body", '')
        total_fee = self.get_argument("total_fee", '')

        data = {"user_id": user_id,
                "_context_user_name": user_name,
                "tenant_id": project_id}
        # add user
        users_api.add_user(data)
        # total_fee can not `None`
        if not total_fee or float(total_fee) <= 0:
            em = "`total_fee` can not None or le 0"
            self.write({"error": [{"code": 400, "msg": "{0}".format(em)}]})
        # recorde recharge
        ret = users_api.add_user_recharge(user_id, user_name, total_fee, out_trade_no, trade_status="failed", recharge_way="Alipay")
        if ret == 0:
            self.json_response(0, result=ret)
        elif ret.get("error"):
            self.json_response(0, result=ret)
        else:
            ret = AliPayPlugins.create_direct_pay_by_user(out_trade_no, subject, body, total_fee)
            status = "sucess"
            if not ret:
                status = "failed"
            LOG.debug("user: <{0}> request alipay url. out_trade_no: <{1}>  url: <{2}>. status: <{3}>".format(user_id, out_trade_no, ret, status))
            self.json_response(0, result=ret)
