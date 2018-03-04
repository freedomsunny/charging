# -*- coding:utf-8 -*-
from __future__ import unicode_literals
import decimal

import datetime
import tornado.web
import json
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from ops_charging.db.models import db_session


class BaseHander(tornado.web.RequestHandler):
    def json_response(self, code=0, result=None, message='ok'):
        return self.finish(json.dumps(dict(code=code, message=message, data=result),
                                      cls=ApiJSONEncoder,
                                      ensure_ascii=False,
                                      separators=(',', ':')))

    # when after request run this method
    def on_finish(self):
        if self.get_status() == 500:
            db_session.rollback()
        else:
            db_session.remove()
    # def on_finish(self):
    #     try:
    #         db_session.close()
    #     except Exception as e:
    #         pass
    #         # LOG.error('sqlalchemy session close make error:%s' % e.message)
    #
    # def prepare(self):
    #     self.db = db_session


class ApiJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj.__class__, DeclarativeMeta):
            data = {}
            fields = obj.__json__() if hasattr(obj, '__json__') else dir(obj)
            for field in [f for f in fields if not f.startswith('_')
            and f not in ['metadata', 'query', 'query_class']]:
                value = obj.__getattribute__(field)
                if callable(value):
                    continue
                try:
                    json.dumps(value)
                    data[field] = value
                except Exception as e:
                    if isinstance(value, datetime.datetime):
                        data[field] = value.isoformat()
                    elif isinstance(value, datetime.date):
                        data[field] = value.isoformat()
                    elif isinstance(value, datetime.timedelta):
                        data[field] = (datetime.datetime.min + value).time().isoformat()
                    elif isinstance(value, decimal.Decimal):
                        data[field] = (str(value))
                    else:
                        data[field] = None
            return data

        return json.JSONEncoder.default(self, obj)
