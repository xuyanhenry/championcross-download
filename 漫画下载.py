import requests
import re
import os
from PIL import Image
# from time import sleep
from io import BytesIO
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

session = requests.Session()
# 定义请求头
headers = {
    "authority": "viewer.championcross.jp",
    "method": "GET",
    "scheme": "https",
    "accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "origin": "https://championcross.jp",
    "referer": "https://championcross.jp/episodes/f2754723940ae/",
    "sec-ch-ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "image",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
}
def find_page_count_by_id(data, target_id):
    for item in data.get("result", []):
        if item.get("id") == target_id:
            return item.get("page_count")
    return None
def find_name_by_id(data, target_id):
    for item in data.get("result", []):
        if item.get("id") == target_id:
            return item.get("name")
    return None
def unscramble_image(input_image, scramble):
    # 打开原始图片
    original_image = Image.open(BytesIO(input_image))
    width, height = original_image.size

    # 计算每个块的宽度和高度（假设切割为 4x4 块）
    rows, cols = 4, 4
    block_width = width // cols
    block_height = height // rows

    # 初始化空的图像来存放重组结果
    reconstructed_image = Image.new("RGB", (width, height))

    # 遍历 scramble 数组，按照 scramble 的顺序提取并重新排列块
    for index, scrambled_index in enumerate(scramble):
        # 计算 scramble 对应的原图块位置
        original_col = scrambled_index // cols
        original_row = scrambled_index % cols
        block_x1 = original_col * block_width
        block_y1 = original_row * block_height
        block_x2 = block_x1 + block_width
        block_y2 = block_y1 + block_height

        # 提取原始图片中的块
        block = original_image.crop((block_x1, block_y1, block_x2, block_y2))

        # 计算目标位置
        new_col = index // cols
        new_row = index % cols
        target_x1 = new_col * block_width
        target_y1 = new_row * block_height

        # 将块放到重组图像中
        reconstructed_image.paste(block, (target_x1, target_y1))

    # 保存重新拼接后的图像
    return reconstructed_image
    # reconstructed_image.save(output_image_path)
    # print(f"图像已成功重组并保存为 {output_image_path}")

def download_and_process_image(item):
    """下载并重组单张图片"""
    url = item["url"]
    scramble = item["scramble"]
    sort = item["sort"]
    # print("url:",url)
    print("sort:",sort)
    if isinstance(scramble, str):
        scramble = eval(scramble)  # 将字符串形式的列表转换为 Python 列表
    if not isinstance(scramble, list):
        print(f"Invalid scramble format for {url}: {scramble}")
        return None
    try:
        # 下载图片
        response = session.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch image from {url}. Status code: {response.status_code}")
            return None

        # 重组图片
        picture = unscramble_image(response.content, scramble)

        # 将图像存入内存
        image_buffer = BytesIO()
        picture.save(image_buffer, format="JPEG")  # 保存为 JPEG 格式
        image_buffer.seek(0)  # 重置缓冲区指针
        return f"image_{sort + 1}.jpg", image_buffer
    except Exception as e:
        print(f"Error processing image from {url}: {e}")
        return None
    







# 多线程下载和处理
def process_all_images_multithreaded(items, max_workers=10):
    """多线程下载和处理所有图片"""
    # print(headers)
    images_in_memory = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(download_and_process_image, item): item for item in items}
        for future in as_completed(future_to_item):
            result = future.result()
            if result:  # 过滤 None
                images_in_memory.append(result)
    return images_in_memory



