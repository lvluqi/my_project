<center>kubernetes部署<center>
---
>安装方式

1. minikube
Minikube是一个工具，可以在本地快速运行一个单节点的kubernetes实例
2. kubeadm
kubeadm也是一个工具，提供kubeadm init和kubeadm join，用于快速部署kubernetes集群
3. 二进制

生产环境kubeadm和二进制二选一，kubeadm降低部署难度，但是屏蔽细节，后期遇到问题难以排查，这里选择二进制包安装
| 软件      |    版本 |
| :-------- | --------:|
| 系统  | Centos 7.4|
|kubernetes|1.11.1|


服务器角色

| 角色 |  IP |   组件|
| :--------       | --------:| :------: |
| k8s-master|   192.168.0.220|  kube-apiserver,kube-controller-manager,kube-scheduler,etcd|
| k8s-node1 | 192.168.0.98 | kubelet,kube-proxy,docker,flannel,etcd|
| k8s-node2 | 192.168.0.216| kubelet,kube-proxy,docker,flannel,etcd|
| 镜像仓库 | 192.168.0.98 |Harbor|
>部署前准备工作

    关闭selinux和firewalld
    下载相关安装包

>导入证书相关命令
```
export CFSSL_URL=https://pkg.cfssl.org/R1.2
wget ${CFSSL_URL}/cfssl_linux-amd64 -O/usr/local/bin/cfssl
wget ${CFSSL_URL}/cfssljson_linux-amd64 -O /usr/local/bin/cfssljson
chmod +x /usr/local/bin/cfssl*
```
编写生成证书的三个文件，证书生成在一台机器上操作即可，然后分发到另外的机器上
```
cat ca-config.json
{
  "signing": {
    "default": {
      "expiry": "87600h"
    },
    "profiles": {
      "www": {
        "expiry": "87600h",
        "usages": [
          "signing",
          "key encipherment",
          "server auth",
          "client auth"
        ]
      }
    }
  }
}
```
```
cat cs-csr.json

{
  "CN": "etcd CA",
  "key": {
    "algo": "rsa",
    "size": 2048
  },
  "names": [
    {
      "C": "CN",
      "L": "Shanghai",
      "ST": "Shanghai"
    }
  ]
}
```
```
cat server-csr.json

{
  "CN": "etcd",
  "hosts": [
    "192.168.0.220",
    "192.168.0.98",
    "192.168.0.216"
  ],
  "key": {
    "algo": "rsa",
    "size": 2048
  },
  "names": [
    {
      "C": "CN",
      "L": "Shanghai",
      "ST": "Shanghai"
    }
  ]
}
```
证书生成
```
cfssl gencert -initca ca-csr.json |cfssljson -bare ca -
cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -profile=www server-csr.json |cfssljson -bare server
```
创建目录并复制证书
```
mkdir /opt/etcd/{bin,cfg,ssl} -p
cp ca*.pem server*.pem /opt/etcd/ssl/
#然后分发到另外主机对应的etcd ssl目录下
```
下载etcd二进制包
```
下载etcd
https://github.com/etcd-io/etcd/releases/download/v3.2.12/etcd-v3.2.12-linux-amd64.tar.gz
```

