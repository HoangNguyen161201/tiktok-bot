from untils import overlay_image_on_image, overlay_video_and_image, concat_videos, zoom_video, get_3_pie_video, crop_video, generate_content,get_content_cv, download_tiktok_video_n_comment
from db import get_all_links, get_product_random
import time
import shutil
import os
from untils import generate_content
from untils import upload_yt
from untils import open_chrome_to_edit_detect, check_identity_verification, open_chrome_to_edit
from db import delete_link, update_next_time_youtube, get_all_models, insert_model, delete_model, update_time, insert_time, get_times, check_not_exist_to_create_ip, find_one_ip, add_gemini_key_to_ip, remove_gemini_key_youtube_to_ip, update_driver_path_to_ip, add_youtube_to_ip, remove_youtube_to_ip
import random
import time
import shutil
from datetime import datetime, timedelta
from data import fake_user, proxies


def main():
    gemini_key_index = 0
    gemini_model_index = 0
    while True:
        # lấy data
        youtube = None
        print('lấy thời gian')
        times = get_times()
        print('lấy thông tin của địa chỉ ip')
        data_by_ip = find_one_ip()
            
        try:
            start_time = time.time()
            links = get_all_links()
            product = get_product_random()

            if links is None or links.__len__() == 0:
                raise Exception("Lỗi xảy ra, không tồn tại link hoặc đã hết tin tức")
            
            short_url= links[0]
            folder_video_path = f'./video'
            data_path = f'{folder_video_path}/data.csv'
            comment_path= f'{folder_video_path}/comments.csv'
            out_path= f'{folder_video_path}/result.mp4'
            
            if os.path.exists(folder_video_path):
                shutil.rmtree(folder_video_path)
            print('lấy kênh youtube hiện tại để đăng')
            youtubes = data_by_ip['youtubes']
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
            
            if youtube is None:
                 raise Exception("Không có youtube nào khả dụng (tất cả còn trong thời gian chờ).")
                
            print('lấy model gemini')
            models = get_all_models()
           
        
            #kiểm tra cuối ngày hay chưa
            print('kiểm tra đã cuối ngày chưa')
            now = datetime.now()
            end_of_day = datetime.combine(now.date(), datetime.max.time())
            start_of_period = end_of_day - timedelta(minutes=times[0]['time4'])
            
            if now >= start_of_period:
                raise Exception("Lỗi xảy ra, tới thời gian nghỉ")
            
            #-------------------------
            download_tiktok_video_n_comment(
                short_url,
                folder_video_path,
                data_path,
                comment_path,
                out_path
            )

            data = get_content_cv(data_path, comment_path)

            props = f''''
                Tôi đang có các thông tin như sau:
                - tiêu đề: {data['title']}
                - người đăng: {data['author_name']}
                - comments: {data['comments']}
                Trên là những thông tin của video tiktok, tôi muốn tạo ra tiêu đề mới khác với tiêu đề cũ, hấp dẫn hơn, thu hút hơn để đăng youtube short.
                Hãy trả ra theo yêu cầu dưới đây:
                1. tiêu đề dưới 100 ký tự
                2. tiêu đề đúng định dạng như sau `[tên người đăng] title 3 hastags(nếu trong tiêu đề cũ tôi cung cấp có hastag thì lấy)`
                3. trả ra tiêu đề luôn, không giải thích gì thêm 
            '''

            props2 = f''''
                Tôi đang có các thông tin như sau:
                - tiêu đề: {data['title']}
                - người đăng: {data['author_name']}
                - comments: {data['comments']}
                Trên là những thông tin của video tiktok, tôi muốn tạo ra mô tả hấp dẫn hơn, thu hút hơn để gắn vào mô tả video youtube.
                Hãy trả ra theo yêu cầu dưới đây:
                1. mô tả trên 100 ký tự, dưới 250 ký tự
                3. trả ra mô tả luôn, không giải thích gì thêm 
            '''
            props2 = f''''
                Tôi đang có các thông tin như sau:
                - tiêu đề: {data['title']}
                - người đăng: {data['author_name']}
                - comments: {data['comments']}
                Trên là những thông tin của video tiktok, tôi muốn tạo ra mô tả hấp dẫn hơn, thu hút hơn để gắn vào mô tả video youtube.
                Hãy trả ra theo yêu cầu dưới đây:
                1. mô tả trên 100 ký tự, dưới 250 ký tự
                3. trả ra mô tả luôn, không giải thích gì thêm 
            '''

            props3 = f''''
                Tôi đang có các thông tin như sau:
                - tiêu đề: {data['title']}
                - người đăng: {data['author_name']}
                - comments: {data['comments']}
                Trên là những thông tin của video tiktok, tôi muốn tạo tags hấp dẫn, chuẩn seo, dễ tìm kiếm, dễ đề xuất cho video youtube.
                Hãy trả ra theo yêu cầu dưới đây:
                1. tags sẽ trả ra như sau: tag1,tag2,tag3,tag4,...tagn+1
                2. trả ra tags luôn, không ghi gì thêm, không chứa kí tự đặt biệt, không giải thích, trả đúng cấu trúc.
                3. tổng độ ký tự cả các tags cộng lại không quá 350 ký tự
            '''

            title = generate_content(props, model= 'gemini-2.5-flash-lite', api_key= data_by_ip['geminiKeys'][0])
            description = generate_content(props2, model= 'gemini-2.5-flash-lite', api_key= data_by_ip['geminiKeys'][0])
            tags = generate_content(props3, model= 'gemini-2.5-flash-lite', api_key= data_by_ip['geminiKeys'][0])


            input_file = "./video/result.mp4"
            output_file = "./video/result2.mp4"
            output_files = ["./video/result3.mp4", "./video/result4.mp4", "./video/result5.mp4"]
            output_files2 = ["./video/result33.mp4", "./video/result44.mp4", "./video/result55.mp4"]
            output_concat_file = "./video/concat.mp4"
            crop_video(input_file, output_file)
            get_3_pie_video(output_file, output_files)
            for index, item in enumerate(output_files):
                zoom_video(item, output_files2[index])
            concat_videos(output_files2, output_concat_file)

            overlay_image_on_image(
                './public/bg-pr.png',
                product['imgUrl'],
                './video/pr.png',
                (7, 6),
                (328, 443),
                product['title'],
                product['oldPrice'],
                product['newPrice'],
            )

            overlay_video_and_image(output_concat_file, './public/bg.png', './video/pr.png' , './video/final.mp4')
            end_time = time.time()
            print(f"Thời gian chạy: {end_time - start_time:.2f} giây")
  
           
            upload_yt(
                youtube['name'],
                youtube['user_agent'],
                youtube['proxy'],
                title,
                description,
                tags,
                os.path.abspath(f"./video/final.mp4"),
            )
            print('thông tin kênh youtube đã đăng:')
            print(youtube)
            delete_link(links[0])
            if os.path.exists(folder_video_path):
                shutil.rmtree(folder_video_path)
            update_next_time_youtube(youtube['name'])
            time.sleep(60)
            print('Tiếp tục...')
        except Exception as e:
            message = str(e)
            
            if "Lỗi xảy ra, không tồn tại link hoặc đã hết tin tức" in message:
                print('hết link, qua kênh khác')
                if youtube:
                    update_next_time_youtube(youtube['name'], (datetime.now() + timedelta(minutes= -(times[0]['time2'] - 10))).isoformat())
                time.sleep(60)
            elif 'lỗi upload youtube' in message:
                print('lỗi upload youtube') 
            elif "Lỗi xảy ra, không có thông tin của content" in message:
                print(f"Lỗi xảy ra, không có thông tin của content")
            elif "Lỗi xảy ra, video không đủ độ dài tối thiểu" in message:
                print(f"Lỗi xảy ra, video không đủ độ dài tối thiểu")
            elif "Lỗi xảy ra, tới thời gian nghỉ" in message:
                print(f"Đã cuối ngày, vui lòng đợi tới ngày mới để đăng tiếp")
                current_day = datetime.now().date()
                while True:
                    now = datetime.now()

                    # Kiểm tra nếu sang ngày mới
                    if now.date() != current_day:
                        print("Đã sang ngày mới:", now.date())
                        break

                    print("Đợi qua ngày... ", now.strftime("%H:%M:%S"))
                    time.sleep(5)
            elif "Lỗi xảy ra, proxy bị lỗi" in message:
                raise Exception("Lỗi xảy ra, proxy bị lỗi")
            elif "Lỗi xảy ra, không đóng được chrome nền" in message:
                raise Exception("Lỗi xảy ra, không đóng được chrome nền")
            elif "Không có youtube nào khả dụng (tất cả còn trong thời gian chờ)." in message:
                print("Không có youtube nào khả dụng (tất cả còn trong thời gian chờ).")
                time.sleep(5 * 60)
            else:
                print(f"[LỖI KHÁC] {message}")
                gemini_model_index += 1
                if gemini_model_index > models.__len__() - 1:
                    gemini_model_index = 0
                    gemini_key_index += 1
                    if gemini_key_index > data_by_ip['geminiKeys'].__len__() - 1:
                        gemini_key_index = 0
                print('Cập nhật model và key của gemini')
                print(f'Model của bạn là: {models[gemini_model_index]}')
                print(f'key của bạn là: {data_by_ip["geminiKeys"][gemini_key_index]}')

                time.sleep(60)


