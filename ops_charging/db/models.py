#!/usr/bin/env python
#encoding=utf-8
import datetime
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, DateTime, Text, Float, DECIMAL, VARCHAR
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, object_mapper, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
import time
import uuid

from ops_charging.options import get_options
from ops_charging import utils

options = get_options()
# pool_recycle should less than MySQL wait_timeout
engine = create_engine(options.sql_connection, convert_unicode=True, poolclass=NullPool)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


def get_session():
    return db_session


def model_query(*args, **kwargs):
    """
    :param session: if present, the session to use
    :param read_deleted: if read deleted data
    """
    session = kwargs.get('session') or get_session()
    read_deleted = kwargs.get('read_deleted')
    query = session.query(*args)

    if read_deleted == 'no':
        query = query.filter_by(deleted=False)
    elif read_deleted == 'only':
        query = query.filter_by(deleted=True)

    return query


def get_uuid():
    return str(uuid.uuid1())


def get_now_time():
    return int(time.time())


def init_db():
    Base.metadata.create_all(bind=engine)


class Orders(Base):
    __tablename__ = 'orders'
    uid = Column(VARCHAR(50), primary_key=True)
    start_time = Column(Integer)
    end_time = Column(Integer)
    resource_from = Column(VARCHAR(50))
    resource_from_provider = Column(VARCHAR(50))
    off = Column(Float, default=1)
    used = Column(Float)
    resource_id = Column(VARCHAR(50))
    resource_type = Column(Integer)
    resource_name = Column(VARCHAR(50))
    project_id = Column(VARCHAR(50))
    project_name = Column(VARCHAR(50))
    user_id = Column(VARCHAR(50))
    status = Column(VARCHAR(50))
    resource = Column(VARCHAR(50))
    user_name = Column(VARCHAR(50))
    order_type = Column(Integer, default=2)
    log_time = Column(Integer)

    def __init__(self, uid, start_time=None, end_time=None, resource_from=None, resource_from_provider=None, off=None,
                 used=None, resource_id=None, resource_type=None, resource_name=None, project_id=None,
                 project_name=None, user_id=None, status=None, resource=None, user_name=None, order_type=None, log_time=None):
        self.uid = uid
        self.start_time = start_time
        self.end_time = end_time
        self.resource_from_provider = resource_from_provider
        self.resource_from = resource_from
        self.off = off
        self.used = used
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.project_id = project_id
        self.project_name = project_name
        self.user_id = user_id
        self.status = status
        self.resource = resource
        self.user_name = user_name
        self.order_type = order_type
        self.log_time = log_time

    def __repr__(self):
        return '<ResourceID %r>' % self.resource_id


class Price(Base):
    __tablename__ = "price"
    uid = Column(VARCHAR(50), primary_key=True)
    unit = Column(Float)
    price = Column(Float)
    time = Column(Integer)
    price_type = Column(Integer)
    name = Column(VARCHAR(50))
    description = Column(VARCHAR(100))

    def __init__(self, uid, unit, price, time, price_type, name, description=None):
        self.uid = uid
        self.unit = unit
        self.price = price
        self.time = time
        self.price_type = price_type
        self.name = name
        self.description = description

    def __repr__(self):
        return '<PriceType %r>' % self.price_type


class User(Base):
    __tablename__ = "users"
    id = Column(VARCHAR(50), primary_key=True)
    user_id = Column(VARCHAR(50), unique=True)
    user_name = Column(VARCHAR(50))
    project_id = Column(VARCHAR(50))
    project_name = Column(VARCHAR(50))
    money = Column(DECIMAL(50, 2), default=10)
    exceed_time = Column(Integer)
    update_time = Column(Integer, default=0)
    register_time = Column(Integer)
    is_exceed = Column(Boolean, default=False)
    is_destroy = Column(Boolean, default=False)

    def __init__(self, id, user_id, user_name, project_id, project_name, register_time, exceed_time=None, update_time=None):
        self.id = id
        self.user_id = user_id
        self.user_name = user_name
        self.project_id = project_id
        self.project_name = project_name
        self.register_time = register_time
        self.exceed_time = exceed_time
        self.update_time = update_time

    def __repr__(self):
        return '<UserName %r>' % self.user_name


