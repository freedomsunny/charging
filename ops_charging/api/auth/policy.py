default = {
    "GET": ["admin", "service_ocmdb", "_member_", "user"],
    "POST": ["admin", "service_ocmdb", "_member_", "user"],
    "PUT": ["admin", "service_ocmdb", "_member_", "user"],
    "DELETE": ["admin", "service_ocmdb", "_member_", "user"],
}

policy = {
    "/alipay/notfiy$": {},
    "/alipay/notfiy_asyncnotify$": {},
    "/alipay/geturl$": {},
    "/test": {},
    "/order/orders$": {},
    "/money/usermoney$": {},
    "/rechargelog$": {},
    "/consumelog$": {},
    "/userdayuse$": {},
    "/discount/add$": {},
    "/discount/get$": {},
    "/test/sayhello": {},
    "/invoice$": {},
    "/file$": {}
    }
