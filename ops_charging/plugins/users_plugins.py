#!encoding=utf-8
from ops_charging.db.models import db_session, Orders, Price, User, RechargeLog, ConsumeLog
from sqlalchemy import and_
from ops_charging.utils import get_http, post_http, get_token
import ops_charging.log as logging
import uuid
import time
import json

from ops_charging.plugins.expr_money_plugins import ExprOrders
from ops_charging import cache
from ops_charging.service import manager
from ops_charging.options import get_options
from ops_charging.plugins.ocmdb_handle import CMDBHandle

LOG = logging.getLogger(__name__)
users_opts = [
    {"name": "exceed_time_notify",
     "default": 2,
     "help": "how many days notify user will be exceed ",
     "type": int
     },
    {"name": "wecat_api",
     "default": "http://122.115.54.249:8902/send_text_msg/",
     "help": "how many days notify user will be exceed ",
     "type": str
     },
    {"name": "dev_ops_userid",
     "default": ["e0469113b277424b8f8a8e73ef141fb6"],
     "help": "su yuan li's user id",
     "type": list
     },
    {"name": "send_msg2user_interval",
     "default": 1,
     "help": "send msg to user interval by days",
     "type": int
     },
    {"name": "check_time",
     "default": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
     "help": "send msg to user at work time",
     "type": list
     },
]
options = get_options(users_opts)