class ConsumeLog(Base):
    """user consume recorde"""
    __tablename__ = "consume_log"
    uid = Column(VARCHAR(50), primary_key=True)
    user_id = Column(VARCHAR(50))
    user_name = Column(VARCHAR(50))
    project_id = Column(VARCHAR(50))
    resource_name = Column(VARCHAR(50))
    resource_type = Column(Integer)
    resource_from = Column(VARCHAR(50))
    resource_id = Column(VARCHAR(50))
    start_time = Column(Integer)
    end_time = Column(Integer)
    money = Column(DECIMAL(50, 2))
    order_uid = Column(String(50))
    log_time = Column(Integer)
    details = Column(String(100))

    def __init__(self, uid, user_id, user_name, project_id, resource_name, resource_type, resource_id,
                 start_time, end_time, money, log_time, resource_from=None, order_uid=None, details=None):
        self.uid = uid
        self.user_id = user_id
        self.user_name = user_name
        self.project_id = project_id
        self.resource_type = resource_type
        self.resource_from = resource_from
        self.resource_id = resource_id
        self.resource_name = resource_name
        self.start_time = start_time
        self.end_time = end_time
        self.money = money
        self.log_time = log_time
        self.order_uid = order_uid
        self.details = details

    def __repr__(self):
        return "UserName %r" % self.user_name


class RechargeLog(Base):
    """user recharge recorde"""
    __tablename__ = "recharge_log"
    uid = Column(VARCHAR(50), primary_key=True)
    user_id = Column(VARCHAR(50))
    user_name = Column(VARCHAR(50))
    money = Column(DECIMAL(50, 2))
    log_time = Column(Integer)
    out_trade_no = Column(VARCHAR(50))
    trade_status = Column(VARCHAR(50))
    description = Column(Text)
    recharge_way = Column(VARCHAR(20))
    # 是否已开发票
    is_invoiced = Column(Boolean, default=False)

    def __init__(self, uid, user_id, user_name, money, log_time, out_trade_no, trade_status, description=None, recharge_way=None):
        self.uid = uid
        self.user_id = user_id
        self.user_name = user_name
        self.money = money
        self.log_time = log_time
        self.out_trade_no = out_trade_no
        self.trade_status = trade_status
        self.description = description
        self.recharge_way = recharge_way

    def __repr__(self):
        return "<UserName %r>" % self.user_name



class Discount(Base):
    """discount table"""
    __tablename__ = "discount"
    uid = Column(VARCHAR(50), primary_key=True, default=get_uuid())
    discount_id = Column(String(50))
    money = Column(DECIMAL(50, 2))
    gen_time = Column(Integer)
    valid_date = Column(Integer)
    is_used = Column(Boolean, default=False)
    is_allocation = Column(Boolean, default=False)
    used_time = Column(Integer)
    description = Column(Text)

    def __init__(self, uid, discount_id, money, gen_time, is_used, valid_date=None, used_time=None, description=None,
                 is_allocation=False):
        self.uid = uid
        self.discount_id = discount_id
        self.money = money
        self.gen_time = gen_time
        self.is_used = is_used
        self.valid_date = valid_date
        self.used_time = used_time
        self.description = description
        self.is_allocation = is_allocation

    def __repr__(self):
        return "<UserName %r>" % self.user_name


class Invoice(Base):
    """invoice table"""
    __tablename__ = "invoice"
    uuid = Column(VARCHAR(50), primary_key=True)
    # 物流单号
    logistics_no = Column(VARCHAR(50))
    # 物流公司
    logistics_company = Column(VARCHAR(50))
    # 发票抬头内容
    title = Column(VARCHAR(100))
    # 状态
        # 审核中  ----- verifying
        # 审核不通过 ----failed
        # 已通过  ----- passed
        # 已邮寄  ----- posted
        # 已完成  ----- finished
    status = Column(VARCHAR(20))
    # 邮寄地址
    post_address = Column(VARCHAR(100))
    # 邮寄用户名
    post_user = Column(VARCHAR(50))
    # 邮寄电话
    post_phone = Column(VARCHAR(20))
    # 发票金额
    money = Column(DECIMAL(50, 2))
    # 发票号
    invoice_no = Column(VARCHAR(100))
    # 发票抬头类型
        # 个人 ---- personal
        # 公司 ---- company
    title_type = Column(VARCHAR(100))
    # 开票方式:
        # 普通发票 --- common
        # 增值税发票 --- increase
    title_mode = Column(VARCHAR(50))
    # 发票内容 默认：`网络服务费`
    context = Column(VARCHAR(100))
    # 公司名称
    corporation_name = Column(VARCHAR(100))
    # 纳税人识别号
    taxpayer_dentity = Column(VARCHAR(100))
    # 公司注册地址
    register_address = Column(VARCHAR(100))
    # 公司注册电话
    register_phone = Column(VARCHAR(100))
    # 开户银行
    deposit_bank = Column(VARCHAR(100))
    # 开户账号
    deposit_account = Column(VARCHAR(100))
    # 平台用户名
    user_name = Column(VARCHAR(50))
    # 平台用户ID
    user_id = Column(VARCHAR(50))
    # 申请时间
    application_date = Column(VARCHAR(50))
    # 完成时间
    complete_date = Column(VARCHAR(50))
    # 描述/备注
    description = Column(Text)
    # 充值记录UUID
    recharge_uuids = Column(Text)
    deleted = Column(Boolean, default=False)
    # 上传的文件相关连的uuid
    upfile_uuid = Column(VARCHAR(50))

    def __init__(self, uuid=None, logistics_no=None, title=None, status=None, post_address=None, post_user=None, post_phone=None,
                 money=None, invoice_no=None, title_type=None, title_mode=None, context=None, corporation_name=None,
                 taxpayer_dentity=None, register_address=None, register_phone=None, deposit_bank=None, deposit_account=None,
                 user_name=None, complete_date=None, description=None, application_date=None, user_id=None, deleted=None, recharge_uuids=None,
                 upfile_uuid=None):
        self.uuid = uuid
        self.logistics_no = logistics_no
        self.title = title
        self.status = status
        self.post_address = post_address
        self.post_user = post_user
        self.post_phone = post_phone
        self.money = money
        self.invoice_no = invoice_no
        self.title_type = title_type
        self.title_mode = title_mode
        self.context = context
        self.corporation_name = corporation_name
        self.taxpayer_dentity = taxpayer_dentity
        self.register_address = register_address
        self.register_phone = register_phone
        self.deposit_bank = deposit_bank
        self.deposit_account = deposit_account
        self.user_name = user_name
        self.complete_date = complete_date
        self.description = description
        self.application_date = application_date
        self.user_id = user_id
        self.deleted = deleted
        self.recharge_uuids = recharge_uuids
        self.upfile_uuid = upfile_uuid

    def __repr__(self):
        return "<user name: %r>" % self.user_name


