import google.generativeai as genai
import pyktok as pyk
import requests
import os
import shutil
import subprocess
import json
import cv2
from PIL import Image
from PIL import Image, ImageDraw, ImageFont, ImageOps
import textwrap
from io import BytesIO
import time
import pyperclip
import psutil

from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc

def download_tiktok_video_n_comment(short_url, folder_video_path, data_path, comment_path, out_path):
    response = requests.get(short_url, allow_redirects=True)
    print('hoang 1')
    print(response)
    long_url = response.url
    print('hoang 2')
    print(long_url)
    os.makedirs(folder_video_path, exist_ok=True)
    print('hoang 3')
    pyk.save_tiktok(long_url,
                    True,
                    data_path)
    print('hoang ')

    folder = '.'
    mp4_files = [f for f in os.listdir(folder) if f.endswith('.mp4')]
    old_file = mp4_files[0]
    shutil.move(old_file, out_path)

    pyk.save_tiktok_comments(long_url, comment_count=30, filename=comment_path,
                             save_comments=True, return_comments=False)


def generate_content(content, model='gemini-1.5-flash', api_key=None):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model)
    response = model.generate_content(content)
    return response.text


def get_content_cv(data_path, comment_path):
    import pandas as pd
    df = pd.read_csv(data_path)
    author_name = df._get_value(0, 'author_name')
    video_description = df._get_value(0, 'video_description')

    df = pd.read_csv(comment_path)
    index = 0
    comments = []
    while index < df.__len__():
        comments.append(df._get_value(index, 'text'))
        index += 1

    return {
        'author_name': author_name,
        'title': video_description,
        'comments': comments,
    }


def crop_video(input_file, output_file):
    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-vf",
        "scale=1080:-2:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
        "crop=iw-200:ih-200:100:100",  # crop 100px mỗi cạnh
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "copy",
        output_file
    ]

    process = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)


def get_video_duration(path):
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json',
        path
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    info = json.loads(result.stdout)
    duration = float(info['format']['duration'])
    return duration


def get_3_pie_video(input_file, output_files):
    duration = get_video_duration(input_file)
    segment_duration = duration / 3

    for i, output_file in enumerate(output_files):
        start_time = i * segment_duration

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),         # đặt trước -i → cắt chính xác
            "-i", input_file,
            "-t", str(segment_duration),
            "-c", "copy",
            "-avoid_negative_ts", "1",      # fix lỗi đứng hình & lệch frame
            output_file
        ]

        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Created: {output_file}")


def add_audio(input_file, video_no_audio, output_file):
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_no_audio,      # video đã zoom nhưng không có âm thanh
        "-i", input_file,          # video gốc để lấy audio
        "-c:v", "copy",            # giữ nguyên video, không mã hóa lại
        "-c:a", "copy",            # giữ nguyên audio, không mã hóa lại
        "-map", "0:v:0",           # lấy video từ file 0
        "-map", "1:a:0",           # lấy audio từ file 1
        output_file
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def get_real_fps(video_path):
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-select_streams", "v:0",
        "-show_streams", video_path
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    info = json.loads(result.stdout)
    fps_text = info["streams"][0]["r_frame_rate"]  # dạng "30000/1001"
    num, den = fps_text.split('/')
    return float(num) / float(den)


def zoom_video(input_file, output_file, max_zoom=1.5):
    video_no_audio_path = 'draff.mp4'
    cap = cv2.VideoCapture(input_file)
    if not cap.isOpened():
        raise ValueError(f"Không thể mở video: {input_file}")

    fps = get_real_fps(input_file)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # ❗ Không dùng frame_count từ OpenCV
    # → Tự đếm frame thực tế
    actual_frames = 0
    while True:
        ret, _ = cap.read()
        if not ret:
            break
        actual_frames += 1

    # mở lại video lần 2 để xử lý
    cap.release()
    cap = cv2.VideoCapture(input_file)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_no_audio_path, fourcc, fps, (w, h))

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Zoom chính xác dựa trên số frame thật
        zoom = 1 + (max_zoom - 1) * frame_idx / actual_frames

        new_w = int(w / zoom)
        new_h = int(h / zoom)
        x1 = (w - new_w) // 2
        y1 = (h - new_h) // 2

        cropped = frame[y1:y1+new_h, x1:x1+new_w]
        resized = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

        out.write(resized)
        frame_idx += 1

    cap.release()
    out.release()

    add_audio(input_file, video_no_audio_path, output_file)
    print(f"Hoàn thành! Video xuất ra: {output_file}")


