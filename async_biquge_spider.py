import os
import time
import random
import re
import json
import logging
import asyncio
import aiohttp
from urllib.parse import quote
from bs4 import BeautifulSoup
from aiohttp import ClientSession, TCPConnector
from aiofiles import open as aio_open

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("async_spider.log"),
        logging.StreamHandler()
    ]
)

class AsyncBiqugeSpider:
    """异步笔趣阁爬虫，使用asyncio和aiohttp实现高并发爬取"""
    
    def __init__(self, download_dir="novels", max_concurrency=10, timeout=30):
        """初始化爬虫
        
        Args:
            download_dir: 小说下载目录
            max_concurrency: 最大并发请求数
            timeout: 请求超时时间（秒）
        """
        self.base_url = "https://www.bqgl.cc/"
        self.search_url = f"{self.base_url}/search.php?q="
        self.download_dir = download_dir
        self.max_concurrency = max_concurrency
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrency)  # 控制并发请求数
        
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
        
        # 记录已下载的章节，用于断点续传
        self.downloaded_chapters = set()
        
        logging.info("异步爬虫初始化完成")
    
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
    
    async def random_sleep(self, min_seconds=0.5, max_seconds=1.5):
        """异步随机等待一段时间，避免请求过于频繁"""
        await asyncio.sleep(random.uniform(min_seconds, max_seconds))
    
    async def get_page(self, session, url, retry=3):
        """异步获取页面内容
        
        Args:
            session: aiohttp会话
            url: 页面URL
            retry: 重试次数
            
        Returns:
            str: 页面HTML内容，失败返回空字符串
        """
        async with self.semaphore:  # 使用信号量控制并发
            for attempt in range(retry):
                try:
                    headers = self.get_headers()
                    async with session.get(url, headers=headers, timeout=self.timeout) as response:
                        if response.status == 200:
                            return await response.text()
                        else:
                            logging.warning(f"获取页面失败，状态码: {response.status}, URL: {url}")
                except Exception as e:
                    logging.warning(f"获取页面出错 ({attempt+1}/{retry}): {url}, 错误: {e}")
                
                # 失败后等待更长时间再重试
                await asyncio.sleep(random.uniform(2, 5))
            
            logging.error(f"获取页面失败，已达到最大重试次数: {url}")
            return ""
    
    async def search_novel(self, keyword):
        """异步搜索小说
        
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
            
            # 创建TCP连接器，限制并发连接数
            connector = TCPConnector(limit=self.max_concurrency, ssl=False)
            
            async with ClientSession(connector=connector) as session:
                # 获取搜索页面
                html = await self.get_page(session, search_url)
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
    
    async def get_novel_info(self, novel_url):
        """异步获取小说详细信息
        
        Args:
            novel_url: 小说详情页URL
            
        Returns:
            dict: 小说详细信息
        """
        try:
            logging.info(f"获取小说信息: {novel_url}")
            
            # 创建TCP连接器，限制并发连接数
            connector = TCPConnector(limit=self.max_concurrency, ssl=False)
            
            async with ClientSession(connector=connector) as session:
                # 获取小说详情页
                html = await self.get_page(session, novel_url)
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
    
    async def download_chapter(self, session, chapter_info, novel_dir, retry=3):
        """异步下载单个章节
        
        Args:
            session: aiohttp会话
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
                html = await self.get_page(session, chapter_url)
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
                
                # 异步保存章节
                async with aio_open(chapter_filename, 'w', encoding='utf-8') as f:
                    await f.write(f"{title_text}\n\n{content_text}")
                
                # 记录已下载
                self.downloaded_chapters.add(chapter_url)
                
                logging.info(f"下载章节成功: {chapter_title}")
                return chapter_title, content_text, True
            except Exception as e:
                logging.error(f"下载章节出错 ({attempt+1}/{retry}): {chapter_title}, 错误: {e}")
                await asyncio.sleep(random.uniform(2, 5))
        
        logging.error(f"下载章节失败，已达到最大重试次数: {chapter_title}")
        return chapter_title, "", False
    
    async def download_novel(self, novel_info, start_chapter=0, end_chapter=None, save_info=True):
        """异步下载整本小说
        
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
            async with aio_open(info_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(novel_info, ensure_ascii=False, indent=4))
        
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
        
        # 创建TCP连接器，限制并发连接数
        connector = TCPConnector(limit=self.max_concurrency, ssl=False)
        
        async with ClientSession(connector=connector) as session:
            # 创建下载任务
            tasks = [self.download_chapter(session, chapter, novel_dir) for chapter in chapters_to_download]
            
            # 分批执行任务，避免创建过多任务
            batch_size = 50
            results = []
            
            for i in range(0, len(tasks), batch_size):
                batch_tasks = tasks[i:i+batch_size]
                batch_results = await asyncio.gather(*batch_tasks)
                results.extend(batch_results)
                
                # 更新进度
                completed = min(i + batch_size, total_chapters)
                progress_percent = (completed / total_chapters) * 100
                logging.info(f"下载进度: {completed}/{total_chapters} ({progress_percent:.2f}%)")
                
                # 保存进度
                async with aio_open(progress_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps({
                        "total_chapters": total_chapters,
                        "completed_chapters": completed,
                        "downloaded_chapters": list(self.downloaded_chapters)
                    }, ensure_ascii=False, indent=4))
        
        # 统计结果
        success_count = sum(1 for _, _, success in results if success)
        fail_count = total_chapters - success_count
        
        logging.info(f"小说下载完成: {title}, 成功: {success_count} 章, 失败: {fail_count} 章")
        
        return novel_dir
    
    async def merge_novel(self, novel_dir, output_filename=None):
        """异步合并小说章节为单个文件
        
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
            async with aio_open(output_filename, 'w', encoding='utf-8') as outfile:
                await outfile.write(f"书名：{title}\n")
                await outfile.write(f"作者：{author}\n")
                await outfile.write(f"简介：{description}\n\n")
                
                # 按章节顺序合并
                for chapter in chapters:
                    chapter_title = chapter["title"]
                    chapter_file = os.path.join(novel_dir, f"{chapter_title}.txt")
                    
                    if os.path.exists(chapter_file):
                        async with aio_open(chapter_file, 'r', encoding='utf-8') as infile:
                            content = await infile.read()
                            await outfile.write(f"\n{content}\n\n")
                    else:
                        logging.warning(f"章节文件不存在，跳过: {chapter_file}")
            
            logging.info(f"小说合并完成: {output_filename}")
            return output_filename
        except Exception as e:
            logging.error(f"合并小说时出错: {e}")
            return None

