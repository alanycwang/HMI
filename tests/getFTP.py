import subprocess

while True: #downloads and installs any missing packages
    try: #try to import
        import ftplib, tarfile, pickle, os, shutil
        break
    except ModuleNotFoundError as e: #if any package is missing, download then try again
        module = str(e)[17:-1].replace('-', '_')
        subprocess.call(["python", "-m", "pip", "install", "--trusted-host", "pypi.org", "--trusted-host", "files.pythonhosted.org", module])
d = input() #program will download all data created after this date to avoid having duplicates ex: 20220802 for Aug 2, 2022
series = input() #specify which data series to download from (events, GEOA, RSGA, SGAS, SRS)
wd = input() #specify working directory
print('received')

#cd
os.chdir(wd)

#login to ftp server
ftp = ftplib.FTP('ftp.swpc.noaa.gov')
ftp.login()
ftp.cwd('pub/warehouse')

#get a list of every folder that contains data we want
files = []
for file in ftp.nlst(): #iterate through all files in /pub/warehouse
    try: #the folders we want are named after the year in which the data was taken, we can therefore filter out any file that isn't a year number
        int(file)
    except ValueError: #if the folder name is not a number, skip
        continue
    if (int(file))*10000 >= d - d%10000: #make sure the folder year is after the specified date
        files.append(file)
files.sort()

folder = "ftp_download_%s" % (series)
if os.path.exists(folder):
    while True: #this keeps breaking but it eventually works if you keep running it until it stops error-ing
        try:
            shutil.rmtree(folder) #delete folder if it somehow still exists
            break
        except OSError:
            continue
os.mkdir(folder) #create directory for all files
for year in files:
    file = "%s/%s_%s.tar.gz" % (year, year, series) #can't use new methods for string formatting since server might be running python 2
    if file in ftp.nlst(year): #data for the current year isn't zipped, so there needs to be a different method for that 
        with open(year + ".tar.gz", 'wb') as fh: #retrieve data from ftp server
            ftp.retrbinary("retr %s" % (file), fh.write)
        with tarfile.open(year + ".tar.gz") as fh: #unzip
            fh.extractall(folder)
        os.remove(year + ".tar.gz") #delete zip file
    else:
        f = "%s/%s_%s" % (folder, year, series) #path to folder for this year
        ftp_f = year + "/" + series
        if series == "events":
            ftp_f = "%s/%s_%s" % (year, year, series)
        for file_ in sorted(ftp.nlst(ftp_f)): #iterate through files in folder
            out_file = f + "/" + file_.split('/')[-1]
            if not os.path.exists(f): #create folder if it doesn't yet exist
                os.mkdir(f)
            with open(out_file, 'wb') as fh: #retrieve file
                if int(file_.split('/')[-1][:8]) > d: ftp.retrbinary("retr %s" % (file_), fh.write)
            d = int(file_.split('/')[-1][:8]) #update d

with tarfile.open(folder + ".tar.gz", "w:gz") as fh:
    for root, dirs, files in os.walk(folder):
        for file in files:
            fh.add(os.path.join(root, file))

shutil.rmtree(folder) #remove all temporary files once zipped
print(d)