def concat_videos(video_paths, output_file="output.mp4"):
    if len(video_paths) < 2:
        raise ValueError("Cần ít nhất 2 video để nối lại.")

    # Tạo file tạm chứa danh sách video cho FFmpeg
    list_file = "videos_to_concat.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for path in video_paths:
            if not os.path.exists(path):
                raise ValueError(f"Không tìm thấy file: {path}")
            f.write(f"file '{os.path.abspath(path)}'\n")

    # Lệnh FFmpeg để nối:
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_file
    ]

    # Chạy FFmpeg
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print(f"Hoàn thành! Video đã nối: {output_file}")


def overlay_video_and_image(video_path, bg_path, overlay_image_path, output_path):
    width = 932
    height = 1664
    top_offset = 70       # khoảng cách từ top
    bottom_offset = 60    # khoảng cách overlay image từ bottom
    left_offset = 67      # khoảng cách overlay image từ left

    filter_complex = (
        # Resize video và đặt cách top 50px
        f"[0:v]scale={width}:{height}[vid];"
        # Overlay video lên background, cách top 50
        f"[1:v][vid]overlay=(W-w)/2:{top_offset}[tmp];"
        # Overlay hình ảnh khác lên background+video
        f"[tmp][2:v]overlay={left_offset}:(H-h-{bottom_offset}):format=auto"
    )

    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-i', bg_path,
        '-i', overlay_image_path,
        '-filter_complex', filter_complex,
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        output_path
    ]

    subprocess.run(cmd, check=True)


def overlay_image_on_image(bg_path, overlay_path, output_path, position=(50, 50), overlay_size=None, title=None, old_price= 0, new_price = 0):
    radius = 18  # border-radius cố định

    # Mở ảnh nền và overlay
    background = Image.open(bg_path).convert("RGBA")
    response = requests.get(overlay_path)
    overlay = Image.open(BytesIO(response.content)).convert("RGBA")

    # Resize overlay nếu cần
    if overlay_size is not None:
        overlay = ImageOps.fit(
            overlay,
            overlay_size,            # (width, height)
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5)     # crop ở giữa giống CSS
        )

    # Tạo mask bo góc
    w, h = overlay.size
    mask = Image.new("L", (w, h), 0)  # ảnh đen mask
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)

    # Áp mask lên overlay
    overlay.putalpha(mask)

    # Ghép overlay lên background
    background.paste(overlay, position, overlay)

    if title:
        if len(title) > 55:
            title = title[:55] + "..."
        draw = ImageDraw.Draw(background)
        font = ImageFont.truetype('./static/Montserrat-SemiBold.ttf', 35)

        max_width = 850
        x, y = 370, 200

        avg_char_width = font.getlength("A")
        chars_per_line = max_width // avg_char_width
        wrapped = textwrap.fill(title, width=int(chars_per_line))
        draw.multiline_text((x, y), wrapped, font=font,
                            fill='black', spacing=10)

    draw = ImageDraw.Draw(background)
    font = ImageFont.truetype('./static/Montserrat-SemiBold.ttf', 30.2)
    x, y = 370, 390
    wrapped = textwrap.fill('Mua ngay sản phẩm, link trong bio!')
    draw.multiline_text((x, y), wrapped, font=font,
                        fill='red', spacing=10)

    # old price
    draw = ImageDraw.Draw(background)
    font = ImageFont.truetype('./static/Montserrat-Medium.ttf', 30)
    x, y = 370, 306
    formatted = f"{old_price:,}".replace(",", ".") + " VND"
    wrapped = textwrap.fill(formatted)
    draw.multiline_text((x, y), wrapped, font=font,
                        fill='grey', spacing=10)
    
    draw.line((370, 325, 595 if old_price >= 1000000 else 555 if old_price <= 99999 else 575, 325), fill='grey', width=3)  # ví dụ màu đỏ, dày 5px
    
    # new price
    draw = ImageDraw.Draw(background)
    font = ImageFont.truetype('./static/Montserrat-SemiBold.ttf', 38)
    x, y = 610, 300
    formatted = f"{new_price:,}".replace(",", ".") + " VND"
    wrapped = textwrap.fill(formatted)
    draw.multiline_text((x, y), wrapped, font=font,
                        fill='red', spacing=10)
    
    # percent
    draw.rounded_rectangle(
        [220, 400, 335, 450],
        fill=(255, 230, 230),
        radius=15
    )
    percent_drop = ((old_price - new_price) / old_price) * 100
    percent_drop = round(percent_drop)
    draw = ImageDraw.Draw(background)
    font = ImageFont.truetype('./static/Montserrat-SemiBold.ttf', 38)
    x, y = 230 if percent_drop >= 10 else 245, 400
    wrapped = textwrap.fill(f'-{percent_drop}%')
    draw.multiline_text((x, y), wrapped, font=font,
                        fill='red', spacing=10)
    
    # Lưu kết quả
    background.save(output_path)