def main():
    global headers
    if getattr(sys, 'frozen', False):
        # 如果程序被打包成了 exe
        current_dir = os.path.dirname(sys.executable)
    else:
        # 如果程序没有被打包
        current_dir = os.path.dirname(os.path.abspath(__file__))

    output_folder = current_dir
    os.makedirs(output_folder, exist_ok=True)
    # 定义 URL
    url=input("输入url:")
    # 发送请求
    headers["referer"] = url
    response = session.get(url, headers=headers)

    if response.status_code == 200:
        # 打印响应内容
        content = response.text

        # 使用正则表达式提取 comici-viewer-id 的值
        match = re.search(r'comici-viewer-id="([\w-]+)"', content)
        if match:
            comici_viewer_id = match.group(1)
            print("comici-viewer-id:", comici_viewer_id)
        else:
            print("未找到 comici-viewer-id")
            print(response.text)
        
        listurl=f"https://championcross.jp/book/episodeInfo?comici-viewer-id={comici_viewer_id}&isPreview=false"
        response = session.get(listurl, headers=headers)
        if response.status_code == 200:
            # 打印响应内容
            content = response.json()
            # page_count = find_page_count_by_id(content,comici_viewer_id)
            # name=find_name_by_id(content,comici_viewer_id)
            # print("name:",name)
            # print("page_count:",page_count)
            # results = list({item["id"]: item for item in (content.get("result", [])[:5] + content.get("result", [])[-5:])}.values())
            ## results = content.get("result", [])
            print("\n请选择下载范围:")
            print("1. 前后各 5 章")
            print("2. 全本")
            try:
                range_choice = int(input("Enter your choice (1/2): "))
                if range_choice == 1:
                    results = list({item["id"]: item for item in (content.get("result", [])[:5] + content.get("result", [])[-5:])}.values())
                elif range_choice == 2:
                    results = content.get("result", [])
                else:
                    print("Invalid choice. Please enter a valid number.")
                    return None
            except ValueError:
                print("Invalid input. Please enter a number.")
                return None

            
            if not results:
                print("No valid results found in content.")
                return None
            

            valid_results = []
            for item in results:
                name = item.get("name", "Unknown Name")
                page_count = item.get("page_count", "Unknown Page Count")
                comici_viewer_id = item.get("id", "Unknown ID")
                if not comici_viewer_id:
                    continue

                # 请求数据验证
                picturelisturl = f"https://championcross.jp/book/contentsInfo?user-id=0&comici-viewer-id={comici_viewer_id}&page-from=0&page-to={page_count}"
                response = session.get(picturelisturl, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("message") == "NoError":
                        result = data.get("result", [])
                        formatted_results = [{"url": item["imageUrl"], "scramble": eval(item["scramble"]), "sort": int(item["sort"])} for item in result]
                        valid_results.append({
                            "name": name,
                            "page_count": page_count,
                            "id": comici_viewer_id,
                            "formatted_results":formatted_results
                        })
            if not valid_results:
                print("No valid results found after checking conditions.")
                return None

            while True:
                # 让用户选择
                print("\n可下载章节:")
                for i, item in enumerate(valid_results):
                    print(f"{i + 1}. {item['name']} - {item['page_count']} pages")


                try:
                    choice = int(input("Enter the number of your choice(exit): "))
                    if choice == "exit":
                        exit()
                    if 1 <= choice <= len(valid_results):
                        selected = valid_results[choice - 1]
                        comici_viewer_id = selected["id"]
                        name = selected["name"]
                        page_count = selected["page_count"]
                        formatted_results=selected["formatted_results"]
                        zip_file_path = os.path.join(output_folder, f"{name}.zip")

                        print(f"Selected: {selected['name']} - ID: {comici_viewer_id}")
                        # return comici_viewer_id, name, page_count
                    else:
                        print("Invalid choice. Please enter a valid number.")
                        return None
                except ValueError:
                    print("Invalid input. Please enter a number.")
                    return None



            # # 存储并打印最后三个结果
            # options = []
            # print("\nAvailable Options:")
            # for i, item in enumerate(results):
            #     name = item.get("name", "Unknown Name")
            #     page_count = item.get("page_count", "Unknown Page Count")
            #     id_ = item.get("id", "Unknown ID")
            #     options.append({"name": name, "page_count": page_count, "id": id_})
            #     print(f"{i + 1}. {name} - {page_count} pages")

            # # 用户选择输入
            # try:
            #     choice = int(input("Enter the number of your choice (1/2/3): "))
            #     if 1 <= choice <= len(options):
            #         selected = options[choice - 1]
            #         comici_viewer_id = selected["id"]
            #         name = selected["name"]
            #         page_count = selected["page_count"]

            #         print(f"Selected: {selected['name']} - ID: {comici_viewer_id}")
            #         # return comici_viewer_id, selected["name"], selected["page_count"]
            #     else:
            #         print("Invalid choice. Please enter a valid number.")
            #         return None
            # except ValueError:
            #     print("Invalid input. Please enter a number.")
            #     return None






            # zip_file_path = os.path.join(output_folder, f"{name}.zip")
            

            # picturelisturl=f"https://championcross.jp/book/contentsInfo?user-id=0&comici-viewer-id={comici_viewer_id}&page-from=0&page-to={page_count}"
            # response = session.get(picturelisturl, headers=headers)
            # if response.status_code == 200:
            #     # 打印响应内容
            #     data = response.json()
            #     #print(content)
            #     result = data.get("result", [])
            #     formatted_results = [{"url": item["imageUrl"], "scramble": eval(item["scramble"]), "sort": int(item["sort"])} for item in result]

                # 打印提取后的格式化数据
                # print("Formatted Results:")
                # for item in formatted_results:
                #     print(item)


                images_in_memory = process_all_images_multithreaded(formatted_results, max_workers=5)

                # 创建 ZIP 文件并将图像写入
                with zipfile.ZipFile(zip_file_path, "w") as zipf:
                    for image_name, image_buffer in images_in_memory:
                        zipf.writestr(image_name, image_buffer.read())  # 写入 ZIP

                print(f"All images are saved to {zip_file_path}")
                    

    else:
        print(f"请求失败，状态码: {response.status_code}")




    #    https://championcross.jp/book/episodeInfo?comici-viewer-id=eb2c4f2de2638214d423b9dde8db4965&isPreview=false      一本漫画的全部书目列表   有每一章的id（既是comici-viewer-id） 和每章页数page_count

    #    https://championcross.jp/episodes/8c048e7f6b952/    漫画中一章的地址url要加到referer中，其中包含 comici-viewer-id  然后可调用上面的URL

    #    https://championcross.jp/book/contentsInfo?user-id=0&comici-viewer-id=137207806d360ad2b642b5a1ff437fc9&page-from=0&page-to=10    可以提取一章中每一页的图片地址和scramble
if __name__ == '__main__':
    main()