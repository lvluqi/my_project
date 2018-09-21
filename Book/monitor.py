import json,time
import requests
from prometheus_client import CollectorRegistry,Gauge,push_to_gateway


class nsqMonitor():
    def __init__(self,url):
        self.url = url

    def _get_topic(self):
        '''

        :return: topics list
        '''
        topics = requests.get(self.url + "/api/topics").json()['topics']
        return topics

    def _get_channel(self,topics):
        '''
        返回topic信息 数据类型 dict
        :param topics: topic
        :return: dict
        '''
        topic_info_dict  = requests.get(self.url+"/api/topics/"+ topics).json()
        return topic_info_dict

    def _get_channel_dict(self):
        channel_info_dict = requests.get(self.url).content
        return json.loads(channel_info_dict.decode('utf-8'))


    def _push_data_to_pushgateway(self,re,job_name,acount):
            registry = CollectorRegistry()
            g = Gauge('nsq_%s' %re , 'Last time a batch job successfully finished', registry=registry)
            g.set(acount)
            push_to_gateway('10.0.20.216:9091', job=job_name, registry=registry)
            print("Push data successful")

    def run(self):
        tmp = 0
        topics_list = self._get_topic()
        for topic in topics_list:
            res = self._get_channel(topic)
            # print(res)
            # for client in res["nodes"]:
            client = res["nodes"][0]
            # print(client["node"], client["hostname"], client["message_count"])
            # tmp = client["message_count"] + tmp
            metrice_data = ""
            if not client["channels"]:
                print("channel not exist.")
                print(client["topic_name"])
                self._push_data_to_pushgateway(client["topic_name"],client["topic_name"],
                                               res["depth"])

            for channel in client["channels"]:
                self._push_data_to_pushgateway(channel["topic_name"] + "_" + channel["channel_name"],
                                               channel["topic_name"] + "_" + channel["channel_name"],
                                               channel["depth"])


if __name__ == '__main__':

    nsqadmin_url="http://10.0.20.220:4171"
    a = nsqMonitor(nsqadmin_url)
    while True:
        a.run()
        time.sleep(5)