def check_exist_video_hd(browser):
    timeout = 20 * 60
    start_time = time.time()
    is_not_find_status = False
    while True:
        # element = browser.find_elements(By.XPATH, '//*[@check-status="UPLOAD_CHECKS_DATA_COPYRIGHT_STATUS_COMPLETED" or @checks-summary-status-v2="UPLOAD_CHECKS_DATA_SUMMARY_STATUS_STARTED" or @check-status="UPLOAD_CHECKS_DATA_COPYRIGHT_STATUS_STARTED"]')
        element = browser.find_elements(By.XPATH, '//*[@check-status="UPLOAD_CHECKS_DATA_COPYRIGHT_STATUS_COMPLETED" or @checks-summary-status-v2="UPLOAD_CHECKS_DATA_SUMMARY_STATUS_COMPLETED" or @checks-summary-status-v2="UPLOAD_CHECKS_DATA_SUMMARY_STATUS_STARTED"]')
        if element:
            break  # Thoát vòng lặp nếu tìm thấy
        
        elapsed = time.time() - start_time
        if elapsed > timeout:
            is_not_find_status = True
            break
        print("Chưa tìm thấy, tiếp tục kiểm tra...")
        time.sleep(2)  # Đợi 2 giây trước khi kiểm tra lại

    if is_not_find_status is True:
        browser.quit()
        raise Exception("lỗi upload youtube")


def get_copy_profile_driver(name_chrome_yt, user_agent=None, proxy=None):
    chrome_options = Options()

    # 🧩 Cấu hình profile (đường dẫn tuyệt đối, không lỗi khóa)
    name_folder = name_chrome_yt
    user_data_dir = os.path.join(os.getcwd(), 'youtubes', name_folder)
    user_data_dir_abspath = os.path.abspath(user_data_dir)
    temp_profile_path = os.path.join(os.getcwd(), 'youtubes', f"temp_{name_folder}")
    
    # ⚙️ Xóa nếu đã tồn tại (tránh lỗi copy)
    if os.path.exists(temp_profile_path):
        shutil.rmtree(temp_profile_path)

    # ⚙️ Copy profile gốc sang profile tạm
    def ignore_func(dir, files):
        # Bỏ qua các file đặc biệt của Chrome
        ignored = {'SingletonLock', 'SingletonSocket', 'SingletonCookie'}
        return [f for f in files if f in ignored]
    shutil.copytree(user_data_dir_abspath, temp_profile_path, dirs_exist_ok=True, ignore=ignore_func)
        
    chrome_options.add_argument(f"--user-data-dir={temp_profile_path}")
    chrome_options.add_argument("--profile-directory=Default")
    # chrome_options.add_argument("--disable-quic")

    # 🧩 Proxy (nếu có)
    # if proxy:
    #     chrome_options.add_argument(f"--proxy-server={proxy}")

    # 🧩 User-Agent (nếu có)
    if user_agent:
        chrome_options.add_argument(f"--user-agent={user_agent}")

    # ⚙️ Các flag ổn định (tránh crash, tối ưu cho VPS)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

  
    # 🧠 Headless (nếu bạn đang chạy trong VPS không GUI)
    # chrome_options.add_argument("--headless=new")

    # 🚀 Khởi tạo Chrome với version_main khớp (141)
    driver = uc.Chrome(options=chrome_options, version_main=141)
    
    return {"driver": driver, "user_data_dir_abspath": user_data_dir_abspath, "temp_profile_path": temp_profile_path}


