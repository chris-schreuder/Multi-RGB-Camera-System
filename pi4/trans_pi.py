from glob import glob
import shutil
from fastprogress import progress_bar
import os

file = glob('/home/p*/*.py')
raspberry_pi_index = file[0].split('/')[2][-1]

print(len(glob(f"/media/pi{raspberry_pi_index}/T7/data/**/*"))+len(glob(f"/media/pi{raspberry_pi_index}/T7/data/**/**/*")))

files1 = glob('/home/p*/data/**/*')
files2 = glob('/home/p*/data/**/**/*')

files = files1+files2
print(len(files))
files = [file for file in files if not os.path.isdir(file)]
files_to = [file.replace(f"/home/pi{raspberry_pi_index}", f"/media/pi{raspberry_pi_index}/T7") for file in files]
print(len(files))
# print(files[:5])
print(len(files_to))
# print(files_to[:5])

for file_frame, file_to in progress_bar(zip(files, files_to), total=len(files)):

    if not os.path.exists(file_to):
        os.makedirs(os.path.dirname(file_to), exist_ok=True)
        shutil.copy(file_frame, file_to)
    # os.makedirs(os.path.dirname(file_to), exist_ok=True)
    # shutil.copy(file_frame, file_to)