etcd服务启动脚本
```
cat /usr/lib/systemd/system/etcd1.service

[Unit]
Description=Etcd Server
After=network.target
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
EnvironmentFile=/opt/etcd/cfg/etcd
ExecStart=/opt/etcd/bin/etcd \
--name=${ETCD_NAME} \
--data-dir=${ETCD_DATA_DIR} \
--listen-peer-urls=${ETCD_LISTEN_PEER_URLS} \
--listen-client-urls=${ETCD_LISTEN_CLIENT_URLS},http://127.0.0.1:2379 \
--advertise-client-urls=${ETCD_ADVERTISE_CLIENT_URLS} \
--initial-advertise-peer-urls=${ETCD_INITIAL_ADVERTISE_PEER_URLS} \
--initial-cluster=${ETCD_INITIAL_CLUSTER} \
--initial-cluster-token=${ETCD_INITIAL_CLUSTER_TOKEN} \
--initial-cluster-state=new \
--cert-file=/opt/etcd/ssl/server.pem \
--key-file=/opt/etcd/ssl/server-key.pem \
--peer-cert-file=/opt/etcd/ssl/server.pem \
--peer-key-file=/opt/etcd/ssl/server-key.pem \
--trusted-ca-file=/opt/etcd/ssl/ca.pem \
--peer-trusted-ca-file=/opt/etcd/ssl/ca.pem
Restart=on-failure
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```
启动etcd服务
```
systemctl daemon-reload
systemctl restart etcd1
systemctl enable etcd1
```
检查集群健康状态
```
/opt/etcd/bin/etcdctl --ca-file=/opt/etcd/ssl/ca.pem --cert-file=/opt/etcd/ssl/server.pem --key-file=/opt/etcd/ssl/server-key.pem --endpoints="https://192.168.0.220:2379,https://192.168.0.98:2379,https://192.168.0.216:2379" cluster-health

member 42c7b0b217d06ee6 is healthy: got healthy result from https://192.168.0.216:2379
member e3d82c6f58b2b6c8 is healthy: got healthy result from https://192.168.0.98:2379
member edabb0b65fe02a4c is healthy: got healthy result from https://192.168.0.220:2379
cluster is healthy
```

####Flannel
flannel需要用etcd存储子网信息，预先设置子网网段:
```
/opt/etcd/bin/etcdctl \
--ca-file=/opt/etcd/ssl/ca.pem \
--cert-file=/opt/etcd/ssl/server.pem \
--key-file=/opt/etcd/ssl/server-key.pem \
--endpoints="https://192.168.0.220:2379,\
https://192.168.0.98:2379,https://192.168.0.216:2379" \
set /coreos.com/network/config '{ "Network": "172.17.0.0/16","Backend": {"Type": "vxlan"}}'


{ "Network": "172.17.0.0/16","Backend": {"Type": "vxlan"}}
```

####node节点部署flannel
#####flannel下载部署
```
wget https://github.com/coreos/flannel/releases/download/v0.10.0/flannel-v0.10.0-linux-amd64.tar.gz
tar xf flannel-v0.10.0-linux-amd64.tar.gz
#创建kubernetes部署目录
mkdir /opt/kubernetes/{bin,cfg,ssl} -p
mv flanneld mk-docker-opts.sh /opt/kubernetes/bin
```
#####配置Flannel
```
cat /opt/kubernetes/cfg/flanneld

FLANNEL_OPTIONS="--etcd-endpoints=https://192.168.0.220:2379,https://192.168.0.98:2379,https://192.168.0.216:2379 -etcd-cafile=/opt/etcd/ssl/ca.pem -etcd-certfile=/opt/etcd/ssl/server.pem -etcd-keyfile=/opt/etcd/ssl/server-key.pem"
```
#####systemd管理flannel
```
cat /usr/lib/systemd/system/flanneld.service

[Unit]
Description=Flanneld overlay address etcd agent
After=network-online.target network.target
Before=docker.service

[Service]
Type=notify
EnvironmentFile=/opt/kubernetes/cfg/flanneld
ExecStart=/opt/kubernetes/bin/flanneld -ip-masq $FLANNEL_OPTIONS
ExecStartPost=/opt/kubernetes/bin/mk-docker-opts.sh -k DOCKER_NETWORK_OPTIONS -d /run/flannel/subnet.env
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

#####配置docker指定flannel子网段
```
vim /usr/lib/systemd/system/docker.service

EnvironmentFile=/run/flannel/subnet.env
ExecStart=/usr/bin/dockerd $DOCKER_NETWORK_OPTIONS

#重启flannel和docker
systemctl daemon-reload
systemctl start flanneld
systemctl enable flanneld
systemctl restart docker
```

检查是否生效，确保docker0和flannel.1在同一网段
```
docker0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default 
    link/ether 02:42:3d:3e:05:1a brd ff:ff:ff:ff:ff:ff
    inet 172.17.66.1/24 scope global docker0
       valid_lft forever preferred_lft forever

