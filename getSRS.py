import subprocess

while True:
    try:
        from ftplib import FTP
        import tarfile, pickle, os, shutil
        break

    except ModuleNotFoundError as e:
        m = str(e)[17:-1].replace('-', '_')
        subprocess.call(["python", "-m", "pip", "install", "--trusted-host", "pypi.org", "--trusted-host", "files.pythonhosted.org", m, "-vvv"])
            
def get_files(d):
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
                        a.append(file[-15:-7])
                        #print(file[-15:-7])
                        data.append(a)
        # print(data)
        return data

    ftp = FTP('ftp.swpc.noaa.gov')
    ftp.login()
    ftp.cwd('pub/warehouse')

    print("Successfully logged in")

    files = []
    for file in ftp.nlst():
        try:
            int(file)
        except ValueError:
            continue
        if int(file)*10000 >= d:
            files.append(file)
    files.sort()

    # file = "2022/SRS/20220511SRS.txt"
    # with open(f"./data/srs/{2022}_SRS/poop", 'wb') as fh:
    #     ftp.retrbinary(f"retr {file}", f.write)

    td = []

    for year in files:
        try:
            print(year)
            if "%s/%s_SRS.tar.gz" % (str(year), str(year)) in ftp.nlst(year):
                with open("./%s_SRS.tar.gz" % (str(year)), 'wb') as fh:
                    ftp.retrbinary("retr ./%s/%s_SRS.tar.gz" % (str(year), str(year)), fh.write)
                with tarfile.open("./%s_SRS.tar.gz" % (str(year))) as fh:
                    fh.extractall("./")
                for file in os.listdir("./%s_SRS" % (str(year))):
                    td.extend(parse_srs_data("./%s_SRS/%s" % (str(year), file)))
                os.remove("./%s_SRS.tar.gz" % (str(year)))
                shutil.rmtree("./%s_SRS" % (str(year)))
            else:
                for file in sorted(ftp.nlst("./%s/SRS" % (str(year)))):
                    if not os.path.exists("./%s_SRS" % (str(year))):
                        os.mkdir("./%s_SRS" % (str(year)))
                    with open("./%s_SRS/%s" % (str(year), file[-15:]), 'wb') as fh:
                        if int(file[-15:-7]) > d: ftp.retrbinary("retr ./%s" % (file), fh.write)
                    d = int(file[-15:-7])
                    td.extend(parse_srs_data("./%s_SRS/%s" % (str(year), file[-15:])))
                shutil.rmtree("./%s_SRS" % (str(year)))
        except Exception as e:
            print("failed")
            print(e)
            print(d)
    return d, td

if __name__ == '__main__':
    d = input()
    out_file = input()
    print(out_file)
    print('received')

    d, td = get_files(d)

    with open(out_file, 'wb') as fh:
        pickle.dump((d, td), fh)