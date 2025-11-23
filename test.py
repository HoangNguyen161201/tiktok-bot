from untils import upload_yt
import os
from db import  find_one_ip, get_times
from datetime import datetime, timedelta

times = get_times()
data_by_ip = find_one_ip()
youtubes = data_by_ip['youtubes']
youtube = youtubes[0]
now = datetime.now()


print(youtube)
upload_yt(
    youtube['name'],
    youtube['user_agent'],
    youtube['proxy'],
    '',
    '',
    '',
    os.path.abspath(f"./video/final.mp4"),
)