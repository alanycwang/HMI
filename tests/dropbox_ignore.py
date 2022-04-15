#run before downloading anything so Dropbox doesn't fill up
import subprocess

if __name__ == '__main__':
    subprocess.call(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe Set-Content -Path 'C:\Users\alany\Dropbox\Projects\Code\LMSAL\HMI\data' -Stream com.dropbox.ignored -Value 1", shell=True)