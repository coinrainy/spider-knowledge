import requests
from bs4 import BeautifulSoup
import time
import os
import random
import re


class BiqugeSpider:
    """笔趣阁小说爬虫"""

    def __init__(self):
        # 设置请求头，模拟浏览器访问
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        }
        # 创建会话对象，维持同一个会话
        self.session = requests.Session()
        # 设置基础URL（以笔趣阁为例，实际URL可能需要更新）
        self.base_url = 'https://www.xbiquge.la'
        # 设置小说保存路径
        self.save_dir = 'novels'
        # 确保保存目录存在
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def get_page(self, url):
        """获取页面内容
        
        Args:
            url: 页面URL
            
        Returns:
            BeautifulSoup对象
        """
        try:
            # 添加随机延时，避免请求过快
            time.sleep(random.uniform(0.5, 2))
            # 发送GET请求
            response = self.session.get(url, headers=self.headers, timeout=10)
            # 设置编码
            response.encoding = 'utf-8'
            # 检查请求是否成功
            if response.status_code == 200:
                # 返回BeautifulSoup对象
                return BeautifulSoup(response.text, 'html.parser')
            else:
                print(f"请求失败，状态码：{response.status_code}")
                return None
        except Exception as e:
            print(f"请求异常：{e}")
            return None

    def search_novel(self, keyword):
        """搜索小说
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            搜索结果列表，每个元素为(小说名, 小说URL, 作者)
        """
        # 构造搜索URL（实际URL可能需要调整）
        search_url = f"{self.base_url}/modules/article/search.php?searchkey={keyword}"
        soup = self.get_page(search_url)
        if not soup:
            return []

        results = []
        # 查找搜索结果列表
        # 注意：以下选择器需要根据实际网站结构调整
        novel_list = soup.select('div.result-list div.result-item')
        for novel in novel_list:
            try:
                title_elem = novel.select_one('div.result-game-item-title a')
                title = title_elem.text.strip()
                url = title_elem['href']
                author = novel.select_one('div.result-game-item-info p.result-game-item-info-tag:nth-child(1) span').text.strip()
                results.append((title, url, author))
            except Exception as e:
                print(f"解析搜索结果异常：{e}")
                continue

        return results

    def get_novel_info(self, novel_url):
        """获取小说信息
        
        Args:
            novel_url: 小说详情页URL
            
        Returns:
            小说信息字典
        """
        soup = self.get_page(novel_url)
        if not soup:
            return None

        try:
            # 提取小说信息（以下选择器需要根据实际网站结构调整）
            info = {}
            info['title'] = soup.select_one('#info h1').text.strip()
            info['author'] = soup.select_one('#info p').text.replace('作者：', '').strip()
            info['intro'] = soup.select_one('#intro').text.strip()
            info['cover_url'] = soup.select_one('#fmimg img')['src'] if soup.select_one('#fmimg img') else ''
            
            # 获取章节列表
            chapters = []
            chapter_elements = soup.select('#list dd a')
            for chapter in chapter_elements:
                chapter_title = chapter.text.strip()
                chapter_url = novel_url + chapter['href'] if chapter['href'].startswith('/') else chapter['href']
                chapters.append((chapter_title, chapter_url))
            
            info['chapters'] = chapters
            return info
        except Exception as e:
            print(f"获取小说信息异常：{e}")
            return None

    def get_chapter_content(self, chapter_url):
        """获取章节内容
        
        Args:
            chapter_url: 章节URL
            
        Returns:
            章节内容文本
        """
        soup = self.get_page(chapter_url)
        if not soup:
            return ""

        try:
            # 提取章节内容（以下选择器需要根据实际网站结构调整）
            content_elem = soup.select_one('#content')
            if not content_elem:
                return ""
            
            # 获取文本内容
            content = content_elem.text
            
            # 清理内容
            content = re.sub(r'\s+', '\n\n', content)  # 替换连续空白字符为换行
            content = re.sub(r'(笔趣阁|www\.xbiquge\.la|http\S+)', '', content)  # 移除网站信息
            
            return content.strip()
        except Exception as e:
            print(f"获取章节内容异常：{e}")
            return ""

    def download_novel(self, novel_url, max_chapters=None):
        """下载小说
        
        Args:
            novel_url: 小说详情页URL
            max_chapters: 最大下载章节数，None表示全部下载
            
        Returns:
            是否下载成功
        """
        # 获取小说信息
        novel_info = self.get_novel_info(novel_url)
        if not novel_info:
            print("获取小说信息失败")
            return False

        # 创建小说目录
        novel_dir = os.path.join(self.save_dir, novel_info['title'])
        if not os.path.exists(novel_dir):
            os.makedirs(novel_dir)

        # 保存小说信息
        with open(os.path.join(novel_dir, 'info.txt'), 'w', encoding='utf-8') as f:
            f.write(f"书名：{novel_info['title']}\n")
            f.write(f"作者：{novel_info['author']}\n")
            f.write(f"简介：{novel_info['intro']}\n")

        # 限制章节数量
        chapters = novel_info['chapters']
        if max_chapters and max_chapters < len(chapters):
            chapters = chapters[:max_chapters]

        # 下载章节内容
        print(f"开始下载《{novel_info['title']}》，共{len(chapters)}章")
        for i, (chapter_title, chapter_url) in enumerate(chapters):
            # 清理章节标题，移除非法字符
            clean_title = re.sub(r'[\\/:*?"<>|]', '_', chapter_title)
            chapter_file = os.path.join(novel_dir, f"{i+1:04d}_{clean_title}.txt")
            
            # 如果章节文件已存在，跳过下载
            if os.path.exists(chapter_file):
                print(f"章节已存在：{chapter_title}")
                continue
            
            # 获取章节内容
            content = self.get_chapter_content(chapter_url)
            if not content:
                print(f"获取章节内容失败：{chapter_title}")
                continue
            
            # 保存章节内容
            with open(chapter_file, 'w', encoding='utf-8') as f:
                f.write(f"{chapter_title}\n\n")
                f.write(content)
            
            print(f"下载完成：{chapter_title}")
            
            # 随机延时，避免请求过快
            time.sleep(random.uniform(1, 3))

        print(f"《{novel_info['title']}》下载完成，保存在 {novel_dir}")
        return True

    def merge_chapters(self, novel_title):
        """合并章节为单个文件
        
        Args:
            novel_title: 小说标题
            
        Returns:
            合并后的文件路径
        """
        novel_dir = os.path.join(self.save_dir, novel_title)
        if not os.path.exists(novel_dir):
            print(f"小说目录不存在：{novel_dir}")
            return None

        # 获取所有章节文件
        chapter_files = [f for f in os.listdir(novel_dir) if f.endswith('.txt') and f != 'info.txt']
        # 按文件名排序（确保章节顺序正确）
        chapter_files.sort()

        # 合并文件路径
        merged_file = os.path.join(self.save_dir, f"{novel_title}.txt")
        
        # 读取小说信息
        info_file = os.path.join(novel_dir, 'info.txt')
        info_content = ""
        if os.path.exists(info_file):
            with open(info_file, 'r', encoding='utf-8') as f:
                info_content = f.read()

        # 合并章节内容
        with open(merged_file, 'w', encoding='utf-8') as outfile:
            # 写入小说信息
            outfile.write(info_content)
            outfile.write("\n\n")
            
            # 写入各章节内容
            for chapter_file in chapter_files:
                with open(os.path.join(novel_dir, chapter_file), 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read())
                    outfile.write("\n\n")

        print(f"章节合并完成，保存为：{merged_file}")
        return merged_file


