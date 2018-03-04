# -*- coding:utf-8 -*-
from __future__ import unicode_literals
import json
import tornado.web

from ops_charging.plugins.discount import DiscountOperate
from ops_charging.plugins.JsonResponses import BaseHander
from ops_charging.api.auth import auth as Auth


url_map = {
    r"/discount/add$": 'Discount',
    r"/discount/get$": 'Discount',

}


class Discount(BaseHander, Auth.BaseAuth):

    # def post(self):
    #     """add discount id"""
    #     data = json.loads(self.request.body)
    #     money = data.get("money")
    #     discount_id = data.get("discount_id")
    #     valid_date = data.get("valid_date")
    #     description = data.get("description")
    #     ret = DiscountOperate.add_discount(discount_id, money, valid_date, self.context, description)
    #     if not ret[0]:
    #         self.set_status(ret[1])
    #         return
    #     self.write({"code": 200, "message": "Add discount id Successful. id: <{0}>".format(discount_id)})


    def post(self):
        """add discounts"""
        data = json.loads(self.request.body)
        moeny = data.get("money")
        counts = data.get("counts")
        valid_date = data.get("valid_date")
        # must be admin token
        if not self.context.get("user").get("admin"):
            self.set_status(500)
            return
        ret = DiscountOperate.generate_discount(moeny, counts, valid_date=valid_date)
        self.json_response(result=ret, code=0)

    def put(self):
        """use discount id"""
        data = json.loads(self.request.body)
        discount_id = data.get("discount_id")
        ret = DiscountOperate.use_discount(id=discount_id, user_context=self.context)
        if not ret[0]:
            self.set_status(ret[1])
            return
        self.write({"code": 200, "message": "used discount id Successful. id: <{0}>".format(discount_id)})

    def get(self):
        """get discount"""
        # must be admin token
        if not self.context.get("user").get("admin"):
            self.set_status(500)
            return
        ret = DiscountOperate.get_discount()
        if not ret[0]:
            self.set_status(500)
            self.json_response(result={}, code=502)
            return
        self.json_response(result=ret[1], code=0)
