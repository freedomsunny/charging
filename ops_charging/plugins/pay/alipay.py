# -*- coding: utf-8 -*-

"""
Created on 2017.07.03
支付宝接口
@author: HuangYingJun
"""
import types
from urllib import urlencode
import random
import time

from ops_charging.plugins.hashcompat import md5_constructor as md5
from tornado import gen, httpclient
from ops_charging.options import get_options
import ops_charging.log as logging
from ops_charging.utils import post_http, get_http

LOG = logging.getLogger(__name__)

alipay_options = [
    {"name": "ALIPAY_KEY",
     "default": 'w76ap3t1iibnn9qj5r03oayx60v3bsf5',
     "help": "get resources type",
     "type": str
     },
    {"name": "ALIPAY_INPUT_CHARSET",
     "default": "utf-8",
     "type": str
     },
    {"name": "ALIPAY_PARTNER",
     "default": "2088311410047654",
     "type": str
     },
    {"name": "ALIPAY_SELLER_EMAIL",
     "default": "xiangyunwang@netnic.com.cn",
     "type": str
     },
    {"name": "ALIPAY_SIGN_TYPE",
     "default": "MD5",
     "type": str
     },
    {"name": "ALIPAY_SHOW_URL",
     "default": "",
     "type": str
     },
    {"name": "ALIPAY_TRANSPORT",
     "default": "http",
     "type": str
     },
    {"name": "GATEWAY",
     "default": "https://mapi.alipay.com/gateway.do?",
     "type": str
     },

    {"name": "OPEN_API_GW",
     "default": "https://openapi.alipay.com/gateway.do?",
     "type": str
     },
    {"name": "PayStatus",
     "default": {"TRADE_FINISHED": "success", "TRADE_SUCCESS": "success"},
     "type": dict
     }
]

options = get_options(alipay_options)


