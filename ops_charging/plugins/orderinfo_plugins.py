import ops_charging.log as logging
import time
from ops_charging.options import get_options

LOG = logging.getLogger(__name__)

options = get_options()

class GetOrderAbout(object):
    def __init__(self, data):
        """
        this method to parser http json request data
        :param data: http request json data
        """
        if not isinstance(data, dict):
            raise ValueError("parameter `data` must dict type")
        self.time_stamp = int(time.mktime(time.strptime(data.get("timestamp")[:19], '%Y-%m-%d %H:%M:%S')))
        if data.get("end_time"):
            self.end_time = int(time.mktime(time.strptime(data.get("end_time")[:19], '%Y-%m-%d %H:%M:%S')))
        else:
            self.end_time = None
        self.resource_from = data.get('resource_from')
        self.resource_from_provider = data.get('resource_from_provider')
        self.resource_id = data.get('resource_id')
        self.project_name = data.get("_context_project_name")
        self.user_id = data.get("user_id")
        self.off = data.get("off")
        self.project_id = data.get("tenant_id")
        self.resource = data.get("resource")
        self.order_type = (data.get("order_type") if data.get("order_type") else 2)
        self.user_name = data.get("_context_user_name")
        self.resources = data.get("resources")
        self.resource_from_provider = data.get("resource_from_provider")
        self.resource_from = data.get("resource_from")
        self.money = data.get("money")
        self.all_data = data


class GeTOrderAboutFromDB(object):
    def __init__(self, order, price):
        """
        method to parser order and price info from db
        :param order: order db object
        :param price: price db object
        """
        if not order.used or not float(order.used):
            em = "resource is not used. resource id: <{0}>. resource name :<{1}>".format(order.resource_id,
                                                                                         price.name)
            LOG.exception(em)
            raise ValueError(em)
        if not price.unit or not float(price.unit):
            em = "price.unit is not define. price type: <{0}>".format(price.price_type)
            LOG.exception(em)
            raise ValueError(em)
        if not price.price or not float(price.price):
            em = "price.price is not define. price type: <{0}>".format(price.price_type)
            LOG.exception(em)
            raise ValueError(em)
        if not price.time or not float(price.time):
            em = "price.time is not define. price type: <{0}>".format(price.price_type)
            LOG.exception(em)
            raise ValueError(em)
        if order.end_time and order.start_time:
            if int(order.end_time) <= int(order.start_time):
                em = "order's end_time can not be le start_time. resource id: <{0}>".format(order.resource_id)
                LOG.exception(em)
                raise ValueError(em)
        self.order_used = order.used
        self.price_unit = price.unit
        self.price_price = price.price
        self.price_time = price.time
        self.start_time = order.start_time
        self.end_time = order.end_time
        if self.end_time:
            self.used_minute = float((self.end_time - self.start_time) / 60)
        else:
            self.used_minute = 1