class UserOperate(manager.Manager):
    def __init__(self, *args, **kwargs):
        super(UserOperate, self).__init__()
        print "i am init"

    @staticmethod
    def add_user(data):
        project_id = data.get("tenant_id")
        project_name = data.get("_context_project_name")
        user_id = data.get("user_id")
        user_name = data.get('_context_user_name')
        id = str(uuid.uuid1())
        exist_user = User.query.filter(User.user_id == user_id).first()
        try:
            if not exist_user:
                db_users = User(id=id, user_id=user_id, user_name=user_name, project_id=project_id,
                                project_name=project_name, register_time=int(time.time()))
                db_session.add(db_users)
                db_session.commit()
                em = "add user: <{0}> success".format(user_name)
                LOG.debug(em)
                return {"success": [{"code": 200, "msg": "{0}".format(em), "data": db_users}]}
        except Exception as e:
                db_session.rollback()
                em = "add user: <{0}> failed msg: {1}".format(user_name, e)
                LOG.exception(em)
                return {"error": [{"code": 400, "msg": "{0}".format(em)}]}

    @staticmethod
    def add_user_recharge(user_id, user_name, total_fee, out_trade_no, trade_status, recharge_way):
        """method to update user money """
        # 用户冲值记录， 只要调用支付宝接口就生成。根据状态判断是否成功

        # check user is it exist
        user = User.query.filter(User.user_id == user_id).first()
        if not user:
            em = "can not found user. user id: <{0}>".format(user_id)
            LOG.exception(em)
            # return {"error": [{"code": 400, "msg": "{0}".format(em)}]}
            return 0

        uid = str(uuid.uuid1())
        log_time = int(time.time())
        try:
            # 记录冲值记录，默认状态为`failed`
            recharge_log = RechargeLog(uid, user_id, user_name, total_fee, log_time, out_trade_no, trade_status, recharge_way=recharge_way)
            db_session.add(recharge_log)
            db_session.commit()
            return {"success": [{"code": 200, "msg": ""}]}
        except Exception as e:
            db_session.rollback()
            em = "recharge for user <{0}> error. user id : <{1}>. msg: {2}".format(user.user_name, user_id, e)
            LOG.exception(em)
            return {"error": [{"code": 500, "msg": "{0}".format(em)}]}

    @staticmethod
    def update_user_recharge(async_data):
        """根据号in_trade_no（唯一订单号）来更新用户冲值记录的状态"""
        out_trade_no = async_data.get("out_trade_no")
        trade_status = async_data.get("trade_status")
        money = float(async_data.get("price"))
        try:
            # 更新用户余额（如果是成功的消息）
            if trade_status == "success":
                # 根据订单号从recharge_log表找用户user_id
                recharg = RechargeLog.query.filter(RechargeLog.out_trade_no == out_trade_no).first()
                if not recharg:
                    em = "can not fond user's user_id from table recharge_log"
                    return {"error": [{"code": 500, "msg": "{0}".format(em)}]}
                user_id = recharg.user_id
                user = User.query.filter(User.user_id == user_id).first()
                if not user:
                    em = "can not fond user user_id : <{0}>".format(user_id)
                    LOG.exception(em)
                    return 0
                user_money = user.money
                new_money = money + (float(user_money) if float(user_money) else 0)
                is_exceed = (True if new_money <= 0 else False)
                # up date user's money
                User.query.filter(User.user_id == user_id).update({User.money: new_money,
                                                                       User.is_exceed: is_exceed})
                db_session.commit()
                ExprOrders.sync_user_exceed_time(user_id=user_id)

            # 更新日志记录
            RechargeLog.query.filter(RechargeLog.out_trade_no == out_trade_no).update({RechargeLog.trade_status: trade_status})
            msg = "user <{0}> recharge money <{1}>".format(user_id, money)
            LOG.debug(msg)
            db_session.commit()
            # 同步数据到cmdb
            result = RechargeLog.query.filter(RechargeLog.out_trade_no == out_trade_no).first()
            CMDBHandle.syncdata2cmdb("recharge", result.uid)
            return {"success": [{"code": 200, "msg": ""}]}
        except Exception as e:
            db_session.rollback()
            em = "update user recharge failed with in_trade_no: <{0}> msg: {1}".format(out_trade_no, e)
            LOG.exception(em)
            return {"error": [{"code": 500, "msg": "{0}".format(em)}]}

    @staticmethod
    def get_user_recharge_log(user_id, recharge_way=None):
        """method to get user recharge recorde"""
        # check user is it exist
        user = User.query.filter(User.user_id == user_id).first()
        if not user:
            em = "can not found user. user id: <{0}>".format(user_id)
            LOG.exception(em)
            return 0
        try:
            if recharge_way:
                recharge_log = RechargeLog.query.filter(and_(RechargeLog.user_id == user_id,
                                                             RechargeLog.recharge_way == recharge_way)).all()
            else:
                recharge_log = RechargeLog.query.filter(RechargeLog.user_id == user_id).all()
            return recharge_log
        except Exception as e:
            em = "get user recharge log error. msg: <{0}>".format(e)
            LOG.exception(em)
            return {"error": [{"code": 400, "msg": "{0}".format(em)}]}

    @staticmethod
    def get_user_consume_log(user_id):
        # check user is it exist
        user = User.query.filter(User.user_id == user_id).first()
        if not user:
            em = "can not found user. user id: <{0}>".format(user_id)
            LOG.exception(em)
            return 0
        try:
            consume_log = ConsumeLog.query.filter(ConsumeLog.user_id == user_id).all()
            return consume_log
        except Exception as e:
            em = "get user consume error. user id: <{0}>. msg: <{1}>".format(user_id, e)
            return {"error": [{"code": 400, "msg": "{0}".format(em)}]}

    @staticmethod
    def expr_consume_kinds_used(user_id):
        # check user is it exist
        user = User.query.filter(User.user_id == user_id).first()
        all_kinds = {}
        if not user:
            em = "can not found user. user id: <{0}>".format(user_id)
            LOG.exception(em)
            return 0
        try:
            consume_log = ConsumeLog.query.filter(ConsumeLog.user_id == user_id).all()
            if not consume_log:
                em = "can not found user's consume log. user id: <{0}>".format(user_id)
                LOG.exception(em)
                return 0
            # get a user's all consume log
            resource_kinds = set([s.resource_name for s in consume_log])
            # get a type's a data
            for resource_kind in resource_kinds:
                all_kinds[resource_kind] = [s for s in consume_log if s.resource_name == resource_kind][0]
                # get a type's all data
                kind_data = [s for s in consume_log if s.resource_name == resource_kind]
                money = 0
                for kind in kind_data:
                    money += kind.money
                all_kinds[resource_kind].money = money
            return all_kinds
        except Exception as e:
            em = "get user consume error. user id: <{0}>. msg: <{1}>".format(user_id, e)
            return {"error": [{"code": 400, "msg": "{0}".format(em)}]}

    @staticmethod
    def get_user_money(user_id):
        now_time = int(time.time())
        used_money = 0
        # check user is it exist
        user = User.query.filter(User.user_id == user_id).first()
        if not user:
            em = "can not found user. user id: <{0}>".format(user_id)
            LOG.exception(em)
            return 0
        orders = Orders.query.filter(and_(Orders.user_id == user_id,
                                          Orders.status == None,
                                          Orders.resource_type != None)).all()
        for order in orders:
            order.end_time = now_time
            order.order_type = options.order_immed
            price = Price.query.filter(Price.price_type == order.resource_type).first()
            used = ExprOrders.order_used_money(order, price, immed=True)
            if used:
                used_money += used
        user.money = float(user.money) - used_money
        return user

    @staticmethod
    def get_user_exceed_time(user_id):
        user = User.query.filter(User.user_id == user_id).first()
        if not user:
            em = "can not found user. user id: <{0}>".format(user_id)
            LOG.exception(em)
            return {"error": [{"code": 400, "msg": "{0}".format(em)}]}
        if user.exceed_time:
            return user.exceed_time

    @staticmethod
    def get_user_info(user_id):
        user = User.query.filter(User.user_id == user_id).first()
        if not user:
            em = "can not found user. user id: <{0}>".format(user_id)
            LOG.exception(em)
            return {}
        return user

    # 周期检查用户超时时间，以微信方式通知用户
    # @manager.periodic_task
    @staticmethod
    def check_user_exceed_time(raise_on_error=True):
        try:
            admin_token = get_token()
            if not admin_token:
                em = "error: can not get admin token......."
                print em
                return False, 500
            time_h = int(time.strftime("%H", time.localtime()))
            redis_exceed_time = options.send_msg2user_interval * 24 * 60 * 60
            # 程序执行时间
            exec_time = options.check_time
            backend = cache.Backend()
            exceed_users = UserOperate.get_user_exceed_time_whecat()
            if not exceed_users[0]:
                return
            exceed_users = exceed_users[1]
            for Nday_user in exceed_users.get("exceed_Nday_users"):
                exceed_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(Nday_user.exceed_time))
                send_status = backend.get(Nday_user.user_id + "_send_status")
                if time_h in exec_time and not send_status:
                    task = u"您的账户可用时长不足{0}天，为避免影响业务，请即时充值。".format(options.exceed_time_notify)
                    ret = UserOperate.send_msg2wechat(admin_token, Nday_user.user_id, exceed_time_str, task, detail="")
                    if not ret:
                        # return ret[1]
                        em = "send exceed msg error. code: <{0}> user id: <{1}>".format(ret[1], Nday_user.user_id)
                        LOG.exception(em)
                        continue
                    backend.set(Nday_user.user_id + "_send_status", 1, redis_exceed_time)
            for exceed_user in exceed_users.get("exceed_users"):
                exceed_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(exceed_user.exceed_time))
                send_status = backend.get(exceed_user.user_id + "_send_status")
                # 已到期用户
                if time_h in exec_time and not send_status:
                    task = u"您的账户已到期，业务现已暂停。为避免资源被彻底销毁请即时充值。"
                    ret = UserOperate.send_msg2wechat(admin_token, exceed_user.user_id, exceed_time_str, task, detail="")
                    if not ret:
                        # return ret[1]
                        em = "send exceed msg error. code: <{0}> user id: <{1}>".format(ret[1], exceed_user.user_id)
                        LOG.exception(em)
                        continue
                    backend.set(exceed_user.user_id + "_send_status", 1, redis_exceed_time)
            return True, 200
        except Exception as e:
            em = "send mesage to wecat error . msg: {0}".format(e)
            print em
            return False, 500

    @staticmethod
    def send_msg2wechat(token, user_id, expire_time, task, detail=u""):
        if not token or not user_id:
            return False, 400
        try:
            headers = {'X-Auth-Token': token.strip(), 'Content-Type': 'application/json'}
            data = {"user_id": user_id,
                    "expire_time": expire_time,
                    "task": task,
                    "detail": detail,
                    }
            data = json.dumps(data)
            ret = post_http(url=options.wecat_api, data=data, headers=headers)
            if ret.status_code != 200:
                return False, ret.status_code
            ret = ret.json()
            if int(ret.get("code")) != 0:
                return False, 500
            return True, 200
        except Exception as e:
            em = "send mesage to wecat error . msg: {0}".format(e)
            LOG.exception(em)
            print em
            return False, 500

    # 获取超时用户及不足N天的用户
    @staticmethod
    def get_user_exceed_time_whecat():
        try:
            all_users = User.query.filter(User.is_exceed == True).all()
            if not all_users:
                em = "no one or more user can be found"
                LOG.exception(em)
            now_time = int(time.time())
            data = {}
            # 小于N天的用户
            n_day_time = now_time + (options.exceed_time_notify * 24 * 60 * 60)
            # 不足N天用户
            exceed_Nday_users = set()
            # 已到期用户
            exceed_users = set()

            for user in all_users:
                if user.exceed_time <= now_time:
                    exceed_users.add(user)
                elif user.exceed_time < n_day_time:
                    exceed_Nday_users.add(user)
            # exceed_Nday_users = map(list, exceed_Nday_users)
            # exceed_users = map(list, exceed_users)
            data["exceed_Nday_users"] = exceed_Nday_users
            data["exceed_users"] = exceed_users
            return True, data
        except ExprOrders as e:
            em = "get exceed_user error. msg: <{0}>".format(e)
            LOG.exception(em)
            return False, 500

    # 周期更新用户相关信息
    # @manager.periodic_task()
    @staticmethod
    def cycle_update_user():
        ""
        try:
            now_time = int(time.time())
            User.query.filter(User.exceed_time < now_time).update({User.is_exceed: True})
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            em = "cycle update user error. msg: <{0}>".format(e)
            LOG.exception(em)

    @manager.periodic_task
    def cycle_exec_task(self):
        """周期任务"""
        UserOperate.cycle_update_user()

    @staticmethod
    def get_user_exceed_time_devops():
        ret = UserOperate.get_user_exceed_time_whecat()
        if not ret[0]:
            return False, ret[1]
        data = {}
        exceed_Nday_users = [s.user_id for s in ret[1].get("exceed_Nday_users") if s]
        exceed_users = [s.user_id for s in ret[1].get("exceed_users") if s]
        data["exceed_Nday_users"] = exceed_Nday_users
        data["exceed_users"] = exceed_users
        return True, data

    @staticmethod
    def get_already_exceed_user(start_time=None, end_time=None, user_id=None):
        try:
            now_time = int(time.time())
            exceed_users = User.query.filter(and_(User.is_destroy == False,
                                                  User.is_exceed == True)).all()
            exceed_users = [s for s in exceed_users if s.exceed_time <= now_time]
            if start_time and not end_time:
                exceed_users = [s for s in exceed_users if s.exceed_time and int(s.exceed_time) > int(start_time)]
                return True, exceed_users
            if end_time and not start_time:
                exceed_users = [s for s in exceed_users if s.exceed_time and int(s.exceed_time) < int(end_time)]
                return True, exceed_users
            if start_time and end_time:
                exceed_users = [s for s in exceed_users if s.exceed_time and int(s.exceed_time) < int(end_time) and int(s.exceed_time) > int(start_time)]
                return True, exceed_users
            if user_id:
                exceed_users = [s for s in exceed_users if s.user_id == user_id]
            return True, exceed_users
        except Exception as e:
            em = "get already exceed user error. msg: <{0}>".format(e)
            LOG.exception(em)
            return False, 500

    @staticmethod
    def change_user_resource_status(user_id, status):
        """status: is a boolean value. True or False"""
        try:
            User.query.filter(User.user_id == user_id).update({User.is_destroy: status})
            db_session.commit()
            return True, 200
        except Exception as e:
            db_session.rollback()
            em = "update user's status error msg: <{0}>".format(e)
            LOG.exception(em)
            return False, 500
