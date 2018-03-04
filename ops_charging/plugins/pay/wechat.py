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
import io

from tornado import gen, httpclient
from ops_charging.options import get_options
import ops_charging.log as logging
from ops_charging.utils import post_http, get_http

LOG = logging.getLogger(__name__)

wechatpay_options = [
    {"name": "",
     "default": '',
     "help": "",
     "type": str
     },
]

options = get_options(wechatpay_options)


class GneQRCode(object):
    def __init__(self, url, version=5, box_size=10, border=4):
        self.url = url.strip()
        self.version = version
        self.box_size = box_size
        self.border = border

    @property
    def qr_code(self):
        qr = qrcode.QRCode(
            version=self.version,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=self.box_size,
            border=self.border,
        )
        qr.add_data(self.url)
        qr.make(fit=True)
        imgio = io.BytesIO()
        img = qr.make_image()
        # img.save('123.png')
        img.save(imgio)
        return imgio.getvalue()
