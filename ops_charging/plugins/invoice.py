#!encoding=utf-8
from __future__ import unicode_literals

from ops_charging.db.models import db_session, Invoice, RechargeLog
from sqlalchemy import and_
import json
import uuid
import time
from tornado.httpclient import HTTPError

from ops_charging.utils import get_http, post_http, get_token, ConvertTime2Int, get_nowtime
import ops_charging.log as logging
from ops_charging import cache
from ops_charging.service import manager
from ops_charging.options import get_options

LOG = logging.getLogger(__name__)
invoice_opts = [
    # 不能开取发票的充值类型
    {"name": "reject_recharge_type",
     "default": ["deveops",
                 "discount_id",
                 ],
    #  "default": [],
     "type": list
     },

]
options = get_options(invoice_opts)


class InvoiceOperate(object):

    @staticmethod
    def add_invoice(data, upfile_uuid):
        # 计算所有充值记录之和
        if not data.orders:
            em = "no any more orders id"
            LOG.exception(em)
            raise HTTPError(400, em)
        money = 0
        for order in data.orders:
            # 查找所有充值记录
            recharge = RechargeLog.query.filter(RechargeLog.uid == order).first()
            if not recharge:
                em = "user id: <{0}>. can not found recharge log. id: <{1}>".format(data.user_id, order)
                LOG.exception(em)
                continue
            if recharge.trade_status != "success" :
                em = "user id: <{0}>. recharge log is not success. id: <{1}>".format(data.user_id, order)
                LOG.exception(em)
                continue
            if recharge.is_invoiced:
                em = "user id: <{0}>. recharge log is invoiced. id: <{1}>".format(data.user_id, order)
                LOG.exception(em)
                continue
            # 不允许开取发票的类型
            if recharge.recharge_way in options.reject_recharge_type:
                em = "user id: <{0}>. recharge type is not allowed id: <{1}>".format(data.user_id, order)
                LOG.exception(em)
                continue

            money += float(recharge.money)
            # 更新充值记录为已开发票
            RechargeLog.query.filter(RechargeLog.uid == order).update({RechargeLog.is_invoiced: True})
            db_session.flush()
        if money <= 0:
            em = "user id: <{0}>. apply invoice error. user's money is le 0".format(data.user_id)
            LOG.exception(em)
            raise HTTPError(500, "server internal error")
        # add database
        invoice_obj = Invoice(uuid=data.invoice_uuid,
                            title=data.title,
                            status=options.invoice_status.get("verifying"),
                            post_address=data.post_address,
                            post_user=data.post_user,
                            post_phone=data.post_phone,
                            money=money,
                            title_type=data.title_type,
                            title_mode=data.title_mode,
                            context=data.context,
                            corporation_name=data.corporation_name,
                            taxpayer_dentity=data.taxpayer_dentity,
                            register_address=data.register_address,
                            register_phone=data.register_phone,
                            deposit_bank=data.deposit_bank,
                            deposit_account=data.deposit_account,
                            user_name=data.user_name,
                            user_id=data.user_id,
                            application_date=get_nowtime(),
                            description=data.description,
                            recharge_uuids=','.join(data.orders),
                            upfile_uuid=upfile_uuid,
                            )
        db_session.add(invoice_obj)
        db_session.commit()
        return invoice_obj

    @staticmethod
    def update_invoice(data):
        # 计算所有充值记录之和
        # if not data.get("orders"):
        #     em = "no any more orders id"
        #     LOG.exception(em)
        #     raise HTTPError(400, em)
        # 确认是发票记录是否存在
        invoice_obj = Invoice.query.filter(Invoice.uuid == data.invoice_uuid).first()
        if not invoice_obj:
            em = "can not found any more invoice with id: <{0}>".format(data.invoice_uuid)
            LOG.exception(em)
            raise HTTPError(400, em)
        # # 如果发票状态为邮寄，也不能修改
        # if invoice_obj.status == options.invoice_status.get("posted"):
        #     em = "invoice is posted. can not change"
        #     LOG.exception(em)
        #     raise HTTPError(400, em)
        # update database

        Invoice.query.filter(Invoice.uuid == data.invoice_uuid).update({Invoice.status: data.status,
                                                                        Invoice.complete_date: data.complete_date,
                                                                        Invoice.description: data.description,
                                                                        Invoice.logistics_no: data.logistics_no,
                                                                        Invoice.logistics_company: data.logistics_company,
                                                                        Invoice.invoice_no: data.invoice_no
                                                                        })
        db_session.commit()
        return True

    @staticmethod
    def delete_invoice(uuid):
        """取消发票"""
        invoice_obj = Invoice.query.filter(Invoice.uuid == uuid).first()
        if not invoice_obj:
            em = "can not found invoice with uuid <{0}>".format(uuid)
            LOG.exception(em)
            raise HTTPError(400, em)

        # 如果发票状态为已邮寄，则不能取消和删除
        if invoice_obj.status == options.invoice_status.get("posted"):
            em = "invoice is posted. can not delete"
            LOG.exception(em)
            raise HTTPError(400, em)
        # 更新充值记
        if invoice_obj.recharge_uuids:
            recharge_ids = invoice_obj.recharge_uuids.split(",")
            for recharge_id in recharge_ids:
                RechargeLog.query.filter(RechargeLog.uid == recharge_id).update({RechargeLog.is_invoiced: False})
                db_session.flush()
        invoice_obj.deleted = True
        db_session.commit()
        return invoice_obj

    @staticmethod
    def get_invoice(user_id, uuid=None, status=None, deleted=False):
        if uuid:
            invoice_obj = Invoice.query.filter(and_(Invoice.uuid == uuid,
                                                    Invoice.user_id == user_id,
                                                    Invoice.deleted == deleted)).first()
            return invoice_obj
        if user_id:
            invoice_obj = Invoice.query.filter(and_(Invoice.user_id == user_id,
                                                    Invoice.deleted == deleted)).all()
            return invoice_obj
        if status:
            invoice_obj = Invoice.query.filter(and_(Invoice.status == status,
                                                    Invoice.user_id == user_id,
                                                    Invoice.deleted == deleted)).all()
            return invoice_obj


