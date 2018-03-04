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
order_tencent_opts = [
]
options = get_options(order_tencent_opts)


class TencentOrders(object):
    @staticmethod
    def add_order(data):
        """添加订单"""
        data = orderinfo_plugins.GetOrderAbout(data)
        for r_name, used in data.resources.iteritems():
            if not used:
                continue
            order_object = Orders(str(uuid.uuid1()),
                                  start_time=data.time_stamp,
                                  end_time=data.end_time,
                                  resource_from=data.resource_from,
                                  resource_from_provider=data.resource_from_provider,
                                  off=data.off,
                                  used=used,
                                  resource_id=data.resource_id,
                                  resource_name=r_name,
                                  project_id=data.project_id,
                                  project_name=data.project_name,
                                  user_id=data.user_id,
                                  resource=data.resource,
                                  user_name=data.user_name,
                                  order_type=data.order_type,
                                  log_time=int(time.time()),
                                  status=options.order_Settlement,
                                  )
            if data.money <= 0:
                em = "tencent order. money can not le 0"
                LOG.exception(em)
                continue
            # 更新用户余额，添加消费记录
            result = ExprOrders.update_user_money(data.money, order_object)
            if result.get("code") != 0:
                return result
                # 订单状态为已结算
            db_session.add(order_object)
            db_session.flush()
        # 更新用户过期时间
        ExprOrders.expr_user_exceed_time(data.user_id)
        db_session.commit()
        return {"code": 0, "message": ""}
