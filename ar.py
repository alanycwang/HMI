import astropy.time
import astropy.units as u

import pandas as pd
from ftplib import FTP
from os.path import exists
import os, tarfile, pickle, re

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

def update_ar_data():

    def get_ar_number(date, num): #ar numbers are only 4 digits so some are repeated - need to make a distinction
        if date[:4] == "2002": #2002 is only year with both 9999 and 0000s
            if int(num) > 5000:
                return "0" + num
            else:
                return "1" + num
        elif int(date[:4]) > 2002:
            return "1" + num
        else:
            return "0" + num

    def parse_srs_data(file):
        data = []
        i = False
        skip = False
        with open(file, "r") as fh:
            for line in fh.readlines():
                if skip:
                    skip = False
                    continue
                #1: look for I
                if not i:
                    if line[0:2] == "I.":
                        i = True
                        skip = True
                #2: parse I data
                else:
                    # 3: stop at IA
                    if line[0:2] == "IA" or line.lower() == "none":
                        break
                    else:
                        # Nmbr Location Lo Area Z LL NN Mag Type
                        a = line.strip("\n").split(" ")
                        a[0] = get_ar_number(file[-15:-11], a[0])
                        a = [x for x in a if x != '']
                        a.append(astropy.time.Time.strptime(file[-15:-7], "%Y%m%d"))
                        #print(file[-15:-7])
                        data.append(a)
        # print(data)
        return data

    # 'data' is an array: [most recent date, data]
    if not exists('./data/srs/parseddata.pkl'):
        data = [0, {}]
    else:
        with open('./data/srs/parseddata.pkl', 'rb') as fh:
            data = pickle.load(fh)

    ftp = FTP('ftp.swpc.noaa.gov')
    ftp.login()
    ftp.cwd('pub/warehouse')

    files = []
    for file in ftp.nlst():
        if file.isnumeric() and int(file)*10000 >= data[0]:
            files.append(file)
    files.sort()

    # file = "2022/SRS/20220511SRS.txt"
    # with open(f"./data/srs/{2022}_SRS/poop", 'wb') as fh:
    #     ftp.retrbinary(f"retr {file}", fh.write)

    td = []

    for year in files:
        if f"{year}/{year}_SRS.tar.gz" in ftp.nlst(year):
            with open(f"./data/srs/{year}_SRS.tar.gz", 'wb') as fh:
                ftp.retrbinary(f"retr {year}/{year}_SRS.tar.gz", fh.write)
            with tarfile.open(f"./data/srs/{year}_SRS.tar.gz") as fh:
                fh.extractall("./data/srs")
            for file in os.listdir(f"./data/srs/{year}_SRS"):
                td.extend(parse_srs_data(f"./data/srs/{year}_SRS/{file}"))
        else:
            for file in sorted(ftp.nlst(f"{year}/SRS")):
                if not exists(f"./data/srs/{year}_SRS"):
                    os.mkdir(f"./data/srs/{year}_SRS")
                with open(f"./data/srs/{year}_SRS/{file[-15:]}", 'wb') as fh:
                    if int(file[-15:-7]) > data[0]: ftp.retrbinary(f"retr {file}", fh.write)
                data[0] = int(file[-15:-7])
                td.extend(parse_srs_data(f"./data/srs/{year}_SRS/{file[-15:]}"))

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
        if not cf:
            continue


        lst.append(key)
    return lst

