import paramiko

#ssh host info
hostname = 'out.lmsal.com'
username = 'awang'
password = 'Alan@999'
ssh_wd = '/sanhome/awang' #working directory for ssh - use an absolute path - paramiko is stupid and somehow yet again has some crazy inexplicable problem - connecting to the ssh client and using cd doesn't actually use this directory, but I will need a directory to upload the files
d = 0 #ignore this if downloading for the first time - if you want to update an existing set of data, use the d output from the last time you ran this script
series = "RSGA" #specify which data series to download from (events, GEOA, RSGA, SGAS, SRS)

#login
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_client.connect(hostname=hostname, username=username, password=password)

#switch to working directory
stdin, stdout, stderr = ssh_client.exec_command(f"cd {ssh_wd}")
stdout.channel.set_combine_stderr(True) #the creators of paramiko in all their infinite wisdom decided that it would be better for the python script to continue running without waiting for the ssh server to finish executing the command - this will force python to wait
stdout.channel.recv_exit_status()

#upload script
ftp_client = ssh_client.open_sftp() #create sftp client for file transfer
ftp_client.put('getFTP.py', f'{ssh_wd}/getFTP.py')

#run script
stdin, stdout, stderr = ssh_client.exec_command(f"python {ssh_wd}/getFTP.py")
stdin.write(str(d) + '\n')
stdin.flush()
stdin.write(f'\'{series}\'\n')
stdin.flush()
stdin.write(f'\'{ssh_wd}\'\n')
stdin.flush()
stdout.channel.set_combine_stderr(True) #wait for program to run (again)
stdout.channel.recv_exit_status()

#in case something goes wrong
out = stdout.readlines()
if "Traceback (most recent call last):\n" in out:
    for line in out:
        print(line, end='')
    print()
    print()
    raise Exception

#retrieve file
ftp_client.get(f'{ssh_wd}/ftp_download_{series}.tar.gz', f'ftp_download_{series}.tar.gz')
ftp_client.close()

#remove file
stdin, stdout, stderr = ssh_client.exec_command(f"rm {ssh_wd}/ftp_download_{series}.tar.gz")
stdout.channel.set_combine_stderr(True)
stdout.channel.recv_exit_status()
stdin, stdout, stderr = ssh_client.exec_command(f"rm {ssh_wd}/getFTP.py")
stdout.channel.set_combine_stderr(True)
stdout.channel.recv_exit_status()

ssh_client.close()

print(out[-1][0:-1]) #new d for use next time
#dont worry about the TypeError - the code does what it needs to do :) and I'm not spending another 2 hours debugging more of Paramiko's defects