# coding=utf8

"""
every opt of used should bu define first


this options is based on tornado.options
"""

from tornado.options import define, parse_command_line, \
    parse_config_file, options

common_opts = [
    {
        "name": 'debug',
        "default": False,
        "help": 'if logged debug info',
        "type": bool,
    },
    {
        "name": 'verbose',
        "default": False,
        "help": 'if log detail',
        "type": bool,
    },
    {
        "name": 'config',
        "default": '/etc/charging/ops_charging.conf',
        "help": 'path of config file',
        "type": str,
        "callback": lambda path: parse_config_file(path, final=False)
    },
    {
        "name": 'sql_connection',
        "default": 'mysql+mysqlconnector://root:123456@127.0.0.1/charging?charset=utf8',
        "help": 'The SQLAlchemy connection string used to connect to \
                    the database',
        "type": str,
    },
    {
        "name": 'db_driver',
        "default": 'ops_charging.db.api',
        "help": 'default db driver',
        "type": str,
    },
    {
        "name": 'lock_path',
        "default": '/var/lock',
        "help": 'path of config file',
        "type": str,
    },
    {
        "name": 'api_port',
        "default": 8900,
        # "default": 8080,
        "help": 'listen port of api',
        "type": int,
    },
    {
        "name": 'listen',
        "default": '127.0.0.1',
        "help": 'listen address',
        "type": str,
    },
    {
        "name": 'keystone_endpoint',
        "default": '',
        # "default": 'http://10.200.100.8:35357/v3',
        # "default": 'http://172.16.68.102:35357/v3',
        "help": 'the keystone endpoint url',
        "type": str,
    },
    {
        "name": 'keystone_admin_endpoint',
        "default": '',
        # "default": 'http://10.200.100.8:5000/v2.0',
        # "default": 'http://172.16.68.102:5000/v2.0',
        "help": 'the keystone endpoint url',
        "type": str,
    },
    {
        "name": 'username',
        "default": 'admin',
        "help": 'username of auth',
        "type": str,
    },
    {
        "name": 'password',
        "default": 'password',
        "help": 'password of auth',
        "type": str,
    },
    {
        "name": 'extra_opts',
        "default": '',
        "help": "all opts of app's",
        "type": str,
    },
    {
        "name": 'keystone_username',
        "default": 'admin',
        "help": "keystone admin user name",
        "type": str,
    },
    {
        "name": 'keystone_password',
        "default": 'MCmRMoLslUW9UeHtDTOuoMc36TMbkHu8zqr9O70e',
        "help": "keystone admin user password",
        "type": str,
    },
    {
        "name": 'keystone_tenant',
        "default": 'admin',
        "help": "keystone admin user tenant",
        "type": str,
    },
    {"name": "order_immed",
     "help": "order type is immediately pay",
     "default": 1,
     "type": int
     },
    {"name": "order_prepay",
     "help": "order type is prepay",
     "default": 2,
     "type": int
     },
    # 申请发票时上传认证文件的路径
    {"name": "upload_file_path",
     "help": "post method upload file path",
     "default": "/data/upload/",
     "type": str
     },
    # 申请发票后的状态
    {"name": "invoice_status",
     "help": "invoice status",
     "default": {"verifying": "verifying",    # 审核中
                 "reject": "reject",       # 审核不通过
                 "passed": "passed",       # 已通过
                 "posted": "posted",       # 已邮寄
                 # "finished": "finished",     # 已完成
                },
     "type": dict
     },
    {"name": "cmdb_ep",
     "help": "order type is prepay",
     "default": "",
     "type": str
     },
    {"name": "ALIPAY_RETURN_URL",
     "help": "alipay return url.",
     "default": "",
     "type": str
     },
    {"name": "ALIPAY_NOTIFY_URL",
     "help": "alipay notify url(async)",
     "default": "",
     "type": str
     },
    {"name": "failure_url",
     "help": "alipay failure url",
     "default": "",
     "type": str
     },
    {"name": "success_url",
     "help": "alipay success url",
     "default": "",
     "type": str
     },
    {"name": "float_ip",
     "help": "floating ip",
     "default": "",
     "type": str
     },
    {"name": "sync_api",
     "help": "real time sync data to cmdb",
     "default": "",
     "type": str
     },
]


def register_opt(opt, group=None):
    """Register an option schema
    opt = {
            "name": 'config',
            "default": 'ops_charging.conf',
            "help": 'path of config file',
            "tyle": str,
            "callback": lambda path: parse_config_file(path, final=False)
        }
    """
    if opt.get('name', ''):
        optname = opt.pop('name')
        if optname in options._options.keys():
            options._options.pop(optname)
        define(optname, **opt)


def register_opts(opts, group=None):
    """Register multiple option schemas at once."""
    for opt in opts:
        register_opt(opt, group)
    return options


def get_options(opts=None, group=None):
    if opts:
        register_opts(opts, group)
    options = register_opts(common_opts, 'common')
    if options.as_dict().get('extra_opts', ''):
        try:
            extra_opts = __import__(options.extra_opts)
            options = register_opts(extra_opts.config.opts, 'extra')
        except Exception as e:
            print "get config error msg %r" % e
    parse_config_file(options.config, final=False)
    parse_command_line()
    return options


if __name__ == "__main__":
    print get_options().as_dict()
    options = get_options()
    print options.get('sql_connection', None)