flannel.1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1450 qdisc noqueue state UNKNOWN group default 
    link/ether 32:ec:f7:fe:76:2a brd ff:ff:ff:ff:ff:ff
    inet 172.17.66.0/32 scope global flannel.1
       valid_lft forever preferred_lft forever
    inet6 fe80::30ec:f7ff:fefe:762a/64 scope link 
       valid_lft forever preferred_lft forever

#当前节点访问另一节点的docker0网段
ping 172.17.36.1
64 bytes from 172.17.36.1: icmp_seq=1 ttl=64 time=0.357 ms
64 bytes from 172.17.36.1: icmp_seq=2 ttl=64 time=0.404 ms
64 bytes from 172.17.36.1: icmp_seq=3 ttl=64 time=0.410 ms
64 bytes from 172.17.36.1: icmp_seq=4 ttl=64 time=0.431 ms
64 bytes from 172.17.36.1: icmp_seq=5 ttl=64 time=0.427 ms
```

###在master节点部署组件
创建kubernetes CA证书
```
cat ca-config.json

{
  "signing": {
    "default": {
      "expiry": "87600h"
    },
    "profiles": {
      "kubernetes": {
        "expiry": "87600h",
        "usages": [
          "signing",
          "key encipherment",
          "server auth",
          "client auth"
        ]
      }
    }
  }
}

cat ca-csr.json

{
  "CN": "kubernetes",
  "key": {
    "algo": "rsa",
    "size": 2048
  },
  "names": [
    {
      "C": "CN",
      "L": "Shanghai",
      "ST": "Shanghai",
      "O": "k8s",
      "OU": "System"
    }
  ]
}

cfssl gencert -initca ca-csr.json | cfssljson -bare ca -
```
生成api-server证书
```
cat server-csr.json

{
  "CN": "kubernetes",
  "hosts": [
    "10.0.0.1",
    "127.0.0.1",
    "192.168.0.220",
    "kubernetes",
    "kubernetes.default",
    "kubernetes.default.svc",
    "kubernetes.default.svc.cluster",
    "kubernetes.default.svc.cluster.local"
  ],
  "key": {
    "algo": "rsa",
    "size": 2048
  },
  "names": [
    {
      "C": "CN",
      "L": "Shanghai",
      "ST": "Shanghai",
      "O": "k8s",
      "OU": "System"
    }
  ]
}

cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -profile=kubernetes server-csr.json|cfssljson -bare server
```
生成 kube-proxy证书
```
cat kube-proxy-csr.json

{
  "CN": "kubernetes",
  "hosts": [],
  "key": {
    "algo": "rsa",
    "size": 2048
  },
  "names": [
    {
      "C": "CN",
      "L": "Shanghai",
      "ST": "Shanghai",
      "O": "k8s",
      "OU": "System"
    }
  ]
}

cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -profile=kubernetes kube-proxy-csr.json|cfssljson -bare kube-proxy
```
最终生成以下证书
```
$ ls *.pem
ca-key.pem  ca.pem  kube-proxy-key.pem  kube-proxy.pem  server-key.pem  server.pem
mkdir /opt/kubernetes/{bin,cfg,ssl} -p
cp ca* server* /opt/kubernetes/ssl/
```
#####部署api-server

```
wget https://dl.k8s.io/v1.11.1/kubernetes-server-linux-amd64.tar.gz
tar xf kubernetes-server-linux-amd64.tar.gz
cd kubernetes/server/bin
cp kube-apiserver kube-scheduler kube-controller-manager kubectl /opt/kubernetes/bin/
```
创建token文件
```
cat /opt/kubernetes/cfg/token.csv

3trC36y7zVzyHr80lH3J36FGEbjbVfhF,kubelet-bootstrap,10001,"system:kubelet-bootstrap"
```
创建apiserver配置文件
```
cat /opt/kubernetes/cfg/kube-apiserver