def main():
    # 创建爬虫实例
    spider = BiqugeSpider()
    
    # 搜索小说
    keyword = input("请输入要搜索的小说名称：")
    search_results = spider.search_novel(keyword)
    
    if not search_results:
        print("未找到相关小说")
        return
    
    # 显示搜索结果
    print(f"找到{len(search_results)}本相关小说：")
    for i, (title, url, author) in enumerate(search_results):
        print(f"{i+1}. {title} - {author}")
    
    # 选择小说
    choice = int(input("请输入要下载的小说序号：")) - 1
    if choice < 0 or choice >= len(search_results):
        print("无效的选择")
        return
    
    # 获取选择的小说信息
    selected_title, selected_url, _ = search_results[choice]
    
    # 设置最大下载章节数
    max_chapters = input("请输入要下载的最大章节数（直接回车下载全部）：")
    max_chapters = int(max_chapters) if max_chapters.strip() else None
    
    # 下载小说
    print(f"开始下载《{selected_title}》...")
    success = spider.download_novel(selected_url, max_chapters)
    
    if success:
        # 询问是否合并章节
        merge = input("是否将章节合并为单个文件？(y/n)：").lower() == 'y'
        if merge:
            spider.merge_chapters(selected_title)


if __name__ == "__main__":
    main()