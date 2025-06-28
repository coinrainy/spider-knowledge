import os
import time
import random
import re
import json
import logging
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from proxy_pool import ProxyPool

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("biquge_proxy.log"),
        logging.StreamHandler()
    ]
)

class BiqugeProxySpider:
    """使用代理池的笔趣阁爬虫"""
    
    def __init__(self, download_dir="novels", max_workers=3, timeout=10):
        """初始化爬虫
        
        Args:
            download_dir: 小说下载目录
            max_workers: 最大线程数
            timeout: 请求超时时间（秒）
        """
        self.base_url = "https://www.biquge.com"
        self.search_url = f"{self.base_url}/search.php?q="
        self.download_dir = download_dir
        self.max_workers = max_workers
        self.timeout = timeout
        
        # 初始化代理池
        self.proxy_pool = ProxyPool(min_proxies=20, check_interval=300)
        
        # 用户代理列表
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
        ]
        
        # 确保下载目录存在
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        # 初始化线程池
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 记录已下载的章节，用于断点续传
        self.downloaded_chapters = set()
        
        # 请求会话，用于保持cookie
        self.session = requests.Session()
        
        logging.info("爬虫初始化完成")
    
    def __del__(self):
        """析构函数，确保资源释放"""
        try:
            if hasattr(self, 'executor'):
                self.executor.shutdown()
        except Exception as e:
            logging.error(f"关闭资源时出错: {e}")
    
    def random_sleep(self, min_seconds=1, max_seconds=3):
        """随机等待一段时间，避免请求过于频繁"""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def get_headers(self):
        """获取随机请求头"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "Referer": self.base_url
        }
    
    def get_page(self, url, retry=3):
        """获取页面内容，使用代理池
        
        Args:
            url: 页面URL
            retry: 重试次数
            
        Returns:
            str: 页面HTML内容，失败返回空字符串
        """
        for attempt in range(retry):
            # 获取代理
            proxy = self.proxy_pool.get_proxy()
            proxies = {"http": proxy, "https": proxy} if proxy else None
            
            try:
                headers = self.get_headers()
                response = self.session.get(
                    url,
                    headers=headers,
                    proxies=proxies,
                    timeout=self.timeout,
                    verify=False  # 不验证SSL证书
                )
                response.raise_for_status()
                response.encoding = "utf-8"
                
                # 报告代理使用成功
                if proxy:
                    self.proxy_pool.report_proxy(proxy, True)
                
                return response.text
            except Exception as e:
                # 报告代理使用失败
                if proxy:
                    self.proxy_pool.report_proxy(proxy, False)
                
                logging.warning(f"获取页面失败 ({attempt+1}/{retry}): {url}, 错误: {e}")
                self.random_sleep(2, 5)  # 失败后等待更长时间
        
        logging.error(f"获取页面失败，已达到最大重试次数: {url}")
        return ""
    
    def search_novel(self, keyword):
        """搜索小说
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            list: 搜索结果列表，每个元素为字典，包含小说信息
        """
        try:
            # 对关键词进行URL编码
            encoded_keyword = quote(keyword)
            search_url = f"{self.search_url}{encoded_keyword}"
            
            logging.info(f"搜索小说: {keyword}, URL: {search_url}")
            
            # 获取搜索页面
            html = self.get_page(search_url)
            if not html:
                return []
            
            # 解析搜索结果
            soup = BeautifulSoup(html, "html.parser")
            result_items = soup.select(".result-item")
            
            results = []
            for item in result_items:
                try:
                    title_element = item.select_one(".result-item-title a")
                    title = title_element.text.strip()
                    url = title_element["href"]
                    
                    info_spans = item.select(".result-item-info span")
                    author = info_spans[0].text.replace("作者：", "").strip() if len(info_spans) > 0 else "未知"
                    category = info_spans[1].text.replace("分类：", "").strip() if len(info_spans) > 1 else "未知"
                    status = info_spans[2].text.replace("状态：", "").strip() if len(info_spans) > 2 else "未知"
                    update_time = info_spans[3].text.replace("更新：", "").strip() if len(info_spans) > 3 else "未知"
                    
                    desc_element = item.select_one(".result-item-desc")
                    description = desc_element.text.strip() if desc_element else ""
                    
                    results.append({
                        "title": title,
                        "url": url,
                        "author": author,
                        "category": category,
                        "status": status,
                        "update_time": update_time,
                        "description": description
                    })
                except Exception as e:
                    logging.warning(f"解析搜索结果项时出错: {e}")
                    continue
            
            logging.info(f"搜索完成，找到 {len(results)} 个结果")
            return results
        except Exception as e:
            logging.error(f"搜索小说时出错: {e}")
            return []
    
    def get_novel_info(self, novel_url):
        """获取小说详细信息
        
        Args:
            novel_url: 小说详情页URL
            
        Returns:
            dict: 小说详细信息
        """
        try:
            logging.info(f"获取小说信息: {novel_url}")
            
            # 获取小说详情页
            html = self.get_page(novel_url)
            if not html:
                return None
            
            # 解析小说信息
            soup = BeautifulSoup(html, "html.parser")
            
            title = soup.select_one(".book-info h1").text.strip()
            
            meta_spans = soup.select(".book-info .book-meta span")
            author = meta_spans[0].text.replace("作者：", "").strip() if len(meta_spans) > 0 else "未知"
            category = meta_spans[1].text.replace("分类：", "").strip() if len(meta_spans) > 1 else "未知"
            status = meta_spans[2].text.replace("状态：", "").strip() if len(meta_spans) > 2 else "未知"
            update_time = meta_spans[3].text.replace("更新：", "").strip() if len(meta_spans) > 3 else "未知"
            
            latest_chapter_element = soup.select_one(".book-info .book-meta span:nth-child(5) a")
            latest_chapter = latest_chapter_element.text.strip() if latest_chapter_element else "未知"
            
            description_element = soup.select_one(".book-info .book-intro")
            description = description_element.text.strip() if description_element else ""
            
            # 获取章节列表
            chapter_elements = soup.select(".catalog-list li a")
            chapters = []
            
            for element in chapter_elements:
                chapter_title = element.text.strip()
                chapter_url = element["href"]
                chapters.append({
                    "title": chapter_title,
                    "url": chapter_url
                })
            
            novel_info = {
                "title": title,
                "author": author,
                "category": category,
                "status": status,
                "update_time": update_time,
                "latest_chapter": latest_chapter,
                "description": description,
                "chapters": chapters,
                "total_chapters": len(chapters)
            }
            
            logging.info(f"获取小说信息成功: {title}, 共 {len(chapters)} 章")
            return novel_info
        except Exception as e:
            logging.error(f"获取小说信息时出错: {e}")
            return None
    
    def download_chapter(self, chapter_info, novel_dir, retry=3):
        """下载单个章节
        
        Args:
            chapter_info: 章节信息，包含title和url
            novel_dir: 小说保存目录
            retry: 重试次数
            
        Returns:
            tuple: (章节标题, 章节内容, 是否成功)
        """
        chapter_title = chapter_info["title"]
        chapter_url = chapter_info["url"]
        chapter_filename = os.path.join(novel_dir, f"{chapter_title}.txt")
        
        # 检查是否已下载
        if chapter_url in self.downloaded_chapters:
            logging.info(f"章节已下载，跳过: {chapter_title}")
            return chapter_title, "", True
        
        # 检查文件是否存在
        if os.path.exists(chapter_filename):
            logging.info(f"章节文件已存在，跳过: {chapter_title}")
            self.downloaded_chapters.add(chapter_url)
            return chapter_title, "", True
        
        for attempt in range(retry):
            try:
                # 获取章节页面
                html = self.get_page(chapter_url)
                if not html:
                    continue
                
                # 解析章节内容
                soup = BeautifulSoup(html, "html.parser")
                
                title_element = soup.select_one(".content h1")
                title_text = title_element.text.strip() if title_element else chapter_title
                
                content_element = soup.select_one(".content .content-txt")
                if not content_element:
                    logging.warning(f"未找到章节内容: {chapter_title}")
                    continue
                
                content_text = content_element.text.strip()
                
                # 清理内容
                content_text = re.sub(r'\s+', '\n', content_text)
                content_text = re.sub(r'(笔趣阁|www\.biquge\.com|http://\S+)', '', content_text)
                
                # 保存章节
                with open(chapter_filename, 'w', encoding='utf-8') as f:
                    f.write(f"{title_text}\n\n{content_text}")
                
                # 记录已下载
                self.downloaded_chapters.add(chapter_url)
                
                logging.info(f"下载章节成功: {chapter_title}")
                return chapter_title, content_text, True
            except Exception as e:
                logging.error(f"下载章节出错 ({attempt+1}/{retry}): {chapter_title}, 错误: {e}")
                self.random_sleep(2, 5)
        
        logging.error(f"下载章节失败，已达到最大重试次数: {chapter_title}")
        return chapter_title, "", False
    
    def download_novel(self, novel_info, start_chapter=0, end_chapter=None, save_info=True):
        """下载整本小说
        
        Args:
            novel_info: 小说信息
            start_chapter: 开始章节索引
            end_chapter: 结束章节索引，None表示下载到最后
            save_info: 是否保存小说信息
            
        Returns:
            str: 小说保存目录
        """
        title = novel_info["title"]
        author = novel_info["author"]
        chapters = novel_info["chapters"]
        
        # 创建小说目录
        novel_dir = os.path.join(self.download_dir, f"{title}__{author}")
        if not os.path.exists(novel_dir):
            os.makedirs(novel_dir)
        
        # 保存小说信息
        if save_info:
            info_file = os.path.join(novel_dir, "info.json")
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(novel_info, f, ensure_ascii=False, indent=4)
        
        # 确定下载范围
        if end_chapter is None:
            end_chapter = len(chapters)
        else:
            end_chapter = min(end_chapter, len(chapters))
        
        # 创建下载进度文件
        progress_file = os.path.join(novel_dir, "progress.json")
        if os.path.exists(progress_file):
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress = json.load(f)
                self.downloaded_chapters = set(progress.get("downloaded_chapters", []))
        
        # 计算需要下载的章节
        chapters_to_download = chapters[start_chapter:end_chapter]
        total_chapters = len(chapters_to_download)
        
        logging.info(f"开始下载小说: {title}, 作者: {author}, 章节范围: {start_chapter}-{end_chapter-1}, 共 {total_chapters} 章")
        
        # 使用线程池下载章节
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.download_chapter, chapter, novel_dir) for chapter in chapters_to_download]
            
            # 显示进度
            completed = 0
            for future in futures:
                result = future.result()
                results.append(result)
                completed += 1
                
                # 更新进度
                if completed % 10 == 0 or completed == total_chapters:
                    progress_percent = (completed / total_chapters) * 100
                    logging.info(f"下载进度: {completed}/{total_chapters} ({progress_percent:.2f}%)")
                    
                    # 保存进度
                    with open(progress_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "total_chapters": total_chapters,
                            "completed_chapters": completed,
                            "downloaded_chapters": list(self.downloaded_chapters)
                        }, f, ensure_ascii=False, indent=4)
        
        # 统计结果
        success_count = sum(1 for _, _, success in results if success)
        fail_count = total_chapters - success_count
        
        logging.info(f"小说下载完成: {title}, 成功: {success_count} 章, 失败: {fail_count} 章")
        
        return novel_dir
    
    def merge_novel(self, novel_dir, output_filename=None):
        """合并小说章节为单个文件
        
        Args:
            novel_dir: 小说目录
            output_filename: 输出文件名，默认为小说名.txt
            
        Returns:
            str: 合并后的文件路径
        """
        try:
            # 获取小说信息
            info_file = os.path.join(novel_dir, "info.json")
            if not os.path.exists(info_file):
                logging.error(f"小说信息文件不存在: {info_file}")
                return None
            
            with open(info_file, 'r', encoding='utf-8') as f:
                novel_info = json.load(f)
            
            title = novel_info["title"]
            author = novel_info["author"]
            description = novel_info["description"]
            chapters = novel_info["chapters"]
            
            # 确定输出文件名
            if output_filename is None:
                output_filename = os.path.join(self.download_dir, f"{title}.txt")
            
            logging.info(f"开始合并小说: {title}, 输出文件: {output_filename}")
            
            # 写入小说信息
            with open(output_filename, 'w', encoding='utf-8') as outfile:
                outfile.write(f"书名：{title}\n")
                outfile.write(f"作者：{author}\n")
                outfile.write(f"简介：{description}\n\n")
                
                # 按章节顺序合并
                for chapter in chapters:
                    chapter_title = chapter["title"]
                    chapter_file = os.path.join(novel_dir, f"{chapter_title}.txt")
                    
                    if os.path.exists(chapter_file):
                        with open(chapter_file, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                            outfile.write(f"\n{content}\n\n")
                    else:
                        logging.warning(f"章节文件不存在，跳过: {chapter_file}")
            
            logging.info(f"小说合并完成: {output_filename}")
            return output_filename
        except Exception as e:
            logging.error(f"合并小说时出错: {e}")
            return None
    
    def interactive(self):
        """交互式爬虫界面"""
        print("\n===== 笔趣阁小说爬虫（代理池版）=====\n")
        print("本程序仅用于学习和研究网络爬虫技术，请勿用于任何商业用途！")
        print("请尊重版权，支持正版！\n")
        print("正在初始化代理池，请稍候...")
        
        # 等待代理池初始化
        time.sleep(5)
        
        while True:
            keyword = input("\n请输入小说名称或作者（输入q退出）: ")
            if keyword.lower() == 'q':
                break
            
            print("\n正在搜索，请稍候...")
            results = self.search_novel(keyword)
            
            if not results:
                print("未找到相关小说，请更换关键词重试。")
                continue
            
            print(f"\n找到 {len(results)} 个结果：")
            for i, novel in enumerate(results):
                print(f"[{i+1}] {novel['title']} - {novel['author']} ({novel['status']})")
                print(f"    分类: {novel['category']} | 更新: {novel['update_time']}")
                print(f"    简介: {novel['description'][:100]}...")
                print()
            
            while True:
                try:
                    choice = input("请选择小说序号（输入0返回搜索）: ")
                    if choice == '0':
                        break
                    
                    index = int(choice) - 1
                    if 0 <= index < len(results):
                        selected_novel = results[index]
                        print(f"\n您选择了: {selected_novel['title']} - {selected_novel['author']}")
                        print("正在获取小说信息，请稍候...")
                        
                        novel_info = self.get_novel_info(selected_novel['url'])
                        if not novel_info:
                            print("获取小说信息失败，请重试。")
                            continue
                        
                        print(f"\n小说名: {novel_info['title']}")
                        print(f"作者: {novel_info['author']}")
                        print(f"分类: {novel_info['category']}")
                        print(f"状态: {novel_info['status']}")
                        print(f"最新章节: {novel_info['latest_chapter']}")
                        print(f"更新时间: {novel_info['update_time']}")
                        print(f"章节数: {novel_info['total_chapters']}")
                        print(f"简介: {novel_info['description']}")
                        
                        download = input("\n是否下载这本小说？(y/n): ")
                        if download.lower() == 'y':
                            start_chapter = 0
                            end_chapter = None
                            
                            try:
                                range_input = input("请输入下载范围（格式：起始章节-结束章节，直接回车下载全部）: ")
                                if range_input.strip():
                                    parts = range_input.split('-')
                                    if len(parts) == 2:
                                        start_chapter = int(parts[0]) - 1  # 转为0-based索引
                                        end_chapter = int(parts[1])
                                    elif len(parts) == 1:
                                        start_chapter = int(parts[0]) - 1
                            except ValueError:
                                print("输入格式错误，将下载全部章节。")
                            
                            print(f"\n开始下载小说: {novel_info['title']}")
                            print(f"下载范围: {start_chapter+1}-{end_chapter if end_chapter else '末尾'}")
                            print("下载过程中请勿关闭程序，可能需要较长时间...")
                            
                            novel_dir = self.download_novel(novel_info, start_chapter, end_chapter)
                            
                            merge = input("\n是否将章节合并为单个文件？(y/n): ")
                            if merge.lower() == 'y':
                                output_file = self.merge_novel(novel_dir)
                                if output_file:
                                    print(f"\n小说已合并保存至: {output_file}")
                            
                            print(f"\n小说下载完成！保存在: {novel_dir}")
                        break
                    else:
                        print("序号无效，请重新输入。")
                except ValueError:
                    print("请输入有效的数字。")
            
            print("\n")

def main():
    try:
        # 创建爬虫实例
        spider = BiqugeProxySpider(max_workers=3)
        
        # 启动交互式界面
        spider.interactive()
        
    except KeyboardInterrupt:
        print("\n程序已中断。")
    except Exception as e:
        print(f"\n程序出错: {e}")
    finally:
        print("\n感谢使用，再见！")

if __name__ == "__main__":
    main()