KUBE_APISERVER_OPTS="--logtostderr=true \
--v=4 \
--etcd-servers=https://192.168.0.220:2379,https://192.168.0.98:2379,https://192.168.0.216:2379 \
--bind-address=192.168.0.220 \
--secure-port=6443 \
--advertise-address=192.168.0.220 \
--allow-privileged=true \
--service-cluster-ip-range=10.0.0.0/24 \
--enable-admission-plugins=NamespaceLifecycle,LimitRanger,SecurityContextDeny,ServiceAccount,ResourceQuota,NodeRestriction \
--authorization-mode=RBAC,Node \
--enable-bootstrap-token-auth \
--token-auth-file=/opt/kubernetes/cfg/token.csv \
--service-node-port-range=30000-50000 \
--tls-cert-file=/opt/kubernetes/ssl/server.pem \
--tls-private-key-file=/opt/kubernetes/ssl/server-key.pem \
--client-ca-file=/opt/kubernetes/ssl/ca.pem \
--service-account-key-file=/opt/kubernetes/ssl/ca-key.pem \
--etcd-cafile=/opt/etcd/ssl/ca.pem \
--etcd-certfile=/opt/etcd/ssl/server.pem \
--etcd-keyfile=/opt/etcd/ssl/server-key.pem"
```
systemd管理kube-apiserver
```
cat /usr/lib/systemd/system/kube-apiserver.service

[Unit]
Description=kubernetes API Server
Documentation=https://github.com/kubernetes/kubernetes

[Service]
EnvironmentFile=/opt/kubernetes/cfg/kube-apiserver
ExecStart=/opt/kubernetes/bin/kube-apiserver $KUBE_APISERVER_OPTS
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
启动
```
systemctl daemon-reload
systemctl enable kube-apiserver
systemctl restart kube-apiserver
```

#####部署schduler
创建schduler配置文件

```
cat /opt/kubernetes/cfg/kube-scheduler

KUBE_SCHEDULER_OPTS="--logtostderr=true \
--v=4 \
--master=127.0.0.1:8080 \
--leader-elect"
```
systemd管理schduler
```
cat /usr/lib/systemd/system/kube-scheduler.service

[Unit]
Description=Kubernetes Scheduler
Documentation=https://github.com/kubernetes/kubernetes

[Service]
EnvironmentFile=-/opt/kubernetes/cfg/kube-scheduler
ExecStart=/opt/kubernetes/bin/kube-scheduler $KUBE_SCHEDULER_OPTS
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
启动
```
systemctl daemon-reload
systemctl enable kube-scheduler
systemctl restart kube-scheduler
```

#####部署controller-manager
```
cat /opt/kubernetes/cfg/kube-controller-manager

KUBE_CONTROLLER_MANAGER_OPTS="--logtostderr=true \
--v=4 \
--master=127.0.0.1:8080 \
--leader-elect=true \
--address=127.0.0.1 \
--service-cluster-ip-range=10.0.0.0/24 \
--cluster-name=kubernetes \
--cluster-signing-cert-file=/opt/kubernetes/ssl/ca.pem \
--cluster-signing-key-file=/opt/kubernetes/ssl/ca-key.pem \
--root-ca-file=/opt/kubernetes/ssl/ca.pem \
--service-account-private-key-file=/opt/kubernetes/ssl/ca-key.pem"
```
systemd管理controller-manager
```
cat /usr/lib/systemd/system/kube-controller-manager.service

[Unit]
Description=Kubernetes Controller Manager 
Documentation=https://github.com/kubernetes/kubernetes

[Service]
EnvironmentFile=-/opt/kubernetes/cfg/kube-controller-manager
ExecStart=/opt/kubernetes/bin/kube-controller-manager $KUBE_CONTROLLER_MANAGER_OPTS
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
启动
```
systemctl daemon-reload
systemctl enable kube-controller-manager
systemctl restart kube-controller-manager
```

