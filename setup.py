#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="charging",
    version='1.0',
    description="charging lib",
    author="huangyingjun",
    install_requires=[
        "mysql",
        "SQLAlchemy",
        "mysql-connector-python-rf",
        "MySQL-python",
        "tornado",
        "eventlet",
        "redis",
        "requests",
        "netaddr",
    ],

    scripts=[
        "bin/charging_api",
        "bin/check_user_exceed_time",
        "bin/ops_admin.py",
    ],

    packages=find_packages(),
    include_package_data=True,
    data_files=[
        ('/etc/charging', ['etc/ops_charging.conf']),
        ('/var/log/charging', []),
    ],
)
