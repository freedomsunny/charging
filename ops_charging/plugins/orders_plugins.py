# encoding=utf-8
import uuid
import time
from ops_charging.db.models import db_session, Orders, Price, User, ConsumeLog
from sqlalchemy import and_

import ops_charging.plugins.orderinfo_plugins as orderinfo_plugins
import ops_charging.log as logging
from ops_charging.options import get_options
from ops_charging.plugins.expr_money_plugins import ExprOrders

LOG = logging.getLogger(__name__)

# not used
order_opts = [
    {"name": "order_Settlement",
     "default": "Settlemented",
     "type": str
     },
    {"name": "money_update_interval",
     "help": "update user's money interval in 86400 second.(1 day)",
     "default": 86400,
     "type": int
     },
]

options = get_options(order_opts)


class OrderAbout(object):
    @staticmethod
    def add_order(data):
        """添加订单"""
        data = orderinfo_plugins.GetOrderAbout(data)
        new_orders = []
        for r_name, used in data.resources.iteritems():
            if not used:
                continue
            # 检查订单是否存在
            check_orders = Orders.query.filter(and_(Orders.resource_id == data.resource_id,
                                                    Orders.project_id == data.project_id,
                                                    Orders.user_id == data.user_id,
                                                    Orders.resource_name == r_name,
                                                    Orders.status == None)).first()
            if check_orders:
                em = "order is already exist. resource id: <{0}> resource type: <{1}>".format(data.resource_id,
                                                                                              r_name)
                LOG.exception(em)
                continue
            # 获取单价
            price_type_obj = Price.query.filter(Price.name == r_name).first()
            if not price_type_obj:
                n_r_name = r_name.split("/")[-1]
                price_type_obj = Price.query.filter(Price.name == n_r_name).first()
            price_type = (price_type_obj.price_type if price_type_obj else None)
            order_object = Orders(str(uuid.uuid1()),
                                  start_time=data.time_stamp,
                                  end_time=data.end_time,
                                  resource_from=data.resource_from,
                                  resource_from_provider=data.resource_from_provider,
                                  off=data.off,
                                  used=used,
                                  resource_id=data.resource_id,
                                  resource_type=price_type,
                                  resource_name=r_name,
                                  project_id=data.project_id,
                                  project_name=data.project_name,
                                  user_id=data.user_id,
                                  resource=data.resource,
                                  user_name=data.user_name,
                                  order_type=data.order_type,
                                  log_time=int(time.time()),
                                  )
            #  订单类型-立即结算
            if data.order_type == options.order_immed:
                if not price_type_obj:
                    em = "can not found price type, order type is immediately. Please define first"
                    LOG.exception(em)
                    return {"code": 1, "message": em}
                else:
                    # get the order total used money
                    immed_order_money = ExprOrders.order_used_money(order_object, price_type_obj, immed=True)
                    if not immed_order_money:
                        continue
                    # 更新用户余额，添加消费记录
                    result = ExprOrders.update_user_money(immed_order_money, order_object)
                    if result.get("code") != 0:
                        return result
                    # 订单状态为已结算
                    order_object.status = options.order_Settlement
                    db_session.add(order_object)
                    db_session.flush()
            else:
                if price_type_obj:
                    new_orders.append(order_object)
        # 更新用户过期时间
        ExprOrders.expr_user_exceed_time(data.user_id, new_orders)
        # 添加到数据库
        for new_order in new_orders:
            db_session.add(new_order)
            db_session.flush()
            msg = "add order successful. resource_id: <{0}>".format(data.resource_id)
            LOG.debug(msg)
        db_session.commit()
        return {"code": 0, "message": ""}

    @staticmethod
    def delete_order(resource_id, end_time):
        """结算订单"""
        # check resource is it exist
        db_objs = Orders.query.filter(Orders.resource_id == resource_id).all()
        if not db_objs:
            em = "can not found resource_id <{0}>".format(resource_id)
            LOG.exception(em)
            return {"code": 1, "message": em}
        used_money = 0
        for db_obj in db_objs:
            db_obj.end_time = end_time
            db_obj.status = options.order_Settlement
            # 单条订单价格
            price_obj = Price.query.filter(Price.price_type == db_obj.resource_type).first()
            if not price_obj:
                em = "can not found price type, order type is immediately. Please define first"
                LOG.exception(em)
                continue
            order_money = ExprOrders.order_used_money(db_obj, price_obj, immed=True)
            if order_money:
                used_money += order_money
                # 更新用户余额,添加消费日志
                ExprOrders.update_user_money(used_money, db_obj)
        # 更新用户过期时间
        ret = ExprOrders.expr_user_exceed_time(db_obj.user_id)
        if not ret:
            em = "update user exceed time error. user_id <{0}>".format(db_obj.user_id)
            LOG.exception(em)
            return {"code": 1, "message": em}
        db_session.commit()
        return {"code": 0, "message": ""}

    @staticmethod
    def update_order(data, resource_id):
        """变更订单"""
        new_orders = []
        data = orderinfo_plugins.GetOrderAbout(data)
        for r_name, used in data.resources.iteritems():
            if not used:
                continue
            # 检查订单是否存在
            check_orders = Orders.query.filter(and_(Orders.resource_id == resource_id,
                                                    Orders.project_id == data.project_id,
                                                    Orders.user_id == data.user_id,
                                                    Orders.resource_name == r_name,
                                                    Orders.status == None)).first()


            if not check_orders:
                em = "order is not exist. resource id: <{0}> resource type: <{1}>".format(resource_id,
                                                                                          r_name)
                LOG.exception(em)
                continue

            # 获取单价
            price_type_obj = Price.query.filter(Price.name == r_name).first()
            if not price_type_obj:
                n_r_name = r_name.split("/")[-1]
                price_type_obj = Price.query.filter(Price.name == n_r_name).first()
            price_type = (price_type_obj.price_type if price_type_obj else None)

            # 结算订单
            check_orders.end_time = data.time_stamp
            order_money = ExprOrders.order_used_money(check_orders, price_type_obj, immed=True)
            # 更新用户余额，添加消费记录
            result = ExprOrders.update_user_money(order_money, check_orders)
            # if result.get("code") != 0:
            #     return result
            check_orders.status = options.order_Settlement
            # 添加新订单
            order_object = Orders(str(uuid.uuid1()),
                                  start_time=data.time_stamp,
                                  resource_from=data.resource_from,
                                  resource_from_provider=data.resource_from_provider,
                                  off=data.off,
                                  used=used,
                                  resource_id=resource_id,
                                  resource_type=price_type,
                                  resource_name=r_name,
                                  project_id=data.project_id,
                                  project_name=data.project_name,
                                  user_id=data.user_id,
                                  resource=data.resource,
                                  user_name=data.user_name,
                                  order_type=data.order_type,
                                  log_time=int(time.time()),
                                  )
            new_orders.append(order_object)
        # 更新用户过期时间
        ExprOrders.expr_user_exceed_time(data.user_id, new_orders)
        for new_order in new_orders:
            db_session.add(new_order)
            db_session.commit()
        return {"code": 0, "message": ""}

    @staticmethod
    def get_user_orders(user_id, status=None):
        # check user is it exist
        user = User.query.filter(User.user_id == user_id).first()
        if not user:
            em = "can not found user. user id: <{0}>".format(user_id)
            LOG.exception(em)
            return 0
        try:
            user_order = Orders.query.filter(and_(Orders.user_id == user_id),
                                             Orders.status == status).all()
            return user_order
        except Exception as e:
            em = "get user orders failed. user id: <{0}>. msg: <{1}>".format(user_id, e)
            LOG.exception(em)
            return {"error": [{"code": 400, "msg": "{0}".format(em)}]}

    @staticmethod
    def get_user_day_used(user_id):
        try:
            # check user is it exist
            user = User.query.filter(User.user_id == user_id).first()
            if not user:
                em = "can not found user. user id: <{0}>".format(user_id)
                LOG.exception(em)
                return 0
            user_day_used = ExprOrders.expr_day_used(user_id)
            if not user_day_used[0]:
                return False, 400
            return user_day_used[1]
        except Exception as e:
            em = "get user day used error. user id: <{0}>. msg: <{1}>".format(user_id, e)
            LOG.exception(em)
            return 0

    @staticmethod
    def expr_order_kinds_used(user_id):
        # check user is it exist
        user = User.query.filter(User.user_id == user_id).first()
        all_kinds = {}
        if not user:
            em = "can not found user. user id: <{0}>".format(user_id)
            LOG.exception(em)
            return 0
        try:
            # get user's all orders
            orders = Orders.query.filter(and_(Orders.user_id == user_id,
                                              Orders.resource_type != None,
                                              Orders.status == None)).all()
            if not orders:
                em = "can not found user's orders. user id: <{0}>".format(user_id)
                LOG.exception(em)
                return 0
            # get a user's all order kinds
            resource_kinds = set([s.resource_name for s in orders])
            # get a type's a data
            for resource_kind in resource_kinds:
                order_kinds = [s for s in orders if s.resource_name == resource_kind]
                price = Price.query.filter(Price.price_type == order_kinds[0].resource_type).first()

                all_kinds[resource_kind] = order_kinds[0]
                min_used = 0
                for order_kind in order_kinds:
                    # get a type's all data
                    min_use = ExprOrders.order_used_money(order_kind, price, immed=False)
                    if min_use:
                        min_used += min_use

                all_kinds[resource_kind].money = min_used * (24 * 60)
            return all_kinds
        except Exception as e:
            em = "get user consume error. user id: <{0}>. msg: <{1}>".format(user_id, e)
            LOG.exception(em)
            return {"error": [{"code": 400, "msg": "{0}".format(em)}]}

    @staticmethod
    def sync_user_et(user_id=None):
        ExprOrders.sync_user_exceed_time(user_id)

    @staticmethod
    def get_order_by_resource_id(resource_id):
        result = Orders.query.filter(Orders.resource_id == resource_id).first()
        db_session.close()
        if not result:
            # 该资源未找到
            return 404

        result = Orders.query.filter(and_(Orders.resource_id == resource_id,
                                          Orders.status == None)).first()
        db_session.close()

        if result:
            # 该资源正在计费
            return 200

        result = Orders.query.filter(and_(Orders.resource_id == resource_id,
                                          Orders.status == "Settlemented")).first()
        db_session.close()
        if result:
            # 该资源已结算
            return 302

        return 500
