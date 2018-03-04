FROM opsbase:latest
MAINTAINER huangyj
COPY charging /root/charging
WORKDIR /root/charging/
RUN yum -y install mysql-connector-python.noarch redis.x86_64 \
    && mkdir /etc/ops_charging/ \
#    && cp etc/ops_charging.conf /etc/ops_charging/ \
    && pip install -r requirements.txt \
    && rm -rf /var/lock && mkdir /var/lock \
    && echo -e "python /root/charging/bin/check_user_exceed_time &\nredis-server &\npython /root/charging/bin/charging_api" > /root/start.sh
CMD sh /root/start.sh