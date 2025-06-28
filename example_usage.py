#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
笔趣阁爬虫使用示例

这个脚本展示了如何使用BiqugeSpider类来爬取指定小说，
无需通过交互式输入，适合批量或自动化任务。
"""

from biquge_spider import BiqugeSpider
import time


def example_search():
    """搜索小说示例"""
    spider = BiqugeSpider()
    print("示例1: 搜索小说")
    print("-" * 50)
    
    # 搜索小说
    keyword = "修真"
    print(f"搜索关键词: {keyword}")
    results = spider.search_novel(keyword)
    
    # 显示搜索结果
    print(f"找到 {len(results)} 本相关小说:")
    for i, (title, url, author) in enumerate(results[:5]):  # 只显示前5个结果
        print(f"{i+1}. {title} - {author} - {url}")
    
    print("-" * 50)
    print()


def example_get_info():
    """获取小说信息示例"""
    spider = BiqugeSpider()
    print("示例2: 获取小说信息")
    print("-" * 50)
    
    # 这里使用一个示例URL，实际使用时需要替换为真实的小说URL
    novel_url = "https://www.xbiquge.la/10/10489/"
    print(f"获取小说信息: {novel_url}")
    
    # 获取小说信息
    info = spider.get_novel_info(novel_url)
    if info:
        print(f"书名: {info['title']}")
        print(f"作者: {info['author']}")
        print(f"简介: {info['intro'][:100]}...")
        print(f"章节数: {len(info['chapters'])}")
        print("前5章:")
        for i, (title, url) in enumerate(info['chapters'][:5]):
            print(f"  {i+1}. {title}")
    else:
        print("获取小说信息失败")
    
    print("-" * 50)
    print()


def example_download_chapter():
    """下载单个章节示例"""
    spider = BiqugeSpider()
    print("示例3: 下载单个章节")
    print("-" * 50)
    
    # 这里使用一个示例章节URL，实际使用时需要替换为真实的章节URL
    chapter_url = "https://www.xbiquge.la/10/10489/4534454.html"
    print(f"下载章节: {chapter_url}")
    
    # 获取章节内容
    content = spider.get_chapter_content(chapter_url)
    if content:
        print(f"章节内容预览: \n{content[:200]}...")
        print(f"章节总字数: {len(content)}")
    else:
        print("获取章节内容失败")
    
    print("-" * 50)
    print()


def example_download_novel():
    """下载整本小说示例"""
    spider = BiqugeSpider()
    print("示例4: 下载小说(限制章节数)")
    print("-" * 50)
    
    # 这里使用一个示例URL，实际使用时需要替换为真实的小说URL
    novel_url = "https://www.xbiquge.la/10/10489/"
    max_chapters = 3  # 只下载前3章作为示例
    
    print(f"下载小说: {novel_url}")
    print(f"限制章节数: {max_chapters}")
    
    # 下载小说
    start_time = time.time()
    success = spider.download_novel(novel_url, max_chapters)
    end_time = time.time()
    
    if success:
        print(f"下载完成，耗时: {end_time - start_time:.2f}秒")
        
        # 获取小说信息以获取标题
        info = spider.get_novel_info(novel_url)
        if info:
            # 合并章节
            print("合并章节为单个文件...")
            merged_file = spider.merge_chapters(info['title'])
            if merged_file:
                print(f"合并完成，保存为: {merged_file}")
    else:
        print("下载失败")
    
    print("-" * 50)
    print()


def example_custom_spider():
    """自定义爬虫参数示例"""
    print("示例5: 自定义爬虫参数")
    print("-" * 50)
    
    # 创建爬虫实例并自定义参数
    spider = BiqugeSpider()
    # 修改基础URL
    spider.base_url = "https://www.xbiquge.la"
    # 修改保存目录
    spider.save_dir = "custom_novels"
    # 修改请求头
    spider.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
    
    print("自定义爬虫参数:")
    print(f"基础URL: {spider.base_url}")
    print(f"保存目录: {spider.save_dir}")
    print(f"User-Agent: {spider.headers['User-Agent']}")
    
    print("-" * 50)
    print()


def main():
    """运行所有示例"""
    print("笔趣阁爬虫使用示例")
    print("=" * 50)
    print()
    
    # 运行示例1: 搜索小说
    example_search()
    
    # 运行示例2: 获取小说信息
    example_get_info()
    
    # 运行示例3: 下载单个章节
    example_download_chapter()
    
    # 运行示例4: 下载整本小说(限制章节数)
    example_download_novel()
    
    # 运行示例5: 自定义爬虫参数
    example_custom_spider()
    
    print("所有示例运行完毕")
    print("=" * 50)


if __name__ == "__main__":
    main()