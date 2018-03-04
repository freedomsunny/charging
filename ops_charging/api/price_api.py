# -*- coding:utf-8 -*-
from __future__ import unicode_literals
import json
import datetime
import tornado.web

from ops_charging.plugins.price_plugins import PriceOperation as price_api
from ops_charging.plugins.orders_plugins import OrderAbout as orders_api
from ops_charging.plugins.JsonResponses import BaseHander
from ops_charging.api.auth import auth as Auth

url_map = {
    r"/price/getprice$": 'Price',
}


class Price(BaseHander, Auth.BaseAuth):
    def get(self):
        ret = price_api.get_price()
        if not ret[0]:
            self.json_response(ret[1], result=ret[1])
        else:
            self.json_response(0, result=ret[1])
