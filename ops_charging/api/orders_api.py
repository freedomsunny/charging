# -*- coding:utf-8 -*-
from __future__ import unicode_literals
import json
import datetime
import tornado.web
import time

from ops_charging.plugins.users_plugins import UserOperate as users_api
from ops_charging.plugins.orders_plugins import OrderAbout as orders_api
from ops_charging.plugins.JsonResponses import BaseHander
from ops_charging.api.auth import auth as Auth
from ops_charging.plugins.expr_money_plugins import ExprOrders as exprorders

url_map = {
    r"/order/orders$": 'SaveOrder',
    r"/order/orders/(?P<rid>.+)$": "SaveOrder",
    r"/money/usermoney$": 'UserMoney',
    r"/rechargelog$": 'UserRechargeLog',
    r"/consumelog$": 'UserOrderConsumeLog',
    r"/userdayuse$": 'UserDayUsed',
    r"/test/sayhello": "SayHello",
    r"/consumekind$": "GetConsumeLogKindMoney",
    r"/orderskind$": "GetOrderLogKindMoney",
    r"/users/getexceedtime": "GetUserExceedTime",
    r"/order/sync$": "SyncET",
    r"/resource$": "GetResource"
}


class SayHello(BaseHander, Auth.BaseAuth):
    def get(self):
        msg = "Hello Word"
        self.write(msg)


class SaveOrder(BaseHander, Auth.BaseAuth):

    def get(self):
        try:
            user_id = self.context.get("user_id")
            status = self.get_argument('status', '')
            if status != "Settlemented" or not status:
                status = None
            ret = orders_api.get_user_orders(user_id, status)
            if ret == 0:
                self.set_status(500)
                self.json_response(1, result=ret)
            else:
                self.json_response(0, result=ret)
        except Exception as e:
            self.set_status(500)
            self.write({"code": 1, "message": "获取订单失败. <{0}>".format(e)})

    def post(self):
        try:
            data = json.loads(self.request.body)
            if not data:
                em = "ValueError: no data found"
                self.write({"code": 1, "message": em})
            # add user
            data["user_id"] = data.get("user_id")
            users_api.add_user(data)
            ret = orders_api.add_order(data)
            if ret.get("code") != 0:
                self.set_status(500)
                self.write(ret)
            else:
                self.write(ret)
        except Exception as e:
            self.set_status(500)
            self.write({"code": 1, "message": "添加订单失败. {0}".format(e)})

    def delete(self, **kwargs):
        try:
            resource_id = str(self.path_kwargs.get('rid', "")).strip()
            ret = orders_api.delete_order(resource_id=resource_id,
                                          end_time=int(time.time())
                                          )
            if ret.get("code") != 0:
                self.set_status(500)
                self.write({"code": 1, "message": "结束订单失败"})
            else:
                self.write({"code": 0, "message": ""})
        except Exception as e:
            self.set_status(500)
            self.write({"code": 1, "message": "结束订单失败. {0}".format(e)})

    def put(self, **kwargs):
        try:
            data = json.loads(self.request.body)
            resource_id = str(self.path_kwargs.get('rid', "")).strip()
            ret = orders_api.update_order(data=data,
                                          resource_id=resource_id)
            if ret.get("code") != 0:
                self.set_status(500)
                self.write({"code": 1, "message": "变更订单失败"})
            else:
                self.write({"code": 0, "message": ""})
        except Exception as e:
            self.set_status(500)
            self.write({"code": 1, "message": "变更订单失败. <{0}>".format(e)})


class UserMoney(BaseHander, Auth.BaseAuth):
    def get(self):
        """
        this method to get user's money
        :return: 
        """
        user_id = self.get_argument('user_id', '')
        if not user_id:
            user_id = self.context.get("user_id")
        else:
            # 如果参数传了user_id不是admin role则不通过
            if not self.context.get("user").get("admin"):
                self.set_status(401)
                return
        ret = users_api.get_user_money(user_id)
        if ret == 0:
            self.json_response(1, result={})
        else:
            self.json_response(0, result=ret)


class UserRechargeLog(BaseHander, Auth.BaseAuth):

    def get(self):
        """this method to get user Recharger recorde"""
        user_id = (self.context.get("user_id") if not self.get_argument('user_id', '') else self.get_argument('user_id', ''))
        recharge_way = self.get_argument('recharge_way', '')

        ret = users_api.get_user_recharge_log(user_id, recharge_way)
        if ret == 0:
            self.json_response(1, result=ret)
        else:
            self.json_response(0, result=ret)


class UserOrderConsumeLog(BaseHander, Auth.BaseAuth):
    def get(self):
        """this method to get user consume log"""
        user_id = self.context.get("user_id")
        ret = users_api.get_user_consume_log(user_id)
        if ret == 0:
            self.json_response(1, result=ret)
        else:
            self.json_response(0, result=ret)


class UserDayUsed(BaseHander, Auth.BaseAuth):
    def get(self):
        """this method to get user how much used one day"""
        user_id = self.context.get("user_id")
        ret = orders_api.get_user_day_used(user_id)
        if ret == 0:
            self.json_response(1, result=ret)
        else:
            self.json_response(0, result=ret)


class GetConsumeLogKindMoney(BaseHander, Auth.BaseAuth):
    def get(self):
        """this method to get user how much used one day"""
        user_id = self.context.get("user_id")
        ret = users_api.expr_consume_kinds_used(user_id)
        if ret == 0:
            self.json_response(1, result=ret)
        else:
            self.json_response(0, result=ret)


class GetOrderLogKindMoney(BaseHander, Auth.BaseAuth):
    def get(self):
        """this method to get user how much used one day"""
        user_id = self.context.get("user_id")
        ret = orders_api.expr_order_kinds_used(user_id)
        if ret == 0:
            self.json_response(1, result=ret)
        else:
            self.json_response(0, result=ret)


class GetUserExceedTime(BaseHander, Auth.BaseAuth):
    def get(self):
        ret = users_api.get_user_exceed_time_devops()
        if not ret[0]:
            self.json_response(0, result=ret[1])
        else:
            self.write(ret[1])


class SyncET(Auth.BaseAuth):
    def put(self):
        if not self.context.get("user").get("admin"):
            self.set_status(401)
        orders_api.sync_user_et()


class GetResource(Auth.BaseAuth):
    def get(self):
        # 检查用户是否是admin用户
        if not self.context.get("user").get("admin"):
            self.set_status(401)
            return
        resource_id = self.get_argument('resource_id', "")

        result = orders_api.get_order_by_resource_id(resource_id=resource_id)
        self.set_status(result)