def check_proxy(browser, proxy):
    browser.get("https://api.myip.com")
    WebDriverWait(browser, 300).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    body_text = browser.find_element("tag name", "body").text
    data = json.loads(body_text)
    if data["ip"] not in proxy:
        raise Exception("Lỗi xảy ra, proxy bị lỗi")



def upload_yt( name_yt, user_agent, proxy, title, description, tags, video_path, comment = None):
    ### dùng để tạo ra 1 user
    # chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
    # user_data_dir = "C:/Path/To/Chrome/news-us"
    # subprocess.Popen([chrome_path, f'--remote-debugging-port=9223', f'--user-data-dir={user_data_dir}'])
    # time.sleep(5)
    
    driver = get_copy_profile_driver(name_yt, user_agent, proxy)
    browser = driver['driver']
    try:
        # check_proxy(browser, proxy)
        browser.get("https://studio.youtube.com/")
        
        WebDriverWait(browser, 200).until(EC.url_contains("studio.youtube.com"))
        print(f'url hiện tại: {browser.current_url}')
        if browser.current_url == 'https://studio.youtube.com/':
            element = WebDriverWait(browser, 100).until(
                EC.element_to_be_clickable((By.XPATH, '//a[contains(@class, "black-secondary")]'))
            )
            element.click()

        # await browser load end
        element = WebDriverWait(browser, 100).until(
            EC.element_to_be_clickable((By.XPATH, '//ytcp-button[@icon="yt-sys-icons:video_call"]'))
        )
        element.click()
        time.sleep(1)


        WebDriverWait(browser, 100).until(
            EC.element_to_be_clickable((By.ID, 'text-item-0'))
        )

        browser.find_element(By.ID, 'text-item-0').click()
        time.sleep(10)
        
        # upload video
        print('upload video in youtube')
        WebDriverWait(browser, 100).until(
            lambda d: len(d.find_elements(By.TAG_NAME, 'input')) > 1  # Đảm bảo có ít nhất 2 input
        )
        
        file_input = browser.find_elements(By.TAG_NAME, 'input')[1]
        file_input.send_keys(video_path)
        time.sleep(6)


        # enter title
        print('nhập title in youtube')
        WebDriverWait(browser, 100).until(
            EC.presence_of_all_elements_located((By.ID, 'textbox'))
        )
        
        title_input = browser.find_element(By.ID, 'textbox')
        
        
        check_clean_title = False
        while check_clean_title is False:
            # Xoá bằng Ctrl+A + Delete
            title_input.send_keys(Keys.CONTROL, "a")
            title_input.send_keys(Keys.DELETE)
            title_input.clear()
            time.sleep(1)
            if title_input.text.strip() == "":
                check_clean_title = True
                
        time.sleep(1)
        title_input.send_keys(title)
        time.sleep(1)

        # enter description
        print('nhập description in youtube')
        des_input = browser.find_elements(By.ID, 'textbox')[1]
        des_input.clear()
        time.sleep(1)
        # Copy vào clipboard
        pyperclip.copy(description)
        des_input.click()
        time.sleep(1)
        des_input.send_keys(Keys.CONTROL, 'v')
        time.sleep(1)

        # enter hiển thị thêm
        # Đợi cho phần tử scrollable-content xuất hiện
        scrollable_element = WebDriverWait(browser, 100).until(
            EC.presence_of_element_located((By.ID, "scrollable-content"))
        )
        # Scroll xuống cuối cùng của phần tử scrollable-content
        browser.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", scrollable_element)
        time.sleep(2)

        WebDriverWait(browser, 100).until(
            EC.presence_of_all_elements_located((By.ID, 'toggle-button'))
        )
        show_more_btn = browser.find_element(By.ID, 'toggle-button')
        show_more_btn.click()
        time.sleep(2)
        

        # enter tags
        print('nhập tags in youtube')
        WebDriverWait(browser, 100).until(
            EC.presence_of_all_elements_located((By.ID, 'text-input'))
        )
        tags_input = browser.find_element(By.ID, 'text-input')
        tags_input.send_keys(tags)
        time.sleep(2)

        # next btn
        browser.find_element(By.ID, 'next-button').click()
        time.sleep(10)
                
        # next
        WebDriverWait(browser, 100).until(
            EC.element_to_be_clickable((By.ID, 'next-button'))
        )
        browser.find_element(By.ID, 'next-button').click()
        time.sleep(2)

        check_exist_video_hd(browser)
        time.sleep(2)

        WebDriverWait(browser, 100).until(
            EC.element_to_be_clickable((By.ID, 'next-button'))
        )
        browser.find_element(By.ID, 'next-button').click()
        time.sleep(2)


        # done
        print('upload video in youtube thành công')
        WebDriverWait(browser, 100).until(
            EC.element_to_be_clickable((By.ID, 'done-button'))
        )
        browser.find_element(By.ID, 'done-button').click()

        # vào youtube để nhập bình luận
        if comment is not None:
            WebDriverWait(browser, 100).until(
                EC.presence_of_all_elements_located((By.ID, 'share-url'))
            )
            link_redirect = browser.find_element(By.ID, 'share-url')
            href = link_redirect.get_attribute('href')
            browser.get(href)
            WebDriverWait(browser, 100).until(
                EC.presence_of_all_elements_located((By.ID, 'above-the-fold'))
            )
            time.sleep(5)
            is_Find_comment = False
            while  is_Find_comment is False:
                try:
                    browser.execute_script("window.scrollBy(0, 50);")
                    time.sleep(1)
                    comment_box = browser.find_element(By.ID, 'simplebox-placeholder')
                    if(comment_box):
                        is_Find_comment = True
                    time.sleep(3)
                except:
                    time.sleep(3)

            comment_box = browser.find_element(By.ID, 'simplebox-placeholder')
            comment_box.click()
            textarea = WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#contenteditable-root[contenteditable='true']"))
            )
            pyperclip.copy(comment)
            textarea.click()
            time.sleep(1)
            textarea.send_keys(Keys.CONTROL, 'v')
            time.sleep(2)
            submit_button = WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.ID, "submit-button"))
            )
            submit_button.click()

        
        
        try:
            # Chờ tối đa 100 giây cho button xuất hiện
            button = WebDriverWait(driver, 100).until(
                EC.presence_of_element_located((By.ID, "secondary-action-button"))
            )
            # Nếu tìm thấy, click
            button.click()
            print("Đã click button!")
        except:
            # Nếu không tìm thấy sau 100 giây
            print("Button không xuất hiện trong 100 giây.")
        
        time.sleep(10)
        WebDriverWait(browser, 100).until(
                EC.presence_of_all_elements_located((By.ID, 'share-url'))
            )
        browser.quit()
        clear_copy_profile(driver['user_data_dir_abspath'], driver['temp_profile_path'])
    except Exception as e:
        message = str(e)
        browser.quit()
        clear_copy_profile(driver['user_data_dir_abspath'], driver['temp_profile_path'])
        if "lỗi upload youtube" in message:
            raise Exception("lỗi upload youtube")
    

