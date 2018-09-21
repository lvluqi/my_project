from django.shortcuts import render, HttpResponse, redirect
from django import http
# Create your views here.
from app01.models import *


def login(request):
    return redirect(request, "/index/")


def index(request):
    return render(request, "index.html")

def check_host():
    host_list = Host.objects.all().get("hostname")
    print(host_list.hostname)
    return host_list

def upload(request):
    from common import common
    import os
    if request.method == "POST":
        file_obj = request.FILES.get('file')
        print(file_obj)
        host = request.POST.get("host")
        pwd = request.POST.get("pwd")
        user = request.POST.get("user")
        print(host, pwd, user)
        with open("upload/" + file_obj.name, 'wb') as f:
            for line in file_obj:
                f.write(line)
        a = common.SshUpFile(hostname=host, username=user, password=pwd)
        localfile = "upload/" + file_obj.name
        remotepath = "/root/"
        remotefile = remotepath + "%s" % file_obj.name
        res = a.up_file(localfile, remotefile)
        print(res)
        return HttpResponse("本地文件:%s 已上传至%s的%s目录" % (file_obj.name, host, remotepath))
    # obj_list = check_host()
    return render(request, 'upload.html')



