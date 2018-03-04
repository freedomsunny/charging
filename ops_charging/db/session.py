# """Session Handling for SQLAlchemy backend."""

import mysql.connector
# import time
# import json
# import datetime
#
# import sqlalchemy.interfaces
# import sqlalchemy.orm
# from sqlalchemy.exc import DisconnectionError, OperationalError
# from sqlalchemy.pool import NullPool, StaticPool
# from ops_charging.db.models import db_session, engine
#
# from ops_charging import exception

from ops_charging.options import get_options

db_options = [

    {
        "name": 'db_user',
        "default": "charging",
        "help": '',
        "type": str,
    },
]
options = get_options(db_options)