#####kubectl查看当前集群状态
```
/opt/kubernetes/bin/kubectl get cs

NAME                 STATUS    MESSAGE              ERROR
controller-manager   Healthy   ok                   
scheduler            Healthy   ok                   
etcd-2               Healthy   {"health": "true"}   
etcd-1               Healthy   {"health": "true"}   
etcd-0               Healthy   {"health": "true"}
```

>[kubernetes版本](https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG-1.11.md)

####node节点部署

首先在master ssl主机下操作

绑定kubelet-bootstrap用户到系统集群角色
```
#创建角色RBAC
./kubectl create clusterrolebinding kubelet-bootstarp \
--clusterrole=system:node-bootstrapper \
--user=kubelet-bootstrap
```
创建kubeconfig文件
```
#创建kubelet bootstrapping kubeconfig
#指定apiserver内网负责均衡地址
export KUBE_APISERVER="https://192.168.0.220:6443"

#设置集群参数
/opt/kubernetes/bin/kubectl config set-cluster kubernetes \
--certificate-authority=./ca.pem \
--embed-certs=true \
--server=${KUBE_APISERVER} \
--kubeconfig=bootstrap.kubeconfig

#设置客户端认证参数
/opt/kubernetes/bin/kubectl config set-credentials kubelet-bootstrap \
--token=${BOOTSTRAP_TOKEN} \
--kubeconfig=bootstrap.kubeconfig

#设置上下文参数
/opt/kubernetes/bin/kubectl config set-context default \
--cluster=kubernetes \
--user=kubelet-bootstrap \
--kubeconfig=bootstrap.kubeconfig

#设置默认上下文
/opt/kubernetes/bin/kubectl config use-context default --kubeconfig=bootstrap.kubeconfig

-------------------------------------------------------

#创建kube-proxy kubeconfig文件
/opt/kubernetes/bin/kubectl config set-cluster kubernetes \
--certificate-authority=./ca.pem \
--embed-certs=true \
--server=${KUBE_APISERVER} \
--kubeconfig=kube-proxy.kubeconfig

/opt/kubernetes/bin/kubectl config set-credentials kube-proxy \
--client-certificate=./kube-proxy.pem \
--client-key=./kube-proxy-key.pem \
--embed-certs=true \
--kubeconfig=kube-proxy.kubeconfig

/opt/kubernetes/bin/kubectl config set-context default \
--cluster=kubernetes \
--user=kube-proxy \
--kubeconfig=kube-proxy.kubeconfig

/opt/kubernetes/bin/kubectl config use-context default --kubeconfig=kube-proxy.kubeconfig
```
将生成的bootstrap.kubeconfig kube-proxy.kubeconfig 复制到Node节点/opt/kubernetes/cfg下

复制Node 的kubelet和kube-proxy命令到/opt/kubernetes/bin

创建kubelet配置文件
```
cat /opt/kubernetes/cfg/kubelet

KUBELET_OPTS="--logtostderr=true \
--v=4 \
--hostname-override=192.168.0.98 \
--kubeconfig=/opt/kubernetes/cfg/kubelet.kubeconfig \
--bootstrap-kubeconfig=/opt/kubernetes/cfg/bootstrap.kubeconfig \
--config=/opt/kubernetes/cfg/kubelet.config \
--cert-dir=/opt/kubernetes/ssl \
--pod-infra-container-image=registry.cn-hangzhon.aliyuncs.com/google-containers/pause-amd64:3.0"
```
kubelet.config配置
```
cat /opt/kubernetes/cfg/kubelet.config

kind: KubeletConfiguration
apiVersion: kubelet.config.k8s.io/v1beta1
address: 192.168.0.98
port: 10250
readOnlyPort: 10255
cgroupDriver: cgroupfs
clusterDNS: ["10.0.0.2"]
clusterDomain: cluster.local.
failSwapOn: false
authentication:
  anonymous:
    enabled: true
  webhook:
    enabled: false
```
systemd管理kubelet
```
cat /usr/lib/systemd/system/kubelet.service

[Unit]
Description=Kubernetes Kubelet 
After=docker.service
Requires=docker.service

[Service]
EnvironmentFile=/opt/kubernetes/cfg/kubelet
ExecStart=/opt/kubernetes/bin/kubelet $KUBELET_OPTS
Restart=on-failure
KillMode=process

[Install]
WantedBy=multi-user.target
```
启动
```
systemctl daemon-reload
systemctl enable kubelet
systemctl restart kubelet
```

