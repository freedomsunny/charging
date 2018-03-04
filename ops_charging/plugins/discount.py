#!encoding=utf-8
from ops_charging.db.models import db_session, Orders, Price, User, RechargeLog, ConsumeLog, Discount
from sqlalchemy import and_
from ops_charging.utils import get_http, post_http, get_token, ConvertTime2Int
import ops_charging.log as logging
import uuid
import time
import json
import random

from ops_charging.plugins.users_plugins import UserOperate
from ops_charging.plugins.expr_money_plugins import ExprOrders
from ops_charging import cache
from ops_charging.service import manager
from ops_charging.options import get_options

LOG = logging.getLogger(__name__)
discount_opts = [

]
options = get_options(discount_opts)


class DiscountOperate(object):
    def __init__(self, *args, **kwargs):
        print "i am init"

    @staticmethod
    def add_discount(id, money, valid_date, user_context, description=None):
        try:
            if not id or not money or not valid_date or not user_context:
                em = "invalid argement with add discount"
                LOG.exception(em)
                return False, 400
            # must be admin role
            if not user_context.get("user").get("admin"):
                em = "user <{0}> is not admin. role must be admin.".format(user_context.get("user").get("user").get("name"))
                LOG.exception(em)
                return False, 400
            # check discount id is it esxit
            discount = Discount.query.filter(Discount.discount_id == id).first()
            if discount:
                em = "discount id discount_id already exist. id: <0>".format(id)
                LOG.exception(em)
                return False, 409
            # add discount id
            add_discount = Discount(uid=str(uuid.uuid1()), discount_id=id, money=money, gen_time=int(time.time()),
                                    valid_date=int(ConvertTime2Int(valid_date)), is_used=False, description=description)
            db_session.add(add_discount)
            db_session.commit()
            LOG.debug("add discount id Successful. discount id: <{0}>".format(id))
            return True, 200
        except Exception as e:
            db_session.rollback()
            em = "add discount error. discount id: <{0}>. msg: <{1}>".format(id, e)
            LOG.exception(em)
            return False, 500

    @staticmethod
    def use_discount(id, user_context):
        try:
            now_time = int(time.time())
            # check discount id is it exsit
            discount = Discount.query.filter(Discount.discount_id == id).first()
            if not discount:
                em = "can not found discount id. id: <0>".format(id)
                LOG.exception(em)
                return False, 410
            # check discount id is is exceed
            if discount.valid_date or discount.is_used:
                if discount.valid_date <= now_time or discount.is_used:
                    em = "discount id is not valid. id: <{0}>".format(discount.discount_id)
                    LOG.exception(em)
                    return False, 400
            user_id = user_context.get("user").get("user").get("id")
            # update user's money
            user = User.query.filter(User.user_id == user_id).first()
            if not user:
                em = "can not found user. user id: <{0}>".format(user_id)
                LOG.exception(em)
                # try to add user
                data = {"tenant_id": user_context.get("tenant_id"),
                        "_context_project_name": user_context.get("user").get("project").get("name"),
                        "user_id": user_context.get("user").get("user").get("id"),
                        "_context_user_name": user_context.get("user").get("user").get("id")
                        }
                ret = UserOperate.add_user(data)
                if not ret.get("success"):
                    return False, 500
                user = ret.get("success")[0].get("data")
            user.money += discount.money
            # update discount tables's status
            # Discount.query.filter(Discount.discount_id == id).update({Discount.is_used: True})
            # add Recharge Log
            recharge = RechargeLog(uid=str(uuid.uuid1()), user_id=user_id, user_name=user_context.get("user").get("user").get("name"),
                                   money=discount.money, log_time=int(time.time()), out_trade_no=discount.discount_id,
                                   trade_status="success", recharge_way="discount_id")
            db_session.add(recharge)
            db_session.flush()
            # update discount id
            Discount.query.filter(Discount.discount_id == id).update({Discount.is_used: True,
                                                                      Discount.used_time: now_time})
            db_session.commit()
            LOG.debug("discount id used by user id: <{0}>")
            # update user's exceed time
            ExprOrders.sync_user_exceed_time(user_id=user_id)
            return True, 200
        except Exception as e:
            db_session.rollback()
            em = "use discount id error. id: <{0}> user id<{1}>".format(id, user_id)
            LOG.exception(em)
            return False, 500

    @staticmethod
    def generate_discount(money, counts=1, code_len=8, valid_date=None):
        ''' 随机生成8位的优惠码 记录到数据库'''
        db_objs = []
        for count in range(counts):
            code_list = []
            # 0-9
            for i in range(10):
                code_list.append(str(i))
            # A-Z
            for i in range(65, 91):
                code_list.append(chr(i))
            # a-z
            for i in range(97, 123):
                code_list.append(chr(i))
            myslice = random.sample(code_list, code_len)
            verification_code = ''.join(myslice)
            db_obj = Discount(uid=str(uuid.uuid1()), discount_id=verification_code, money=money, gen_time=int(time.time()),
                              is_used=False, valid_date=valid_date, used_time=None, description=None)
            db_objs.append(db_obj)
        for db_obj in db_objs:
            db_session.add(db_obj)
            db_session.flush()
        db_session.commit()
        return {"result": "successful"}
        # return db_objs

    @staticmethod
    def get_discount():
        db_obj = Discount.query.filter(and_(Discount.is_used == False,
                                            Discount.is_allocation == False)).first()
        if not db_obj:
            LOG.exception("no avalid discount card can be use")
            return False, 500
        db_obj.is_allocation = True
        db_session.commit()
        return True, db_obj