def clear_all_chrome_background():
    chrome_procs = []
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                chrome_procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied): 
            print('loii')   
            
    for proc in chrome_procs:
        try:
            proc.kill()
        except Exception as e:
            print(f"Không thể kill {proc.pid}: {e}")


def wait_check_clear_all_chrome_background():
    clear_all_chrome_background()         
    """⏳ Đợi đến khi Chrome tắt hoàn toàn (tối đa timeout giây)"""
    start = time.time()
    while time.time() - start < 500:
        chrome_running = False
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == 'chrome.exe':
                    chrome_running = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if not chrome_running:
            print("✅ Chrome đã tắt hoàn toàn.")
            return True
        
        time.sleep(0.5)

    print("⚠️ Chrome vẫn chưa tắt hết, bỏ qua kiểm tra.")
    return False
    
def clear_copy_profile(user_data_dir_abspath, temp_profile_path):
    is_clear_all_chrome_background = wait_check_clear_all_chrome_background()
    if is_clear_all_chrome_background is False:
        raise Exception("Lỗi xảy ra, không đóng được chrome nền")
    files_to_copy = [
        "Local State",
        os.path.join("Default", "Cookies"),
        os.path.join("Default", "Network", 'Cookies'),
        os.path.join("Default", "Login Data"),
        os.path.join("Default", "Web Data")
    ]
        
    for file in files_to_copy:
        src = os.path.join(temp_profile_path, file)
        dst = os.path.join(user_data_dir_abspath, file)

        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            print(f"✅ Cập nhật lại: {file}")
        else:
            print(f"⚠️ Không tìm thấy file: {file}")

    # 🧹 Xóa profile tạm
    shutil.rmtree(temp_profile_path, ignore_errors=True)
    print("🧹 Đã xóa thư mục tạm.")

