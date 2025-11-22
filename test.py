from untils import upload_yt
import os
from db import  find_one_ip, get_times
from datetime import datetime, timedelta

times = get_times()
data_by_ip = find_one_ip()
youtubes = data_by_ip['youtubes']
youtube = None
now = datetime.now()
for item in youtubes:
    next_time_str = item.get("next_time")
    if not next_time_str:
        youtube = item
        break
    try:
        next_time = datetime.fromisoformat(next_time_str)
    except ValueError:
        youtube = item
        break
    if next_time + timedelta(hours= times[0]['time2'] / 60 ) < now:
        youtube = item
        break

upload_yt(
    youtube['name'],
    youtube['user_agent'],
    youtube['proxy'],
    '',
    '',
    '',
    os.path.abspath(f"./video/final.mp4"),
)