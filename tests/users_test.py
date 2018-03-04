#encoding=utf-8

import sys
sys.path.append("/root/charging")
from ops_charging.plugins.orders_plugins import OrderAbout


def test_get_user_day_used(user_id):
    return OrderAbout.get_user_day_used(user_id=user_id)



test_get_user_day_used("65c7111800194e95981b1924112b25ef")