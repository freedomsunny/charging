# -*- coding:utf-8 -*-
from __future__ import unicode_literals
import json
import datetime
import tornado.web
import uuid

from ops_charging.db.models import get_uuid, Invoice
from ops_charging.options import get_options
from ops_charging.plugins.file_upload import FileUploadOperate
from ops_charging.plugins.invoice import InvoiceData, InvoiceOperate, InvoiceDataCMDB
from ops_charging.plugins.JsonResponses import BaseHander
from ops_charging.api.auth import auth as Auth
from ops_charging.plugins.ocmdb_handle import CMDBHandle


url_map = {
    r"/invoice$": 'InvoiceAPI',
    r"/hookcallback": "HookCallBack",
    r"/checkauthfile": "CheckAuthFile",

}

options = get_options()


class InvoiceAPI(BaseHander, Auth.BaseAuth):
    def post(self):
        """add invoice"""
        data_obj = InvoiceData(self, self.context)
        invoice_uuid = self.get_argument("title", "")
        title_type = self.get_argument("title_type")
        # 抬头类型为公司、开票方式为增值税。认证信息使用之前的信息
        if invoice_uuid and title_type == "increase":
            # # 检查之前的认证信息
            # file_result = FileUploadOperate.check_is_uploaded(user_id)
            # for status in file_result.values():
            #     # 其中任意一个文件没有审核成功，则不能使用之前的信息
            #     if status != "passed":
            #         self.write(file_result)
            #         return file_result
            invoice_obj = Invoice.query.filter(Invoice.uuid == invoice_uuid).first()
            if not invoice_obj:
                self.write(400)
                return
            upfile_uuid = invoice_obj.upfile_uuid
        else:
            # 保存审核文件文件
            uesr_full_path = options.upload_file_path + self.context.get("user_id") + "/"
            upfile_uuid = FileUploadOperate.save_file(self.request.files, uesr_full_path, self.context)
        # save base info
        result = InvoiceOperate.add_invoice(data_obj, upfile_uuid)
        self.json_response(result=result)

    def get(self):
        """get invoice"""
        user_id = self.context.get("user_id")
        invoice_uuid = self.get_argument('invoice_uuid', "")
        status = self.get_argument('status', "")
        result = InvoiceOperate.get_invoice(user_id, uuid=invoice_uuid, status=status)
        self.json_response(result=result)


    def delete(self):
        invoice_uuid = self.get_argument('invoice_uuid', "")
        result = InvoiceOperate.delete_invoice(invoice_uuid)
        self.json_response(result=result)


class HookCallBack(BaseHander):
    """在cmdb中编辑后，cmdb回调告诉是哪条数据进行了修改(uuid)，通过uuid从cmdb获取数据，并更新到本地"""
    def get(self):
        cmdb_uuid = self.get_argument('uuid', "")
        # 从cmdb中获取数据
        data = CMDBHandle.get_physical_info(cmdb_uuid=cmdb_uuid)
        if not data[0]:
            self.set_status(data[1])
        print data[1]
        data = InvoiceDataCMDB(data[1])
        # 更新发票信息
        InvoiceOperate.update_invoice(data)


class CheckAuthFile(BaseHander, Auth.BaseAuth):
    """检查用户审核文件是否上传"""
    def get(self):
        user_id = self.context.get("user_id")
        result = FileUploadOperate.check_is_uploaded(user_id)
        self.write(result)