启动kubelet报错
```
1. F0907 11:46:35.522980    3387 server.go:262] failed to run Kubelet: unable to load bootstrap kubeconfig: invalid configuration: no 
server found for cluster "kubernetes"
解决：此问题是没有找到apiserver bootstarp-kubeconfig

2. system:anoymon 
 生成的bootstap-kubeconfig token问题一定要和你生成的token.csv一致
```

master审批node加入集群
```
/opt/kubernetes/bin/kubectl get csr
/opt/kubernetes/bin/kubectl certificate approve XXXXID
/opt/kubernetes/bin/kubectl get node

NAME            STATUS    ROLES     AGE       VERSION
192.168.0.216   Ready     <none>    12s       v1.11.1
192.168.0.98    Ready     <none>    22s       v1.11.1
```

#####Node部署kube-proxy
创建kube-proxy配置文件
```
cat  >> /opt/kubernetes/cfg/kube-proxy << EOF
KUBE_PROXY_OPTS="--logtostderr=true \
--v=4 \
--hostname-override=$NODEIP \
--cluster-cidr=10.0.0.0/24 \
--kubeconfig=/opt/kubernetes/cfg/kube-proxy.kubeconfig"
EOF
```

systemd管理kube-proxy
```
cat >> /usr/lib/systemd/system/kube-proxy.service << EOF
[Unit]
Description=Kubernetes Proxy  
After=network.target

[Service]
EnvironmentFile=/opt/kubernetes/cfg/kube-proxy
ExecStart=/opt/kubernetes/bin/kube-proxy \$KUBE_PROXY_OPTS
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
```
启动
```
systemctl daemon-reload
systemctl enable kube-proxy
systemctl restart kube-proxy
```

查看集群状态
```
kubectl get node

NAME            STATUS    ROLES     AGE       VERSION
192.168.0.216   Ready     <none>    4d        v1.11.1
192.168.0.98    Ready     <none>    4d        v1.11.1

kubectl get cs

NAME                 STATUS    MESSAGE              ERROR
controller-manager   Healthy   ok                   
scheduler            Healthy   ok                   
etcd-0               Healthy   {"health": "true"}   
etcd-1               Healthy   {"health": "true"}   
etcd-2               Healthy   {"health": "true"} 
```

运行一个实例测试
```
#创建一个Nging
kubectl run nginx --image=nginx --replicas=3
kubectl expose deployment nginx --port=88 --target-port=80 --type=NodePort

#kubectl get pods 查看pod是否正常启动
kubectl get svc

NAME         TYPE           CLUSTER-IP   EXTERNAL-IP   PORT(S)                         AGE
kubernetes   ClusterIP      10.0.0.1     <none>        443/TCP                         4d
nginx        NodePort       10.0.0.98    <none>        88:45110/TCP                    55s
```
访问Nginx http://NodeIP:45110进行测试
![Alt text](./1536656186274.png)
恭喜你集群搭建成功