class InvoiceData(object):
    """用户在页面提交新订单时的数据"""
    def __init__(self, data, user_context):
        # 用户选择的所有订单ID
        self.orders = (data.get_argument('orderList' "").split(",") if data.get_argument('orderList' "") else [])
        self.invoice_uuid = data.get_argument('invoice_uuid', str(uuid.uuid1()))
        # self.invoice_uuid = str(uuid.uuid1())
        self.logistics_no = data.get_argument('logistics_no', "")
        self.title = data.get_argument("title", "")
        self.status = data.get_argument("status", "")
        self.post_address = data.get_argument("post_address", "")
        self.post_user = data.get_argument("post_user", "")
        self.post_phone = data.get_argument("post_phone", "")
        self.money = data.get_argument("money", "")
        self.invoice_no = data.get_argument("invoice_no", "")
        self.title_type = data.get_argument("title_type", "")
        self.title_mode = data.get_argument("title_mode", "")
        self.context = data.get_argument("context", "")
        self.corporation_name = data.get_argument("corporation_name", "")
        self.taxpayer_dentity = data.get_argument("taxpayer_dentity", "")
        self.register_address = data.get_argument("register_address", "")
        self.register_phone = data.get_argument("register_phone", "")
        self.deposit_bank = data.get_argument("deposit_bank", "")
        self.deposit_account = data.get_argument("deposit_account", "")
        self.complete_date = data.get_argument("complete_date", "")
        self.description = data.get_argument("description", "")
        self.user_name = user_context.get("user").get("user").get("name")
        self.user_id = user_context.get("user_id")


class InvoiceDataCMDB(object):
    """cmdb返回的数据解析"""
    def __init__(self, data):
        self.status = data['property'].get("status")
        self.complete_date = get_nowtime()
        self.description = data['property'].get("description")
        self.invoice_uuid = data.get("uuid")
        self.logistics_no = data['property'].get("logistics_no")
        self.logistics_company = data['property'].get("logistics_company")
        self.invoice_no = data['property'].get("invoice_no")

