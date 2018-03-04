#!encoding=utf-8
import shutil
import uuid
import os
import time

from ops_charging.db.models import db_session, UploadLog, Invoice
from sqlalchemy import and_
from ops_charging.utils import get_http, post_http, get_token, ConvertTime2Int
import ops_charging.log as logging
from ops_charging import cache
from ops_charging.service import manager
from ops_charging.options import get_options

LOG = logging.getLogger(__name__)
file_upload_opts = [

]
options = get_options(file_upload_opts)


class FileUploadOperate(object):
    """tornado upload/download file operate"""
    @staticmethod
    def save_file(files, file_path, user_info):
        isExists = os.path.exists(file_path)
        if not isExists:
            os.makedirs(file_path)
        if not files:
            return None
        # 添加到数据库
        db_obj = UploadLog(str(uuid.uuid1()),
                           user_info.get("user_id"),
                           user_info.get("user").get("user").get("name"),
                           int(time.time()),
                           )
        for file in files:
            # 原始文件名
            source_fname = files.get(file)[0].get("filename")
            # 生成新的文件名, 返回完整路径
            full_file = FileUploadOperate.gen_file_name(file_path, source_fname)
            with open(full_file, "wb") as f:
                f.write(files.get(file)[0].get("body"))
            em = "save {0} to path: {1}".format(file, full_file)
            LOG.info(em)
            # 文件路径入库为url格式：http://172.16.68.75:8900/file?path=/data/upload/xxxxx/xxxx.jpg
            file_full_url = "http://" + str(options.float_ip) + ":" + str(options.api_port) + "/" + "file?path=" + full_file

            if file == "yhkh":
                db_obj.yhkh_url = file_full_url

            if file == "swdj":
                db_obj.swdj_url = file_full_url

                print file_full_url
            if file == "yezz":
                db_obj.yezz_url = file_full_url

        db_session.add(db_obj)
        db_session.commit()
        return db_obj.uuid

    @staticmethod
    def update_file(files, file_path, invoice_data):
        isExists = os.path.exists(file_path)
        if not isExists:
            os.makedirs(file_path)
        for file in files:
            # 原始文件名
            source_fname = files.get(file)[0].get("filename")
            # 生成新的文件名, 返回完整路径
            full_file = FileUploadOperate.gen_file_name(file_path, source_fname)
            with open(full_file, "wb") as f:
                f.write(files.get(file)[0].get("body"))
            em = "save {0} to path: {1}".format(file, full_file)
            LOG.info(em)
            # 更新数据库数据库
            upload_db_obj = UploadLog.query.filter(and_(UploadLog.invoice_uuid == invoice_data.invoice_uuid,
                                                        UploadLog.file_type == file)).first()
            if not upload_db_obj:
                em = "can not found file type: <{0}> with invoice id: <{1}>".format(file, invoice_data.invoice_uuid)
                LOG.exception(em)
                continue
            upload_db_obj.file = full_file
            upload_db_obj.create_time = int(time.time)
            upload_db_obj.status = "unapproval"
            db_session.flush()
        db_session.commit()
        return 200

    @staticmethod
    def check_is_uploaded(user_id):
        """检查用户是否已经上传相关认证"""

        result = {"yezz": "unupload", "swdj": "unupload", "yhkh": "unupload"}
        # 检查营业执照
        upfile_obj = UploadLog.query.filter(UploadLog.user_id == user_id).first()
        if not upfile_obj:
            return result
        if upfile_obj.yezz_url:
            result["yezz"] = upfile_obj.status
        if upfile_obj.swdj_url:
            result["swdj"] = upfile_obj.status
        if upfile_obj.yhkh_url:
            result["yhkh"] = upfile_obj.status
        return result

    @staticmethod
    def gen_file_name(path, file_name):
        """随机生成文件名"""
        f_suffix = file_name.split(".")[-1]
        f_prefix = str(uuid.uuid1()).replace("-","")
        new_file_name = f_prefix + "." + f_suffix
        return path + new_file_name