#####部署Dashboard
```
cat dashboard-deployment.yaml

apiVersion: apps/v1beta2
kind: Deployment
metadata:
  name: kubernetes-dashboard
  namespace: kube-system
  labels:
    k8s-app: kubernetes-dashboard
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
spec:
  selector:
    matchLabels:
      k8s-app: kubernetes-dashboard
  template:
    metadata:
      labels:
        k8s-app: kubernetes-dashboard
      annotations:
        scheduler.alpha.kubernetes.io/critical-pod: ''
    spec:
      serviceAccountName: kubernetes-dashboard
      containers:
      - name: kubernetes-dashboard
        image: registry.cn-hangzhou.aliyuncs.com/kube_containers/kubernetes-dashboard-amd64:v1.8.1 
        resources:
          limits:
            cpu: 100m
            memory: 300Mi
          requests:
            cpu: 100m
            memory: 100Mi
        ports:
        - containerPort: 9090
          protocol: TCP
        livenessProbe:
          httpGet:
            scheme: HTTP
            path: /
            port: 9090
          initialDelaySeconds: 30
          timeoutSeconds: 30
      tolerations:
      - key: "CriticalAddonsOnly"
        operator: "Exists"
```
```
cat dashboard-rbac.yaml

apiVersion: v1
kind: ServiceAccount
metadata:
  labels:
    k8s-app: kubernetes-dashboard
    addonmanager.kubernetes.io/mode: Reconcile
  name: kubernetes-dashboard
  namespace: kube-system
---

kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  name: kubernetes-dashboard-minimal
  namespace: kube-system
  labels:
    k8s-app: kubernetes-dashboard
    addonmanager.kubernetes.io/mode: Reconcile
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: kubernetes-dashboard
    namespace: kube-system
```
```
cat dashboard-service.yaml

apiVersion: v1
kind: Service
metadata:
  name: kubernetes-dashboard
  namespace: kube-system
  labels:
    k8s-app: kubernetes-dashboard
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
spec:
  type: NodePort
  selector:
    k8s-app: kubernetes-dashboard
  ports:
  - port: 80
    targetPort: 9090
```

#####master部署coredns
```
cat coredns.yaml

apiVersion: v1
kind: ServiceAccount
metadata:
  name: coredns
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRole
metadata:
  labels:
    kubernetes.io/bootstrapping: rbac-defaults
  name: system:coredns
rules:
- apiGroups:
  - ""
  resources:
  - endpoints
  - services
  - pods
  - namespaces
  verbs:
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  annotations:
    rbac.authorization.kubernetes.io/autoupdate: "true"
  labels:
    kubernetes.io/bootstrapping: rbac-defaults
  name: system:coredns
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:coredns
subjects:
- kind: ServiceAccount
  name: coredns
  namespace: kube-system
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health
        kubernetes cluster.local  172.17.0.0/16 {
          pods insecure
          upstream
          fallthrough in-addr.arpa ip6.arpa
        }
        prometheus :9153
        proxy . /etc/resolv.conf
        cache 30
        reload
    }
---
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: coredns
  namespace: kube-system
  labels:
    k8s-app: kube-dns
    kubernetes.io/name: "CoreDNS"
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  selector:
    matchLabels:
      k8s-app: kube-dns
  template:
    metadata:
      labels:
        k8s-app: kube-dns
    spec:
      serviceAccountName: coredns
      tolerations:
        - key: "CriticalAddonsOnly"
          operator: "Exists"
      containers:
      - name: coredns
        image: coredns/coredns:1.1.3
        imagePullPolicy: IfNotPresent
        args: [ "-conf", "/etc/coredns/Corefile" ]
        volumeMounts:
        - name: config-volume
          mountPath: /etc/coredns
          readOnly: true
        ports:
        - containerPort: 53
          name: dns
          protocol: UDP
        - containerPort: 53
          name: dns-tcp
          protocol: TCP
        - containerPort: 9153
          name: metrics
          protocol: TCP
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            add:
            - NET_BIND_SERVICE
            drop:
            - all
          readOnlyRootFilesystem: true
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 60
          timeoutSeconds: 5
          successThreshold: 1
          failureThreshold: 5
      dnsPolicy: Default
      volumes:
        - name: config-volume
          configMap:
            name: coredns
            items:
            - key: Corefile
              path: Corefile
---
apiVersion: v1
kind: Service
metadata:
  name: kube-dns
  namespace: kube-system
  annotations:
    prometheus.io/scrape: "true"
  labels:
    k8s-app: kube-dns
    kubernetes.io/cluster-service: "true"
    kubernetes.io/name: "CoreDNS"
spec:
  selector:
    k8s-app: kube-dns
  clusterIP: 10.0.0.2
  ports:
  - name: dns
    port: 53
    protocol: UDP
  - name: dns-tcp
    port: 53
    protocol: TCP
```