async def interactive():
    """异步交互式爬虫界面"""
    print("\n===== 异步笔趣阁小说爬虫 =====\n")
    print("本程序仅用于学习和研究网络爬虫技术，请勿用于任何商业用途！")
    print("请尊重版权，支持正版！\n")
    
    # 创建爬虫实例
    spider = AsyncBiqugeSpider(max_concurrency=10)
    
    while True:
        keyword = input("\n请输入小说名称或作者（输入q退出）: ")
        if keyword.lower() == 'q':
            break
        
        print("\n正在搜索，请稍候...")
        results = await spider.search_novel(keyword)
        
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
                    
                    novel_info = await spider.get_novel_info(selected_novel['url'])
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
                        
                        start_time = time.time()
                        novel_dir = await spider.download_novel(novel_info, start_chapter, end_chapter)
                        end_time = time.time()
                        
                        print(f"\n下载耗时: {end_time - start_time:.2f} 秒")
                        
                        merge = input("\n是否将章节合并为单个文件？(y/n): ")
                        if merge.lower() == 'y':
                            output_file = await spider.merge_novel(novel_dir)
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
        # 运行异步交互式界面
        asyncio.run(interactive())
    except KeyboardInterrupt:
        print("\n程序已中断。")
    except Exception as e:
        print(f"\n程序出错: {e}")
    finally:
        print("\n感谢使用，再见！")

if __name__ == "__main__":
    main()