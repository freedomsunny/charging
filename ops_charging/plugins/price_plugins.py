import uuid
import time
from ops_charging.db.models import db_session, Orders, Price, User
from sqlalchemy import and_

import ops_charging.plugins.orderinfo_plugins as orderinfo_plugins
import ops_charging.log as logging
from ops_charging.options import get_options


LOG = logging.getLogger(__name__)

# not used
order_opts = [
    {"name": "testaaaaaaa1aaaa",
     "default": "111111111",
     "type": str
     },

]

options = get_options(order_opts)


class PriceOperation(object):

    def __init__(self):
        pass

    @staticmethod
    def get_price():
        try:
            prices = Price.query.filter().all()
            if not prices:
                em = "not any more prices....."
                LOG.exception(em)
                return False, 500
            return True, prices
        except Exception as e:
            em = "get price error..........msg: <{0}>".format(e)
            LOG.exception(em)
            return False, em

    def update_price(self, **kwargs):
        pass


