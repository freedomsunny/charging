#encoding=utf-8
from ops_charging.db.models import db_session, Orders, Price, User, ConsumeLog
from sqlalchemy import and_
import time
import uuid
import time
import copy

from ops_charging.plugins.ocmdb_handle import CMDBHandle
import ops_charging.log as logging
import ops_charging.plugins.orderinfo_plugins as orderinfo_plugins
from ops_charging.options import get_options

LOG = logging.getLogger(__name__)

options = get_options()


class ExprOrders(object):
    @staticmethod
    def expr_user_exceed_time(user_id, new_orders=None):
        """计算用户过期时间"""
        # user_id     用户唯一ID
        # new_order   新进来的订单，列表中包含数据库对象[db_obj1, db_obj2, db_obj3, .....]

        min_used_money = 0
        total_used_money = 0
        now_time = int(time.time())
        user = User.query.filter(User.user_id == user_id).first()
        if not user:
            em = "can not found user. user id: <{0}>".format(user_id)
            LOG.exception(em)
            return {"code": 1, "message": em}
        orders = Orders.query.filter(and_(Orders.user_id == user_id,
                                          Orders.status == None,
                                          Orders.resource_type != None)).all()
        for order in orders:
            price = Price.query.filter(Price.price_type == order.resource_type).first()

            print "start time=======", order.start_time
            print "end time=======", order.end_time
            # 结束时间为当前时间
            order.end_time = now_time
            # 获取订单总使用金额
            total_used = ExprOrders.order_used_money(order, price, immed=True)
            if total_used:
                total_used_money += total_used
            # 获取订单每分钟使用金额
            min_used = ExprOrders.order_used_money(order, price, immed=False)
            if min_used:
                min_used_money += min_used
            order.end_time = None
        if new_orders:
            for new_order in new_orders:
                price = Price.query.filter(Price.price_type == new_order.resource_type).first()
                if price:
                    # 获取新订单每分钟使用金额
                    min_used = ExprOrders.order_used_money(new_order, price, immed=False)
                    if min_used:
                        min_used_money += min_used

        # 当前余额 - 之前订单使用总和 = 可用余额
        vaild_money = float(user.money) - total_used_money
        # 余额小于0，直接更新为过期
        if vaild_money <= 0:
            if not user.is_exceed:
                User.query.filter(User.user_id == user_id).update({User.is_exceed: True,
                                                                   User.exceed_time: now_time})
                db_session.flush()
                em = "user available money le 0. user is exceed with user id: <{0}>".format(user_id)
                LOG.debug(em)
        else:
            # 可用余额 / 每分钟使用量 * 60 = 可用秒数
            if min_used_money > 0:
                valid_use_sec = (vaild_money / min_used_money) * 60
                # 过期时间 = 当前时间 + 可用秒数
                user_exceed_time = now_time + valid_use_sec
                User.query.filter(User.user_id == user_id).update({User.exceed_time: user_exceed_time})
                db_session.flush()
                em = "update user's exceed time to <{0}> with user id <{1}>".format(user_exceed_time, user_id)
                LOG.debug(em)

        # 用户现在过期状态为`已过期`，如果无订单，余额大于0，更新用户过期状态为`未过期`
        if user.is_exceed:
            if not orders:
                User.query.filter(User.user_id == user_id).update({User.exceed_time: None,
                                                                   User.is_exceed: False})
                db_session.flush()
        db_session.commit()
        return True

    @staticmethod
    def expr_day_used(user_id, resource_type=None, status=None):
        """
        this method expr user how much day used 
        """
        try:
            min_used = 0
            orders = Orders.query.filter(and_(Orders.user_id == user_id,
                                              Orders.resource_type != None,
                                              Orders.status == status)).all()
            if not orders:
                em = "not found user's order. user id: <{0}>".format(user_id)
                LOG.exception(em)
                return False, 400
            for order in orders:
                price = Price.query.filter(Price.price_type == order.resource_type).first()
                min_money = ExprOrders.order_used_money(order, price, immed=False)
                if min_money:
                    min_used += min_money
            day_used = min_used * (24 * 60)
            return True, {"user_id": user_id, "day_used": day_used}
        except Exception as e:
            em = "error can not expr user's exceed time. msg: {0}".format(e)
            LOG.exception(em)
            return False, 500

    @staticmethod
    def order_used_money(order, price, immed=False):
        """ 
        this method to expr how much used by a order(every minute money.is a single order)
        :param order: order db object
        :param price: price db object
        immed : order type is the immed pay
        :return: float: money use
        """
        try:
            # get order about
            order_info = orderinfo_plugins.GeTOrderAboutFromDB(order, price)
            # get order's off  add by huangyingjun 2017/08/4
            order_off = 1
            if order.off is not None:
                order_off = float(order.off)
            # if immed expr order total used money. else expr every minute money
            if immed:
                order_money = order_info.used_minute * (float(order_info.order_used) / order_info.price_unit *
                              ((float(order_info.price_price) / (order_info.price_time * 60)) * order_off))
            else:
                order_money = (float(order_info.order_used) / order_info.price_unit) * ((float(order_info.price_price) /
                              (order_info.price_time * 60)) * order_off)
            return order_money
        except Exception as e:
            em = "expr order failed. msg: {0}".format(e)
            LOG.exception(em)
            return False

    @staticmethod
    def update_user_money(money, order):
        """
        this method to update user's money(order's money)
        :param order:  db object with order info
        :return: 
        """
        try:
            if float(money) <= 0:
                return {"code": 0, "message": ""}
            user = User.query.filter(User.user_id == order.user_id).first()
            if not user:
                em = "can not found user id: <{0}>".format(order.user_id)
                LOG.exception(em)
                return False
            user.money = (float(user.money) if float(user.money) else 0)
            new_money = user.money - money
            if new_money < 0 and order.order_type == options.order_immed:
                em = "user have no enough money. user id: <{0}> resource id: <{1}>  " \
                     "resource name: <{2}>".format(order.user_id,
                                                   order.resource_id,
                                                   order.resource_name)
                LOG.exception(em)
                return {"code": 1, "message": em}
            User.query.filter(User.user_id == order.user_id).update({User.money: new_money})
            db_session.flush()
            msg = "update user <{0}> money from <{1}> to <{2}>".format(user.user_id,
                                                                       user.money,
                                                                       new_money)
            LOG.debug(msg)
            # add log
            consume_log = ConsumeLog(str(uuid.uuid1()),
                                     order.user_id,
                                     order.user_name,
                                     order.project_id,
                                     order.resource_name,
                                     order.resource_type,
                                     order.resource_id,
                                     order.start_time,
                                     order.end_time,
                                     money,
                                     int(time.time()),
                                     resource_from=order.resource_from,
                                     order_uid=order.uid,
                                     details=order.resource)
            db_session.add(consume_log)
            db_session.commit()
            # 实时同步数据到cmdb
            CMDBHandle.syncdata2cmdb("consume", consume_log.uid)
            return {"code": 0, "message": ""}
        except Exception as e:
            db_session.rollback()
            em = "update user money failed. user id: <{0}> " \
                 "resource id: <{1}> resource name: <{2}> msg: <{3}>".format(order.user_id,
                                                                             order.resource_id,
                                                                             order.resource_name,
                                                                             e)
            LOG.exception(em)
            return {"code": 1, "message": em}

    @staticmethod
    def expr_kind_order_money(user_id):
        """method to get every order kind money how many use"""
        orders = {}
        # get user's all order
        orders_obj = Orders.query.filter(and_(Orders.user_id == user_id,
                                              Orders.resource_type != None,
                                              Orders.status == None)).all()
        if not orders_obj:
            em = "not found user's order. id. ID: <{0}>".format(user_id)
            LOG.exception(em)
            return 0
        # get all order resource kinds
        try:
            order_kinds = set([k.resource_name for k in orders_obj])
            for order_kind in order_kinds:
                # 每种类型的订单
                kinds = [s for s in orders_obj if s.resource_name == order_kind]
                price = Price.query.filter(Price.price_type == kinds[0].resource_type).first()
                if not price:
                    em = "can not found price info "
                    LOG.exception(em)
                    return {"error": [{"code": 500, "msg": "{0}".format(em)}]}
                min_used = 0
                used = 0
                for kind in kinds:
                    min_use = ExprOrders.order_used_money(kind, price, immed=False)
                    if min_use:
                        min_used += min_use
                    used += kind.used
                day_used = used * (24 * 60)
                orders[order_kind] = {"money": day_used,
                                      "used": used}
            return orders
        except Exception as e:
            em = "expr kind order money error msg: <{0}>".format(e)
            LOG.exception(em)
            return {"error": [{"code": 500, "msg": "{0}".format(em)}]}

    @staticmethod
    def sync_user_exceed_time(user_id=None):
        """数据同步，根据用户当前订单及余额，更新用户超时时间"""
        try:
            now_time = int(time.time())
            if not user_id:
                all_users = User.query.filter().all()
            else:
                all_users = User.query.filter(User.user_id == user_id).all()
            for user in all_users:
                total_used = 0
                min_used = 0
                orders = Orders.query.filter(and_(Orders.user_id == user.user_id,
                                                  Orders.status == None,
                                                  Orders.resource_type)).all()
                # 如果没有订单，余额大于0，更新过期时间为空，未过期
                if not orders and float(user.money) > 0:
                    User.query.filter(User.user_id == user.user_id).update({User.is_exceed: False,
                                                                            User.exceed_time: None,
                                                                            })
                    db_session.flush()
                for order in orders:
                    order.end_time = now_time
                    order.order_type = options.order_immed
                    price = Price.query.filter(Price.price_type == order.resource_type).first()
                    if not price:
                        em = "can not found price type. price type: <{0}>".format(order)
                        LOG.exception(em)
                        return False
                    used = ExprOrders.order_used_money(order, price, immed=True)
                    if used:
                        total_used += used
                        order.end_time = None
                if total_used > float(user.money):
                    if not user.is_exceed:
                        User.query.filter(User.user_id == user.user_id).update({User.is_exceed: True,
                                                                                User.exceed_time: now_time,
                                                                            })
                    db_session.flush()
                else:
                    for order in orders:
                        price = Price.query.filter(Price.price_type == order.resource_type).first()
                        used = ExprOrders.order_used_money(order, price, immed=False)
                        if used:
                            min_used += used
                    if total_used > 0 and min_used > 0:
                        new_money = float(user.money) - total_used
                        valid_use_sec = new_money / min_used * 60
                        user_exceed_time = valid_use_sec + now_time
                        User.query.filter(User.user_id == user.user_id).update({User.exceed_time: user_exceed_time,
                                                                                User.is_exceed: False})
                        db_session.flush()
                        em = "update <{0}> user's exceed time to <{1}>".format(user.user_id, user_exceed_time)
                        LOG.debug(em)
                print "==================finish one. user_id: <{0}>==============================".format(user.user_id)
            db_session.commit()
        except ExprOrders as e:
            db_session.rollback()
            print "error. user_id==========>>>, ", user.user_id
            print e
