#!/usr/bin/env python3
# _*_ coding:utf-8 _*_

import sys,json,time
import requests

def get_dict(url):
    respone = requests.get(url).content
    return json.loads(respone.decode('utf-8'))

def post_data(url,job_name,data):

    respone  = requests.post("http://%s/metrics/job/%s" % (url,job_name),data=data)
    return respone


def make_data(get_dict):
    metrice_data = ""
    for channel in get_dict["channels"]:
        metrice_data += 'nsq_%s_%s_depth_status{instance="%s",topic="%s",channel="%s",job="%s"} %s\n' % (
            channel["topic_name"],channel["channel_name"],"nsq_cluster",channel["topic_name"], channel["channel_name"], "nsq_topic_"+channel["topic_name"]+"_status",channel["depth"])
    return  metrice_data,"nsq_topic_"+channel["topic_name"]+"_status"


if __name__ == "__main__":
    if len(sys.argv) < 2 :
        print("Usage: python3 %s \"topic_name\"" % (sys.argv[0]))
        exit(1)
    topic_name=sys.argv[1]
    nsq_stats_url = "http://10.0.20.192:4171/api/topics/" + topic_name
    url="192.168.0.216:9091"
    while True:
        post_data,job_name = make_data(get_dict(nsq_stats_url))
        post_data(url=url,job_name=job_name,data=post_data)
        time.sleep(2)

    # post_data,job_name = make_data(Get_dict(nsq_stats_url))
    # print(post_data)
    # print(Post_data(url,job_name,post_data))
