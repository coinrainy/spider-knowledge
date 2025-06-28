#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
异步笔趣阁爬虫使用示例

这个脚本展示了如何使用AsyncBiqugeSpider类进行小说搜索、信息获取和下载。
"""

import asyncio
import logging
import os
from async_biquge_spider import AsyncBiqugeSpider

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("async_example.log"),
        logging.StreamHandler()
    ]
)

async def search_example():
    """搜索小说示例"""
    spider = AsyncBiqugeSpider()
    keyword = "斗破苍穹"
    
    print(f"\n搜索小说: {keyword}")
    results = await spider.search_novel(keyword)
    
    if not results:
        print("未找到相关小说")
        return
    
    print(f"\n找到 {len(results)} 个结果:")
    for i, novel in enumerate(results[:5]):  # 只显示前5个结果
        print(f"[{i+1}] {novel['title']} - {novel['author']} ({novel['status']})")
        print(f"    分类: {novel['category']} | 更新: {novel['update_time']}")
        print(f"    简介: {novel['description'][:100]}...")
        print()
    
    return results

async def get_novel_info_example(novel_url):
    """获取小说信息示例"""
    spider = AsyncBiqugeSpider()
    
    print(f"\n获取小说信息: {novel_url}")
    novel_info = await spider.get_novel_info(novel_url)
    
    if not novel_info:
        print("获取小说信息失败")
        return
    
    print(f"\n小说名: {novel_info['title']}")
    print(f"作者: {novel_info['author']}")
    print(f"分类: {novel_info['category']}")
    print(f"状态: {novel_info['status']}")
    print(f"最新章节: {novel_info['latest_chapter']}")
    print(f"更新时间: {novel_info['update_time']}")
    print(f"章节数: {novel_info['total_chapters']}")
    print(f"简介: {novel_info['description'][:200]}...")
    
    return novel_info

async def download_chapter_example(novel_info):
    """下载单个章节示例"""
    spider = AsyncBiqugeSpider()
    
    if not novel_info or not novel_info.get('chapters'):
        print("小说信息无效")
        return
    
    # 获取第一章信息
    first_chapter = novel_info['chapters'][0]
    print(f"\n下载第一章: {first_chapter['title']}")
    
    # 创建小说目录
    novel_dir = os.path.join(spider.download_dir, f"{novel_info['title']}__{novel_info['author']}")
    if not os.path.exists(novel_dir):
        os.makedirs(novel_dir)
    
    # 创建TCP连接器和会话
    from aiohttp import ClientSession, TCPConnector
    connector = TCPConnector(limit=5, ssl=False)
    
    async with ClientSession(connector=connector) as session:
        # 下载章节
        chapter_title, content, success = await spider.download_chapter(session, first_chapter, novel_dir)
        
        if success:
            print(f"章节 '{chapter_title}' 下载成功")
            # 显示内容前100个字符
            if content:
                print(f"内容预览: {content[:100]}...")
        else:
            print(f"章节 '{chapter_title}' 下载失败")

async def download_novel_example(novel_info, chapter_limit=5):
    """下载小说示例（限制章节数）"""
    spider = AsyncBiqugeSpider(max_concurrency=5)  # 限制并发数为5
    
    if not novel_info:
        print("小说信息无效")
        return
    
    print(f"\n开始下载小说: {novel_info['title']} (限制前{chapter_limit}章)")
    novel_dir = await spider.download_novel(novel_info, start_chapter=0, end_chapter=chapter_limit)
    
    if novel_dir:
        print(f"\n小说下载完成，保存在: {novel_dir}")
        
        # 合并章节
        print("\n开始合并章节...")
        output_file = await spider.merge_novel(novel_dir)
        
        if output_file:
            print(f"小说已合并保存至: {output_file}")
        else:
            print("合并章节失败")
    else:
        print("小说下载失败")

async def custom_spider_example():
    """自定义爬虫参数示例"""
    # 创建自定义参数的爬虫
    spider = AsyncBiqugeSpider(
        download_dir="custom_novels",  # 自定义下载目录
        max_concurrency=3,            # 限制并发数为3
        timeout=15                    # 设置超时时间为15秒
    )
    
    print("\n使用自定义参数的爬虫:")
    print(f"下载目录: {spider.download_dir}")
    print(f"最大并发数: {spider.max_concurrency}")
    print(f"超时时间: {spider.timeout}秒")
    
    # 搜索小说
    keyword = "修真"
    print(f"\n搜索关键词: {keyword}")
    results = await spider.search_novel(keyword)
    
    if results:
        print(f"找到 {len(results)} 个结果")
        # 只显示第一个结果的标题和作者
        first_result = results[0]
        print(f"第一个结果: {first_result['title']} - {first_result['author']}")
    else:
        print("未找到相关小说")

async def main():
    """主函数，运行所有示例"""
    try:
        # 1. 搜索小说
        results = await search_example()
        if not results:
            return
        
        # 2. 获取第一个搜索结果的详细信息
        first_novel = results[0]
        novel_info = await get_novel_info_example(first_novel['url'])
        if not novel_info:
            return
        
        # 3. 下载单个章节示例
        await download_chapter_example(novel_info)
        
        # 4. 下载小说示例（限制前5章）
        await download_novel_example(novel_info, chapter_limit=5)
        
        # 5. 自定义爬虫参数示例
        await custom_spider_example()
        
    except Exception as e:
        logging.error(f"运行示例时出错: {e}")

if __name__ == "__main__":
    print("===== 异步笔趣阁爬虫使用示例 =====\n")
    print("本程序仅用于学习和研究网络爬虫技术，请勿用于任何商业用途！")
    print("请尊重版权，支持正版！\n")
    
    # 运行异步主函数
    asyncio.run(main())
    
    print("\n示例运行完成！")