class UploadLog(Base):
    """user upload file table"""
    __tablename__ = "upload_log"
    uuid = Column(VARCHAR(50), primary_key=True)
    user_id = Column(VARCHAR(50))
    # 用户名
    user_name = Column(VARCHAR(50))
    # 上传时间
    create_time = Column(VARCHAR(50), default=get_now_time())
    # 状态
    # passed   审核通过
    # abnormal  异常
    # unapproval 未通过
    status = Column(VARCHAR(20), default="unapproval")
    # 营业执照
    yezz_url = Column(VARCHAR(200))
    # 税务登记(一般纳税人)
    swdj_url = Column(VARCHAR(200))
    # 银行开户许可证
    yhkh_url = Column(VARCHAR(200))
    # 描述信息
    description = Column(Text)
    def __init__(self, uuid, user_id, user_name, create_time, yezz_url=None, swdj_url=None, yhkh_url=None):
        self.uuid = uuid
        self.user_id = user_id
        self.user_name = user_name
        self.create_time = create_time
        self.yezz_url = yezz_url
        self.swdj_url = swdj_url
        self.yhkh_url = yhkh_url


class OpsBase(object):
    """Base class for Ops Models."""
    __table_args__ = {'mysql_engine': 'InnoDB'}
    __table_initialized__ = False
    created_at = Column(DateTime, default=utils.utcnow)
    updated_at = Column(DateTime, onupdate=utils.utcnow)
    deleted_at = Column(DateTime)
    deleted = Column(Boolean, default=False)
    metadata = None

    def save(self, session=None):
        """Save this object."""
        if not session:
            session = db_session
        session.add(self)
        session.flush()

    def delete(self, session=None):
        """Delete this object."""
        self.deleted = True
        self.deleted_at = utils.utcnow()
        self.save(session=session)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __iter__(self):
        self._i = iter(object_mapper(self).columns)
        return self

    def next(self):
        n = self._i.next().name
        return n, getattr(self, n)

    def update(self, values):
        """Make the model object behave like a dict"""
        for k, v in values.iteritems():
            setattr(self, k, v)

    def iteritems(self):
        """Make the model object behave like a dict.

        Includes attributes from joins."""
        local = dict(self)
        joined = dict([(k, v) for k, v in self.__dict__.iteritems()
                       if not k[0] == '_'])
        local.update(joined)
        return local.iteritems()


class APICount(Base, OpsBase):
    """count api caled"""
    __tablename__ = 'api_count'
    id = Column(Integer, primary_key=True)
    name = Column(String(128))
    url = Column(String(1024))
    count = Column(Integer)


def register_models(tables):
    """Register Models and create metadata.
    tablese = (Costlog,)
    """
    models = tables
    for model in models:
        model.metadata.create_all(engine)


register_models((APICount,
                 Orders,
                 Price,
                 ConsumeLog,
                 RechargeLog,
                 Discount,
                 Invoice,
                 UploadLog,
                 ))