def open_chrome_to_edit_detect(name_chrome_yt, user_agent=None, proxy=None):
    driver = get_copy_profile_driver(name_chrome_yt, user_agent, proxy)
    
    # 🧩 Kiểm tra proxy hoặc tác vụ bạn muốn
    check_proxy(driver['driver'], proxy)
    input("Nhấn Enter để đóng Chrome...")
    driver['driver'].quit()
    
    clear_copy_profile(driver['user_data_dir_abspath'], driver['temp_profile_path'])
   
   
def check_identity_verification(name_chrome_yt, user_agent, proxy):
    driver = get_copy_profile_driver(name_chrome_yt, user_agent, proxy)
    
    video_path = os.path.abspath(f"./public/more/kokoro.mp4"),
    thumb_path = os.path.abspath(f"./public/decorates/decorate1/bg.png"),
    
    try:
        check_proxy(driver['driver'], proxy)
        driver['driver'].get("https://studio.youtube.com/")
        
        WebDriverWait(driver['driver'], 200).until(EC.url_contains("studio.youtube.com"))
        if driver['driver'].current_url == 'https://studio.youtube.com/':
            element = WebDriverWait(driver['driver'], 100).until(
                EC.element_to_be_clickable((By.XPATH, '//a[contains(@class, "black-secondary")]'))
            )
            element.click()
        
        # await driver['driver'] load end
        element = WebDriverWait(driver['driver'], 100).until(
            EC.element_to_be_clickable((By.XPATH, '//ytcp-button[@icon="yt-sys-icons:video_call"]'))
        )
        element.click()
        time.sleep(1)

        WebDriverWait(driver['driver'], 100).until(
            EC.element_to_be_clickable((By.ID, 'text-item-0'))
        )
            
        driver['driver'].find_element(By.ID, 'text-item-0').click()
        time.sleep(10)

        # upload video
        print('upload video in youtube')
        # chờ tối đa 100 giây cho ít nhất 2 input xuất hiện
        WebDriverWait(driver['driver'], 100).until(
            lambda d: d.find_elements(By.TAG_NAME, 'input') if len(d.find_elements(By.TAG_NAME, 'input')) > 1 else False
        )
        file_input = driver['driver'].find_elements(By.TAG_NAME, 'input')[1]
        file_input.send_keys(video_path)
        time.sleep(3)


        # upload thumbnail
        print('upload thumbnail in youtube')
        WebDriverWait(driver['driver'], 10).until(
            EC.visibility_of_element_located((By.ID, 'file-loader'))
        )
        thumbnail_input = driver['driver'].find_element(By.ID, 'file-loader')
        thumbnail_input.send_keys(thumb_path)
        time.sleep(3)
    except:
        print('error')
    
    input('nhấn bất kì để đóng chrome:')
    driver['driver'].quit()
    
    clear_copy_profile(driver['user_data_dir_abspath'], driver['temp_profile_path'])

def open_chrome_to_edit(name_chrome_yt, driver_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"):
    user_data_dir = os.path.abspath(f"./youtubes/{name_chrome_yt}")
    process = subprocess.Popen([driver_path, f'--remote-debugging-port=9223', f'--user-data-dir={user_data_dir}'])
   
    input('nhấn bất kì để đóng chrome:')
    process.terminate()  # gửi tín hiệu terminate
    try:
        process.wait(timeout=30)  # đợi chrome tắt
    except subprocess.TimeoutExpired:
        process.kill()  # nếu không tắt thì kill hẳn là sao không hiểu
        
    clear_all_chrome_background()
