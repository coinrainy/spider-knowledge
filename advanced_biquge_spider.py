import time
import random
import os
import re
import json
import logging
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from concurrent.futures import ThreadPoolExecutor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("spider.log"),
        logging.StreamHandler()
    ]
)

class AdvancedBiqugeSpider:
    """高级笔趣阁爬虫，使用Selenium处理动态内容和反爬机制"""
    
    def __init__(self, headless=True, download_dir="novels", max_workers=5, timeout=10):
        """初始化爬虫
        
        Args:
            headless: 是否使用无头模式（不显示浏览器界面）
            download_dir: 小说下载目录
            max_workers: 最大线程数
            timeout: 页面加载超时时间（秒）
        """
        self.base_url = "https://www.biquge.com"
        self.search_url = f"{self.base_url}/search.php?q="
        self.download_dir = download_dir
        self.max_workers = max_workers
        self.timeout = timeout
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
            
        # 初始化浏览器
        self.init_browser(headless)
        
        # 初始化线程池
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 记录已下载的章节，用于断点续传
        self.downloaded_chapters = set()
        
        logging.info("爬虫初始化完成")
    
    def init_browser(self, headless=True):
        """初始化浏览器"""
        try:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
            
            # 添加反爬参数
            chrome_options.add_argument(f"--user-agent={random.choice(self.user_agents)}")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            
            # 禁用图片加载以提高速度
            chrome_options.add_argument("--blink-settings=imagesEnabled=false")
            
            # 禁用JavaScript弹窗
            chrome_options.add_argument("--disable-popup-blocking")
            
            # 禁用扩展
            chrome_options.add_argument("--disable-extensions")
            
            # 禁用GPU加速
            chrome_options.add_argument("--disable-gpu")
            
            # 禁用沙盒模式
            chrome_options.add_argument("--no-sandbox")
            
            # 禁用开发者工具
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # 设置窗口大小
            chrome_options.add_argument("--window-size=1920,1080")
            
            # 初始化浏览器
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # 设置页面加载超时
            self.driver.set_page_load_timeout(self.timeout)
            
            # 修改WebDriver特征
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            
            logging.info("浏览器初始化成功")
        except Exception as e:
            logging.error(f"浏览器初始化失败: {e}")
            raise
    
    def __del__(self):
        """析构函数，确保浏览器关闭"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
            if hasattr(self, 'executor'):
                self.executor.shutdown()
        except Exception as e:
            logging.error(f"关闭资源时出错: {e}")
    
    def random_sleep(self, min_seconds=1, max_seconds=3):
        """随机等待一段时间，避免请求过于频繁"""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
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
            
            # 访问搜索页面
            self.driver.get(search_url)
            
            # 等待搜索结果加载
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".result-item"))
            )
            
            # 随机等待，模拟人类行为
            self.random_sleep()
            
            # 获取搜索结果
            result_items = self.driver.find_elements(By.CSS_SELECTOR, ".result-item")
            
            results = []
            for item in result_items:
                try:
                    title_element = item.find_element(By.CSS_SELECTOR, ".result-item-title a")
                    title = title_element.text
                    url = title_element.get_attribute("href")
                    
                    author_element = item.find_element(By.CSS_SELECTOR, ".result-item-info span:nth-child(1)")
                    author = author_element.text.replace("作者：", "")
                    
                    category_element = item.find_element(By.CSS_SELECTOR, ".result-item-info span:nth-child(2)")
                    category = category_element.text.replace("分类：", "")
                    
                    status_element = item.find_element(By.CSS_SELECTOR, ".result-item-info span:nth-child(3)")
                    status = status_element.text.replace("状态：", "")
                    
                    update_element = item.find_element(By.CSS_SELECTOR, ".result-item-info span:nth-child(4)")
                    update_time = update_element.text.replace("更新：", "")
                    
                    desc_element = item.find_element(By.CSS_SELECTOR, ".result-item-desc")
                    description = desc_element.text
                    
                    results.append({
                        "title": title,
                        "url": url,
                        "author": author,
                        "category": category,
                        "status": status,
                        "update_time": update_time,
                        "description": description
                    })
                except NoSuchElementException as e:
                    logging.warning(f"解析搜索结果项时出错: {e}")
                    continue
            
            logging.info(f"搜索完成，找到 {len(results)} 个结果")
            return results
        except TimeoutException:
            logging.error("搜索超时，可能是网络问题或网站结构变化")
            return []
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
            
            # 访问小说详情页
            self.driver.get(novel_url)
            
            # 等待页面加载
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".book-info"))
            )
            
            # 随机等待
            self.random_sleep()
            
            # 获取小说信息
            title = self.driver.find_element(By.CSS_SELECTOR, ".book-info h1").text
            author = self.driver.find_element(By.CSS_SELECTOR, ".book-info .book-meta span:nth-child(1)").text.replace("作者：", "")
            category = self.driver.find_element(By.CSS_SELECTOR, ".book-info .book-meta span:nth-child(2)").text.replace("分类：", "")
            status = self.driver.find_element(By.CSS_SELECTOR, ".book-info .book-meta span:nth-child(3)").text.replace("状态：", "")
            update_time = self.driver.find_element(By.CSS_SELECTOR, ".book-info .book-meta span:nth-child(4)").text.replace("更新：", "")
            latest_chapter = self.driver.find_element(By.CSS_SELECTOR, ".book-info .book-meta span:nth-child(5) a").text
            description = self.driver.find_element(By.CSS_SELECTOR, ".book-info .book-intro").text
            
            # 获取章节列表
            chapter_elements = self.driver.find_elements(By.CSS_SELECTOR, ".catalog-list li a")
            chapters = []
            
            for element in chapter_elements:
                chapter_title = element.text
                chapter_url = element.get_attribute("href")
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
        except TimeoutException:
            logging.error("获取小说信息超时，可能是网络问题或网站结构变化")
            return None
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
                # 创建新的浏览器实例，避免主浏览器被阻塞
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument(f"--user-agent={random.choice(self.user_agents)}")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option("useAutomationExtension", False)
                chrome_options.add_argument("--blink-settings=imagesEnabled=false")
                
                temp_driver = webdriver.Chrome(options=chrome_options)
                temp_driver.set_page_load_timeout(self.timeout)
                
                # 访问章节页面
                temp_driver.get(chapter_url)
                
                # 等待内容加载
                WebDriverWait(temp_driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".content"))
                )
                
                # 随机等待
                time.sleep(random.uniform(0.5, 1.5))
                
                # 获取章节标题和内容
                chapter_title_element = temp_driver.find_element(By.CSS_SELECTOR, ".content h1")
                chapter_title_text = chapter_title_element.text
                
                content_element = temp_driver.find_element(By.CSS_SELECTOR, ".content .content-txt")
                content_text = content_element.text
                
                # 清理内容
                content_text = re.sub(r'\s+', '\n', content_text)
                content_text = re.sub(r'(笔趣阁|www\.biquge\.com|http://\S+)', '', content_text)
                
                # 保存章节
                with open(chapter_filename, 'w', encoding='utf-8') as f:
                    f.write(f"{chapter_title_text}\n\n{content_text}")
                
                # 记录已下载
                self.downloaded_chapters.add(chapter_url)
                
                logging.info(f"下载章节成功: {chapter_title}")
                
                # 关闭临时浏览器
                temp_driver.quit()
                
                return chapter_title, content_text, True
            except TimeoutException:
                logging.warning(f"下载章节超时，重试 ({attempt+1}/{retry}): {chapter_title}")
                try:
                    if 'temp_driver' in locals():
                        temp_driver.quit()
                except Exception:
                    pass
                time.sleep(random.uniform(2, 5))  # 超时后等待更长时间
            except Exception as e:
                logging.error(f"下载章节出错 ({attempt+1}/{retry}): {chapter_title}, 错误: {e}")
                try:
                    if 'temp_driver' in locals():
                        temp_driver.quit()
                except Exception:
                    pass
                time.sleep(random.uniform(2, 5))
        
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
        print("\n===== 高级笔趣阁小说爬虫 =====\n")
        print("本程序仅用于学习和研究网络爬虫技术，请勿用于任何商业用途！")
        print("请尊重版权，支持正版！\n")
        
        while True:
            keyword = input("请输入小说名称或作者（输入q退出）: ")
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
        spider = AdvancedBiqugeSpider(headless=True, max_workers=3)
        
        # 启动交互式界面
        spider.interactive()
        
    except KeyboardInterrupt:
        print("\n程序已中断。")
    except WebDriverException as e:
        print(f"\n浏览器驱动错误: {e}")
        print("请确保已安装Chrome浏览器和对应版本的ChromeDriver。")
    except Exception as e:
        print(f"\n程序出错: {e}")
    finally:
        print("\n感谢使用，再见！")

if __name__ == "__main__":
    main()