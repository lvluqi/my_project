class SshUpFile:
    def __init__(self,hostname,username,password,port=22):

        self.hostname = hostname
        self.port = port
        self.username =username
        self.password = password

    def up_file(self,file,remotepath):
        import datetime
        import paramiko
        print('上传开始')
        # begin = datetime.datetime.now()

        #ssh控制台
        # ssh = paramiko.SSHClient()
        # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        # ssh.connect(hostname=self.hostname,port=self.port)

        #ssh传输
        transport = paramiko.Transport(self.hostname,self.port)
        transport.connect(username=self.username,password=self.password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        try:
            sftp.put(file,remotepath=remotepath)
        except Exception as e:
            print(e)

        sftp.close()