if __name__ == "__main__":
    is_exit = False
    while is_exit is False:
        check_not_exist_to_create_ip()
        print('|-----------------------------------------------|')
        print('|-------       tool youtube linux        -------|')
        print('|-0. Thoát chương trình                  -------|')
        print('|-1. Chỉnh sửa danh sách chrome youtube  -------|')
        print('|-2. Chỉnh sửa danh sách gemini          -------|')
        print('|-3. Chỉnh sửa chrome driver             -------|')
        print('|-4. chỉnh thời gian chạy (chỉnh toàn bộ vps) --|')
        print('|-5. Chạy youtube                        -------|')

        func = int(input("Nhập chọn chức năng: "))

        if func == 1:
            while func == 1:
                data = find_one_ip()
                print('|-----------------------------------------------|')
                print('|---   Chỉnh sửa danh sách chrome youtube   ----|')
                print('|- DANH SÁCH YOUTUBE:                    -------|')
                if (data.get('youtubes') is not None and data['youtubes'].__len__() > 0):
                    print(data['youtubes'])
                else:
                    print('Trống vui lòng thêm youtube mới')
                print('|-0. Quay lại                            -------|')
                print('|-1. Thêm youtube mới (nhập 1-name)      -------|')
                print('|-2. Xóa youtube (nhập 2-name)           -------|')
                print('|-3. Mở để chỉnh sửa (nhập 3-name)       -------|')
                print('|-4. Mở để chỉnh sửa không proxy (nhập 4-name) -|')
                print('|-5. Check xác minh danh tính (nhập 5-name)  ---|')
                print('|- Lưu ý: name chrome ghi liền mạch không cách -|')
                func1 = input("Nhập chọn chức năng: ")

                if (' ' in func1):
                    print('lỗi cú pháp, không được chứa dấu cách')
                elif func1 == 0 or func1 == '0':
                    func = 'exit'
                elif func1.startswith("1-"):
                    text = func1[2:]
                    if (data.get('youtubes') is not None and any(item.get('name') == text for item in data.get("youtubes", []))):
                        print('đã tồn tại chrome youtube này rồi')
                    else:
                        index_ad = None
                        index_decorate = None
                        index_func = None
                        user_agent = None
                        proxy = None
                        
                        while user_agent is None:
                            random_item = random.choice(fake_user)
                            if (data.get('youtubes') is not None and any(item.get('user_agent') == random_item for item in data.get("youtubes", []))):
                                print('đã tồn tại user agent, random lại')
                            else:
                                user_agent = random_item
                        
                        while proxy is None:
                            random_item = random.choice(proxies)
                            if (data.get('youtubes') is not None and any(item.get('proxy') == random_item for item in data.get("youtubes", []))):
                                print('đã tồn tại proxy, random lại')
                            else:
                                proxy = random_item

                        add_youtube_to_ip(
                            text, user_agent, proxy)
                        open_chrome_to_edit(text, data.get('driverPath'))
                elif func1.startswith("2-"):
                    text = func1[2:]
                    if (data.get('youtubes') is not None and any(item.get('name') == text for item in data.get("youtubes", []))):
                        remove_youtube_to_ip(text)
                        try:
                            shutil.rmtree(f"./youtubes/{text}")
                        except:
                            print('')
                    else:
                        print('Không thể xóa vì chưa tồn tại chrome youtube này')
                elif func1.startswith("3-"):
                    text = func1[2:]
                    if (data.get('youtubes') is not None and any(item.get('name') == text for item in data.get("youtubes", []))):
                        youtubes = data.get("youtubes", [])
                        result = next((item for item in youtubes if item["name"].lower() == text.lower()), None)
                        open_chrome_to_edit_detect(text, result['user_agent'], result['proxy'])
                    else:
                        print('Chưa tồn tại trình duyệt này')
                elif func1.startswith("4-"):
                    text = func1[2:]
                    if (data.get('youtubes') is not None and any(item.get('name') == text for item in data.get("youtubes", []))):
                        open_chrome_to_edit(text, data.get('driverPath'))
                    else:
                        print('Chưa tồn tại trình duyệt này')
                elif func1.startswith("5-"):
                    text = func1[2:]
                    if (data.get('youtubes') is not None and any(item.get('name') == text for item in data.get("youtubes", []))):
                        youtubes = data.get("youtubes", [])
                        result = next((item for item in youtubes if item["name"].lower() == text.lower()), None)
                        check_identity_verification(text,  result['user_agent'], result['proxy'])
                    else:
                        print('Chưa tồn tại trình duyệt này')

        elif func == 2:
            while func == 2:
                data = find_one_ip()
                models = get_all_models()
                print('|-----------------------------------------------|')
                print('|---    Chỉnh sửa danh sách gemini keys     ----|')
                print('|- DANH SÁCH GEMINI KEYS:                -------|')
                if (data.get('geminiKeys') is not None and data['geminiKeys'].__len__() > 0):
                    print(data['geminiKeys'])
                else:
                    print('Trống vui lòng thêm gemini key mới')
                print('|- DANH SÁCH GEMINI MODEL:               -------|')
                if (models is not None and models.__len__() > 0):
                    print(models)
                else:
                    print('Trống vui lòng thêm model mới')
                print('|-0. Quay lại                            -------|')
                print('|-1. Thêm key mới (nhập 1-key)           -------|')
                print('|-2. Xóa key (nhập 2-key)                -------|')
                print('|-3. Thêm model (nhập 3-model, toàn bộ vps)   --|')
                print('|-4. xóa model (nhập 4-model, toàn bộ vps)    --|')
                print('|-5. xem các models trong gemini              --|')
                print('|-6. test chạy key (nhập 6-key)               --|')
                print('|-7. test chạy (nhập 7-model)                 --|')
                print('|- Lưu ý: key ghi liền mạch không cách   -------|')
                func2 = input("Nhập chọn chức năng: ")

                if func2 == 0 or func2 == '0':
                    func = 'exit'
                elif func2.startswith("1-"):
                    text = func2[2:]
                    if (data.get('geminiKeys') is not None and text in data.get("geminiKeys", [])):
                        print('đã tồn tại key này rồi')
                    else:
                        add_gemini_key_to_ip(text)
                elif func2.startswith("2-"):
                    text = func2[2:]
                    if (data.get('geminiKeys') is not None and text in data.get("geminiKeys", [])):
                        remove_gemini_key_youtube_to_ip(text)
                    else:
                        print('Không thể xóa vì chưa tồn tại key này')
                elif func2.startswith("3-"):
                    text = func2[2:]
                    if (models is not None and text in models):
                        print('đã tồn tại model này rồi')
                    else:
                        insert_model(text)

                elif func2.startswith("4-"):
                    text = func2[2:]
                    if (models is not None and text in models):
                        delete_model(text)
                    else:
                        print('Không thể xóa vì chưa tồn tại model này')
                elif func2.startswith("5"):
                    if (data.get('geminiKeys') is not None and data['geminiKeys'].__len__() > 0):
                        import google.generativeai as genai
                        genai.configure(api_key=data['geminiKeys'][0])
                        models = genai.list_models()
                        for m in models:
                            if 'generateContent' in m.supported_generation_methods:
                                print(m.name, m.description,
                                      m.supported_generation_methods)
                    else:
                        print('chưa có key để search model')

                elif func2.startswith("6-"):
                    text = func2[2:]
                    data = generate_content(
                        "hãy tạo ra 1 câu truyện cổ tích", api_key=text)
                    print(data)
                elif func2.startswith("7-"):
                    if (data.get('geminiKeys') is not None and data['geminiKeys'].__len__() > 0):
                        text = func2[2:]
                        data = generate_content(
                            "hãy tạo ra 1 câu truyện cổ tích", model=text, api_key=data['geminiKeys'][0])
                        print(data)
                    else:
                        print('chưa có key để test model')
        elif func == 3:
            while func == 3:
                data = find_one_ip()
                print('|-----------------------------------------------|')
                print('|---         Chỉnh sửa chrome driver        ----|')
                print('|- DRIVER CỦA BẠN LÀ:                    -------|')
                print(data['driverPath'])
                print('|-1. Thay driver (nhập 1-driver path     -------|')
                print('|-0. Quay lại                            -------|')

                func3 = input("Nhập chọn chức năng: ")
                if func3 == 0 or func3 == '0':
                    func = 'exit'
                elif func3.startswith("1-"):
                    text = func3[2:]
                    update_driver_path_to_ip(text)

        elif func == 4:
            while func == 4:
                data = get_times()
                print('|-----------------------------------------------|')
                print('|---         Chỉnh sửa thời gian            ----|')
                print('|- THÔNG TIN CHI TIẾT:                   -------|')
                if (data.__len__() == 0):
                    print('Chưa có thông tin thời gian, vui lòng cập nhật')
                else:
                    print(f'Thời gian đợi khi hết link: {data[0]["time1"]} phút')
                    print(f'Thời gian đợi khi upload thành công nếu chỉ 1 kênh: {data[0]["time2"]} phút')
                    print(f'Thời gian đợi khi upload thành công nếu có nhiều kênh: { data[0]["time3"]} phút')
                    print(f'Thời gian nghỉ cuối ngày: {data[0]["time4"]} phút')

                print('|-1. thời gian đợi khi hết link, thời gian chờ -|')
                print('| khi úp yt thành công nếu chỉ 1 kênh, thời    -|')
                print('| gian khi úp yt thành công nếu có nhiều kênh, -|')
                print('| thời gian nghỉ cuối ngày                   , -|')
                print('| (nhập 1-time1-time2-time3-time4) (phút)      -|')
                print('|-0. Quay lại                            -------|')

                func3 = input("Nhập chọn chức năng: ")
                if func3 == 0 or func3 == '0':
                    func = 'exit'
                elif func3.startswith("1-"):
                    arr = func3.split('-')
                    if (arr.__len__() != 5):
                        print('Không đúng cú pháp')
                    elif not arr[1].isdigit() or not arr[2].isdigit() or not arr[3].isdigit() or not arr[4].isdigit():
                        print('Không đúng cú pháp')
                    elif int(arr[1]) <= 0 or int(arr[2]) <= 0 or int(arr[3]) <= 0 or int(arr[4]) <= 0:
                        print('Thời gian không được nhỏ hơn hoặc bằng 0')
                    else:
                        if (data.__len__() == 0):
                            insert_time(int(arr[1]), int(arr[2]), int(arr[3]), int(arr[4]))
                        else:
                            update_time(data[0]['_id'], int(
                                arr[1]), int(arr[2]), int(arr[3]), int(arr[4]))

        elif func == 5:
            data = find_one_ip()
            times = get_times()
            if (data.get('geminiKeys') is None or data['geminiKeys'].__len__() == 0):
                print('bạn chưa thể chạy vì chưa thêm gemini key')
            elif (data.get('youtubes') is None or data['youtubes'].__len__() == 0):
                print('bạn chưa thể chạy vì chưa thêm youtube chrome')
            elif (times.__len__() == 0):
                print('bạn chưa thể chạy vì chưa chỉnh thời gian')
            else:
                main()
        elif func == 0:
            is_exit = True
        else:
            print('Thoát thành công')