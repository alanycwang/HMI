import astropy.time
import astropy.units as u

import pandas as pd
from ftplib import FTP
from os.path import exists
import os, tarfile, pickle, re, getSRS, paramiko

class AR():
    start = astropy.time.Time.strptime("25000101", "%Y%m%d")
    end = astropy.time.Time.strptime("19700101", "%Y%m%d")
    mag_type = []

    def __init__(self, number, df):
        for i, row in df.iterrows():
            self.start = min(self.start, row["Date"])
            self.end = max(self.end, row["Date"])
            if len(self.mag_type) >= 1 and row["Mag Type"] == self.mag_type[-1][0]:
                self.mag_type[-1][1] += 1
            else:
                self.mag_type.append([row["Mag Type"], 1])

            if i != 0 and row["Location"][3] != df["Location"][i - 1][3]:
                self.ct = df["Date"][i - 1]
        self.df = df
        self.number = number

    #entries are expected to be appended in order
    def append(self, row):
        self.start = min(self.start, row[-1])
        self.end = max(self.end, row[-1])
        self.df.append(row)
        if row[-2] == self.mag_type[-1][0]:
            self.mag_type[-1][1] += 1
        else:
            self.mag_type.append([row[-2], 1])
        self.longevity = len(self.df)

        if len(self.df) != 1 and row[1][3] != self.df["Location"][-2][3]:
            self.ct = self.df["Date"][-2]

def update_ar_data(ssh_tunnel=True, ssh_hostname=None, ssh_username=None, ssh_password=None, ssh_wd=""):

    # 'data' is an array: [most recent date, data]
    if not exists('./data/srs/parseddata.pkl'):
        data = [0, {}]
    else:
        with open('./data/srs/parseddata.pkl', 'rb') as fh:
            data = pickle.load(fh)
    
    print(data[0])

    if ssh_tunnel:
        #login
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=ssh_hostname, username=ssh_username, password=ssh_password)
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {ssh_wd}")
        stdout.channel.set_combine_stderr(True)
        stdout.channel.recv_exit_status()

        #upload script
        ftp_client = ssh_client.open_sftp()
        ftp_client.put('./getSRS.py', f'{ssh_wd}/getSRS.py')

        #run script
        d = data[0]
        while True:
            stdin, stdout, stderr = ssh_client.exec_command(f"python {ssh_wd}/getSRS.py")
            stdin.write(f"{d}\n")
            stdin.flush()
            stdin.write(f"\'{ssh_wd}/td.pkl\'\n")
            stdin.flush()
            stdout.channel.set_combine_stderr(True)
            stdout.channel.recv_exit_status()
            for i, line in enumerate(stdout.readlines()):
                print(line)
                if len(line) == len("failed\n") and line == "failed\n":
                    print("failed, trying again:", stdout.readlines()[i + 1])
                    d = int(stdout.readlines()[i + 2])
                    continue
            break
        
        #retrieve file
        if not exists("./data/srs"):
            os.makedirs('./data/srs')
        ftp_client.get(f"{ssh_wd}/td.pkl", "./data/srs/td.pkl")
        ftp_client.close()

        #remove files
        stdin, stdout, stderr = ssh_client.exec_command(f"rm {ssh_wd}/td.pkl")
        stdout.channel.set_combine_stderr(True)
        stdout.channel.recv_exit_status()
        stdin, stdout, stderr = ssh_client.exec_command(f"rm {ssh_wd}/getSRS.py")
        stdout.channel.set_combine_stderr(True)
        stdout.channel.recv_exit_status()

        ssh_client.close()

        with open('./data/srs/td.pkl', 'rb') as fh:
            data[0], td = pickle.load(fh)
    else:
        data[0], td = getSRS.get_files(data[0])
    for line in td:
            line[-1] = astropy.time.Time.strptime(line[-1], "%Y%m%d")

    for item in td:
        if len(item) != 9:
            print(item)
            continue
        if item[0] in data[1]:
            data[1][item[0]].append(item[1:])
        else:
            data[1][item[0]] = AR(item[0],  pd.DataFrame([item[1:]], columns=["Location", "Lo", "Area", "Z", "LL", "NN", "Mag Type", "Date"]))

    with open('./data/srs/parseddata.pkl', 'wb') as fh:
        pickle.dump(data, fh)

    return data

def filter_ar(data, start=None, end=None, ct=None, longevity=None, centering=None, mag_type=None): #fix centering later
    if centering is None:
        cf = lambda _: True
    else:
        d = re.search(centering[0], "^(\*\/)?([NS\*])(\d{1,2}|\*|((\d{1,2}|\*):(\d{1,2}|\*)))([EW\*])(\d{1,2}|\*|((\d{1,2}|\*):(\d{1,2}|\*)))(\/\*)?$")
        d2 = re.search(centering[1], "^(\*\/)?(d{1,2})(\/\*)?")
        def check_centering(ar):
            value = ar.df["Location"][int(d2.group(2))]
            if d.group(2) != "*" and d.group(2) != value[0]:
                return False
            if ":" in d.group(3):
                if d.group(5) != "*" and int(d.group(5) > value[1:3]):
                    return False
                if d.group(6) != "*" and int(d.group(6) < value[1:3]):
                    return False
            if d.group(3) != "*" and d.group(3) != value[1:3]:
                return False
            if d.group(7) != "*" and d.group(7) != value[3]:
                return False
            if ":" in d.group(8):
                if d.group(10) != "*" and int(d.group(10) > value[4:6]):
                    return False
                if d.group(11) != "*" and int(d.group(11) < value[4:6]):
                    return False
            if d.group(8) != "*" and d.group(8) != value[1:3]:
                return False
            return True
        cf = check_centering

    lst = []
    for key, value in data[1].items():
        if start is not None and value.start < start:
            continue
        if end is not None and value.end > end:
            continue
        if ct is not None and value.ct - ct <= 1*u.day:
            continue
        if longevity is not None and value.longevity != longevity:
            continue
        if not cf(value.centering):
            continue


        lst.append(key)
    return lst