class AliPayPlugins(object):
    @staticmethod
    def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
        """
        Returns a bytestring version of 's', encoded as specified in 'encoding'.
    
        If strings_only is True, don't convert (some) non-string-like objects.
        """
        if strings_only and isinstance(s, (types.NoneType, int)):
            return s
        if not isinstance(s, basestring):
            try:
                return str(s)
            except UnicodeEncodeError:
                if isinstance(s, Exception):
                    # An Exception subclass containing non-ASCII data that doesn't
                    # know how to print itself properly. We shouldn't raise a
                    # further exception.
                    return ' '.join([AliPayPlugins.smart_str(arg, encoding, strings_only,
                                                             errors) for arg in s])
                return unicode(s).encode(encoding, errors)
        elif isinstance(s, unicode):
            return s.encode(encoding, errors)
        elif s and encoding != 'utf-8':
            return s.decode('utf-8', errors).encode(encoding, errors)
        else:
            return s

    # 对数组排序并除去数组中的空值和签名参数
    # 返回数组和链接串
    @staticmethod
    def params_filter(params):
        ks = params.keys()
        ks.sort()
        newparams = {}
        prestr = ''
        for k in ks:
            v = params[k]
            k = AliPayPlugins.smart_str(k, options.ALIPAY_INPUT_CHARSET)
            if k not in ('sign', 'sign_type') and v != '':
                newparams[k] = AliPayPlugins.smart_str(v, options.ALIPAY_INPUT_CHARSET)
                prestr += '%s=%s&' % (k, newparams[k])
        prestr = prestr[:-1]
        return newparams, prestr

    # 生成签名结果
    @staticmethod
    def build_mysign(prestr, key, sign_type='MD5'):
        if sign_type == 'MD5':
            return md5(prestr + key).hexdigest()
        return ''

    # 即时到账交易接口(返回支付宝支付URL)
    @staticmethod
    def create_direct_pay_by_user(tn, subject, body, total_fee):
        params = {}
        params['service'] = 'create_direct_pay_by_user'
        params['payment_type'] = '1'

        # 获取配置文件
        params['partner'] = options.ALIPAY_PARTNER
        params['seller_email'] = options.ALIPAY_SELLER_EMAIL
        params['return_url'] = options.ALIPAY_RETURN_URL
        params['notify_url'] = options.ALIPAY_NOTIFY_URL
        params['_input_charset'] = options.ALIPAY_INPUT_CHARSET
        params['show_url'] = options.ALIPAY_SHOW_URL

        # 从订单数据中动态获取到的必填参数
        params['out_trade_no'] = tn  # 请与贵网站订单系统中的唯一订单号匹配
        params['subject'] = subject  # 订单名称，显示在支付宝收银台里的“商品名称”里，显示在支付宝的交易管理的“商品名称”的列表里。
        params['body'] = body  # 订单描述、订单详细、订单备注，显示在支付宝收银台里的“商品描述”里
        params['total_fee'] = total_fee  # 订单总金额，显示在支付宝收银台里的“应付总额”里

        # 扩展功能参数——网银提前
        params['paymethod'] = 'directPay'  # 默认支付方式，四个值可选：bankPay(网银); cartoon(卡通); directPay(余额); CASH(网点支付)
        params['defaultbank'] = ''  # 默认网银代号，代号列表见http://club.alipay.com/read.php?tid=8681379

        # 扩展功能参数——防钓鱼
        params['anti_phishing_key'] = ''
        params['exter_invoke_ip'] = ''

        # 扩展功能参数——自定义参数
        params['buyer_email'] = ''
        params['extra_common_param'] = ''

        # 扩展功能参数——分润
        params['royalty_type'] = ''
        params['royalty_parameters'] = ''

        params, prestr = AliPayPlugins.params_filter(params)

        params['sign'] = AliPayPlugins.build_mysign(prestr, options.ALIPAY_KEY, options.ALIPAY_SIGN_TYPE)
        params['sign_type'] = options.ALIPAY_SIGN_TYPE
        url = options.GATEWAY + urlencode(params)
        return url

    # 纯担保交易接口
    @staticmethod
    def create_partner_trade_by_buyer(tn, subject, body, price):
        params = {}
        # 基本参数
        params['service'] = 'create_partner_trade_by_buyer'
        params['partner'] = options.ALIPAY_PARTNER
        params['_input_charset'] = options.ALIPAY_INPUT_CHARSET
        params['notify_url'] = options.ALIPAY_NOTIFY_URL
        params['return_url'] = options.ALIPAY_RETURN_URL

        # 业务参数
        params['out_trade_no'] = tn  # 请与贵网站订单系统中的唯一订单号匹配
        params['subject'] = subject  # 订单名称，显示在支付宝收银台里的“商品名称”里，显示在支付宝的交易管理的“商品名称”的列表里。
        params['payment_type'] = '1'
        params['logistics_type'] = 'POST'  # 第一组物流类型
        params['logistics_fee'] = '0.00'
        params['logistics_payment'] = 'BUYER_PAY'
        params['price'] = price  # 订单总金额，显示在支付宝收银台里的“应付总额”里
        params['quantity'] = 1  # 商品的数量
        params['seller_email'] = options.ALIPAY_SELLER_EMAIL
        params['body'] = body  # 订单描述、订单详细、订单备注，显示在支付宝收银台里的“商品描述”里
        params['show_url'] = options.ALIPAY_SHOW_URL

        params, prestr = AliPayPlugins.params_filter(params)

        params['sign'] = AliPayPlugins.build_mysign(prestr, options.ALIPAY_KEY, options.ALIPAY_SIGN_TYPE)
        params['sign_type'] = options.ALIPAY_SIGN_TYPE

        return options.GATEWAY + urlencode(params)

    @staticmethod
    def notify_verify(request):
        params = {}
        params['is_success'] = request('is_success', '')
        params['partnerId'] = request('partnerId', '')
        params['notify_id'] = request('notify_id', '')
        params['notify_type'] = request('notify_type', '')
        params['notify_time'] = request('notify_time', '')
        params['sign'] = request('sign', '')
        params['sign_type'] = request('sign_type', '')
        params['trade_no'] = request('trade_no', '')
        params['subject'] = request('subject', '')
        params['price'] = request('price', '')
        params['quantity'] = request('quantity', '')
        params['seller_email'] = request('seller_email', '')
        params['seller_id'] = request('seller_id', '')
        params['buyer_email'] = request('buyer_email', '')
        params['buyer_id'] = request('buyer_id', '')
        params['discount'] = request('discount', '')
        params['total_fee'] = request('total_fee', '')
        params['trade_status'] = request('trade_status', '')
        params['is_total_fee_adjust'] = request('is_total_fee_adjust', '')
        params['use_coupon'] = request('use_coupon', '')
        params['body'] = request('body', '')
        params['exterface'] = request('exterface', '')
        params['out_trade_no'] = request('out_trade_no', '')
        params['payment_type'] = request('payment_type', '')
        params['logistics_type'] = request('logistics_type', '')
        params['logistics_fee'] = request('logistics_fee', '')
        params['logistics_payment'] = request('logistics_payment', '')
        params['gmt_logistics_modify'] = request('gmt_logistics_modify', '')
        params['buyer_actions'] = request('buyer_actions', '')
        params['seller_actions'] = request('seller_actions', '')
        params['gmt_create'] = request('gmt_create', '')
        params['gmt_payment'] = request('gmt_payment', '')
        params['refund_status'] = request('refund_status', '')
        params['gmt_refund'] = request('gmt_refund', '')
        params['receive_name'] = request('receive_name', '')
        params['receive_address'] = request('receive_address', '')
        params['receive_zip'] = request('receive_zip', '')
        params['receive_phone'] = request('receive_phone', '')
        params['receive_mobile'] = request('receive_mobile', '')

        # 初级验证--签名
        _, prestr = AliPayPlugins.params_filter(params)
        mysign = AliPayPlugins.build_mysign(prestr, options.ALIPAY_KEY, options.ALIPAY_SIGN_TYPE)
        if mysign != request('sign', ''):
            # raise gen.Return(False)
            return 0
        return 1

        # # 二级验证--查询支付宝服务器此条信息是否有效
        # params = {}
        # params['partner'] = options.ALIPAY_PARTNER
        # params['notify_id'] = request('notify_id', '')
        # if options.ALIPAY_TRANSPORT == 'https':
        #     params['service'] = 'notify_verify'
        #     gateway = 'https://mapi.alipay.com/gateway.do'
        # else:
        #     gateway = 'http://notify.alipay.com/trade/notify_query.do'
        # # 返回200代表消息是支付宝发送则正确
        # resp = post_http(url=gateway, data=urlencode(params))
        # return resp

    @staticmethod
    def asyncnotify_verify(request):
        params = {}
        params["notify_time"] = request("notify_time", "")
        params["notify_type"] = request("notify_type", "")
        params["notify_id"] = request("notify_id", "")
        params["sign_type"] = request("sign_type", "")
        params["sign"] = request("sign", "")
        params["out_trade_no"] = request("out_trade_no", "")
        params["subject"] = request("subject", "")
        params["payment_type"] = request("payment_type", "")
        params["trade_no"] = request("trade_no", "")
        params["gmt_create"] = request("gmt_create", "")
        params["trade_status"] = request("trade_status", "")
        params["gmt_create"] = request("gmt_create", "")
        params["refund_status"] = request("refund_status", "")
        params["gmt_payment"] = request("gmt_payment", "")
        params["gmt_close"] = request("gmt_close", "")
        params["refund_status"] = request("refund_status", "")
        params["gmt_refund"] = request("gmt_refund", "")
        params["seller_email"] = request("seller_email", "")
        params["buyer_email"] = request("buyer_email", "")
        params["seller_id"] = request("seller_id", "")
        params["price"] = request("price", "")
        params["total_fee"] = request("total_fee", "")
        params["quantity"] = request("quantity", "")
        params["body"] = request("body", "")
        params["discount"] = request("discount", "")
        params["is_total_fee_adjust"] = request("is_total_fee_adjust", "")
        params["use_coupon"] = request("use_coupon", "")
        params["extra_common_param"] = request("extra_common_param", "")
        params["buyer_id"] = request("buyer_id", "")

        # 初级验证--签名
        _, prestr = AliPayPlugins.params_filter(params)
        mysign = AliPayPlugins.build_mysign(prestr, options.ALIPAY_KEY, options.ALIPAY_SIGN_TYPE)
        if mysign != request('sign', ''):
            em = "async notify verify failed"
            LOG.exception(em)
            return {"error": [{"code": 400, "msg": "{0}".format(em)}]}
        params["trade_status"] = options.PayStatus.get(params.get("trade_status"), "failed")
        return params

    @staticmethod
    def generate_out_trade_no():
        trade_no = time.strftime('%Y%m%d%H%m%S', time.localtime(time.time()))
        rand_num = str(random.random())[2:6]
        return trade_no + rand_num
