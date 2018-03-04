#!encoding=utf-8
from ops_charging.db.models import db_session, Orders, Price, User, RechargeLog, ConsumeLog
from sqlalchemy import and_
from ops_charging.utils import get_http, post_http, get_token
import ops_charging.log as logging

from ops_charging import cache
from ops_charging.options import get_options

LOG = logging.getLogger(__name__)
sms_opts = [
    {"name": "",
     "default": "",
     "help": "",
     "type": str
     },
]
options = get_options(sms_opts)

#encoding=utf-8

from yunpian_python_sdk.model import constant as YC
from yunpian_python_sdk.ypclient import YunpianClient
import cPickle

from ops_sia.cache import Backend
import random
from tomorrow import threads
from ops_sia.options import get_options
from ops_sia.utils import get_http, post_http, get_token
import ops_sia.log as logging

LOG = logging.getLogger(__name__)


# 移动号段：
# 134 135 136 137 138 139 147 148 150 151 152 157 158 159 172 178 182 183 184 187 188 198
# 联通号段：
# 130 131 132 145 146 155 156 166 171 175 176 185 186
# 电信号段：
# 133 149 153 173 174 177 180 181 189 199
# 虚拟运营商:
# 170


options = get_options()


class SendSmsMsg(object):
    cache = Backend()
    def __init__(self, phone, api_key=options.sms_api_key):
        self.phone = phone
        self.api_key = api_key

    # @threads(20)
    # def send_msg(self, msg):
    #     # 初始化client,apikey作为所有请求的默认值
    #     clnt = YunpianClient(self.api_key)
    #     param = {YC.MOBILE: self.phone,
    #              YC.TEXT: msg}
    #     result = clnt.sms().single_send(param)
    #     if result.code() != 0:
    #         msg = "Error send msg to phone <{0}>".format(self.phone)
    #         LOG.exception(msg)
    #         return False
    #     return True

    @staticmethod
    def check_phone(session_id):
        """确定该用户是否已发送短信"""
        ret = SendSmsMsg.cache.conn.get(session_id)
        if ret:
            # return cPickle.loads(ret)
            return ret
        return {}

    @staticmethod
    def check_auth_code(session_id, auth_code):
        ret = SendSmsMsg.cache.conn.get(session_id)
        if not ret or str(ret).strip() != str(auth_code).strip():
            return {"code": 1, "result": u"无效验证码"}

        return {"code": 0, "result": u""}

    @staticmethod
    def save_phone_auth_code(session_id, data):
        # msg = cPickle.dumps(data)
        SendSmsMsg.cache.conn.set(session_id, data)
        SendSmsMsg.cache.conn.set(session_id + "_", data)
        # 验证码有效时间
        SendSmsMsg.cache.conn.expire(session_id, options.auth_code_valid_time)
        # 发送短信间隔时间
        SendSmsMsg.cache.conn.expire(session_id + "_", options.auth_code_interval)

    @staticmethod
    def delete_phone_auth_code(session_id):
        # msg = cPickle.dumps(data)
        SendSmsMsg.cache.conn.delete(session_id)

    @staticmethod
    def gen_sms_auth_code(len=options.sms_auth_code_len):
        result = []
        for i in range(len):
            result.append(str(random.randint(0, 9)))
        return result


@threads(20)
def send_msg(phone, msg):
    # 初始化client,apikey作为所有请求的默认值
    clnt = YunpianClient(options.sms_api_key)
    param = {YC.MOBILE: phone,
             YC.TEXT: msg}
    result = clnt.sms().single_send(param)
    if result.code() != 0:
        msg = "Error send msg to phone <{0}>".format(phone)
        LOG.exception(msg)
        return False
    return True
