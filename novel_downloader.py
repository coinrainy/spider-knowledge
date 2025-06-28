#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
笔趣阁小说下载器 - 命令行工具

这个脚本提供了一个命令行界面，用于下载笔趣阁小说。
支持多种爬虫模式：同步、异步、Selenium和代理池。
"""

import os
import sys
import time
import argparse
import asyncio
import logging
from datetime import datetime

# 配置日志
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"downloader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# 检查是否安装了必要的依赖
required_packages = {
    'requests': False,
    'beautifulsoup4': False,
    'aiohttp': False,
    'aiofiles': False,
    'selenium': False
}

for package in required_packages:
    try:
        __import__(package)
        required_packages[package] = True
    except ImportError:
        pass

# 定义爬虫类型和依赖关系
spider_types = {
    'sync': ['requests', 'beautifulsoup4'],
    'async': ['aiohttp', 'aiofiles', 'requests', 'beautifulsoup4'],
    'selenium': ['selenium', 'requests', 'beautifulsoup4'],
    'proxy': ['requests', 'beautifulsoup4']
}

def check_dependencies(spider_type):
    """检查指定爬虫类型的依赖是否已安装"""
    missing = []
    for package in spider_types.get(spider_type, []):
        if not required_packages.get(package, False):
            missing.append(package)
    return missing

def install_dependencies(packages):
    """安装缺失的依赖"""
    if not packages:
        return True
    
    print(f"\n需要安装以下依赖: {', '.join(packages)}")
    choice = input("是否自动安装这些依赖？(y/n): ")
    
    if choice.lower() != 'y':
        return False
    
    try:
        import subprocess
        for package in packages:
            print(f"\n正在安装 {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"{package} 安装成功")
        return True
    except Exception as e:
        print(f"安装依赖时出错: {e}")
        return False

async def run_async_spider(args):
    """运行异步爬虫"""
    try:
        from async_biquge_spider import AsyncBiqugeSpider, interactive
        
        if args.interactive:
            await interactive()
        else:
            spider = AsyncBiqugeSpider(
                download_dir=args.output_dir,
                max_concurrency=args.concurrency,
                timeout=args.timeout
            )
            
            if args.keyword:
                print(f"\n搜索小说: {args.keyword}")
                results = await spider.search_novel(args.keyword)
                
                if not results:
                    print("未找到相关小说")
                    return
                
                print(f"\n找到 {len(results)} 个结果:")
                for i, novel in enumerate(results[:10]):  # 只显示前10个结果
                    print(f"[{i+1}] {novel['title']} - {novel['author']} ({novel['status']})")
                    print(f"    分类: {novel['category']} | 更新: {novel['update_time']}")
                    print(f"    简介: {novel['description'][:100]}...")
                    print()
                
                if args.index is None:
                    try:
                        index = int(input("请选择小说序号: ")) - 1
                        if index < 0 or index >= len(results):
                            print("无效的序号")
                            return
                    except ValueError:
                        print("请输入有效的数字")
                        return
                else:
                    index = args.index - 1
                    if index < 0 or index >= len(results):
                        print(f"无效的序号: {args.index}")
                        return
                
                selected_novel = results[index]
                print(f"\n您选择了: {selected_novel['title']} - {selected_novel['author']}")
                
                novel_info = await spider.get_novel_info(selected_novel['url'])
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
                
                start_chapter = args.start_chapter - 1 if args.start_chapter else 0
                end_chapter = args.end_chapter if args.end_chapter else None
                
                print(f"\n开始下载小说: {novel_info['title']}")
                print(f"下载范围: {start_chapter+1}-{end_chapter if end_chapter else '末尾'}")
                print("下载过程中请勿关闭程序，可能需要较长时间...")
                
                start_time = time.time()
                novel_dir = await spider.download_novel(novel_info, start_chapter, end_chapter)
                end_time = time.time()
                
                print(f"\n下载耗时: {end_time - start_time:.2f} 秒")
                
                if args.merge:
                    print("\n开始合并章节...")
                    output_file = await spider.merge_novel(novel_dir)
                    if output_file:
                        print(f"\n小说已合并保存至: {output_file}")
                
                print(f"\n小说下载完成！保存在: {novel_dir}")
    except Exception as e:
        logging.error(f"运行异步爬虫时出错: {e}")

def run_sync_spider(args):
    """运行同步爬虫"""
    try:
        from biquge_spider import BiqugeSpider, main as interactive_main
        
        if args.interactive:
            interactive_main()
        else:
            # 实现类似于异步爬虫的命令行参数处理
            spider = BiqugeSpider(download_dir=args.output_dir)
            
            if args.keyword:
                print(f"\n搜索小说: {args.keyword}")
                results = spider.search_novel(args.keyword)
                
                if not results:
                    print("未找到相关小说")
                    return
                
                print(f"\n找到 {len(results)} 个结果:")
                for i, novel in enumerate(results[:10]):  # 只显示前10个结果
                    print(f"[{i+1}] {novel['title']} - {novel['author']} ({novel['status']})")
                    print(f"    分类: {novel['category']} | 更新: {novel['update_time']}")
                    print(f"    简介: {novel['description'][:100]}...")
                    print()
                
                if args.index is None:
                    try:
                        index = int(input("请选择小说序号: ")) - 1
                        if index < 0 or index >= len(results):
                            print("无效的序号")
                            return
                    except ValueError:
                        print("请输入有效的数字")
                        return
                else:
                    index = args.index - 1
                    if index < 0 or index >= len(results):
                        print(f"无效的序号: {args.index}")
                        return
                
                selected_novel = results[index]
                print(f"\n您选择了: {selected_novel['title']} - {selected_novel['author']}")
                
                novel_info = spider.get_novel_info(selected_novel['url'])
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
                
                start_chapter = args.start_chapter - 1 if args.start_chapter else 0
                end_chapter = args.end_chapter if args.end_chapter else None
                
                print(f"\n开始下载小说: {novel_info['title']}")
                print(f"下载范围: {start_chapter+1}-{end_chapter if end_chapter else '末尾'}")
                print("下载过程中请勿关闭程序，可能需要较长时间...")
                
                start_time = time.time()
                novel_dir = spider.download_novel(novel_info, start_chapter, end_chapter)
                end_time = time.time()
                
                print(f"\n下载耗时: {end_time - start_time:.2f} 秒")
                
                if args.merge:
                    print("\n开始合并章节...")
                    output_file = spider.merge_chapters(novel_dir)
                    if output_file:
                        print(f"\n小说已合并保存至: {output_file}")
                
                print(f"\n小说下载完成！保存在: {novel_dir}")
    except Exception as e:
        logging.error(f"运行同步爬虫时出错: {e}")

def run_selenium_spider(args):
    """运行Selenium爬虫"""
    try:
        from advanced_biquge_spider import AdvancedBiqugeSpider, main as interactive_main
        
        if args.interactive:
            interactive_main()
        else:
            # 实现命令行参数处理
            print("正在初始化Selenium爬虫，这可能需要一些时间...")
            spider = AdvancedBiqugeSpider(
                download_dir=args.output_dir,
                headless=not args.show_browser
            )
            
            # 类似于其他爬虫的实现...
            if args.keyword:
                print(f"\n搜索小说: {args.keyword}")
                results = spider.search_novel(args.keyword)
                
                # 处理搜索结果和下载过程...
                # 这里的实现与同步爬虫类似，根据AdvancedBiqugeSpider的API进行调整
                
                # 完成后关闭浏览器
                spider.close()
    except Exception as e:
        logging.error(f"运行Selenium爬虫时出错: {e}")

def run_proxy_spider(args):
    """运行代理池爬虫"""
    try:
        from biquge_with_proxy import BiqugeProxySpider, main as interactive_main
        
        if args.interactive:
            interactive_main()
        else:
            # 实现命令行参数处理
            print("正在初始化代理池爬虫...")
            spider = BiqugeProxySpider(download_dir=args.output_dir)
            
            # 类似于其他爬虫的实现...
            if args.keyword:
                print(f"\n搜索小说: {args.keyword}")
                results = spider.search_novel(args.keyword)
                
                # 处理搜索结果和下载过程...
                # 这里的实现与同步爬虫类似，根据BiqugeProxySpider的API进行调整
    except Exception as e:
        logging.error(f"运行代理池爬虫时出错: {e}")

def main():
    """主函数，处理命令行参数并运行相应的爬虫"""
    parser = argparse.ArgumentParser(description="笔趣阁小说下载器 - 命令行工具")
    
    # 爬虫类型
    parser.add_argument(
        "-t", "--type", 
        choices=["sync", "async", "selenium", "proxy"], 
        default="async",
        help="爬虫类型: sync(同步), async(异步), selenium(浏览器), proxy(代理池)，默认为async"
    )
    
    # 交互模式
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="使用交互式模式"
    )
    
    # 搜索关键词
    parser.add_argument(
        "-k", "--keyword",
        help="搜索关键词"
    )
    
    # 选择序号
    parser.add_argument(
        "-n", "--index",
        type=int,
        help="选择搜索结果的序号（从1开始）"
    )
    
    # 章节范围
    parser.add_argument(
        "-s", "--start-chapter",
        type=int,
        help="起始章节（从1开始）"
    )
    
    parser.add_argument(
        "-e", "--end-chapter",
        type=int,
        help="结束章节"
    )
    
    # 输出目录
    parser.add_argument(
        "-o", "--output-dir",
        default="novels",
        help="小说保存目录，默认为'novels'"
    )
    
    # 合并章节
    parser.add_argument(
        "-m", "--merge",
        action="store_true",
        help="下载完成后合并章节"
    )
    
    # 异步爬虫特有参数
    parser.add_argument(
        "-c", "--concurrency",
        type=int,
        default=10,
        help="异步爬虫的最大并发数，默认为10"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="请求超时时间（秒），默认为30"
    )
    
    # Selenium爬虫特有参数
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="显示浏览器窗口（仅Selenium爬虫有效）"
    )
    
    args = parser.parse_args()
    
    # 检查依赖
    missing_packages = check_dependencies(args.type)
    if missing_packages:
        if not install_dependencies(missing_packages):
            print(f"\n缺少必要的依赖: {', '.join(missing_packages)}")
            print("请手动安装这些依赖后再运行程序")
            return
    
    print("\n===== 笔趣阁小说下载器 =====\n")
    print("本程序仅用于学习和研究网络爬虫技术，请勿用于任何商业用途！")
    print("请尊重版权，支持正版！\n")
    
    # 运行相应的爬虫
    try:
        if args.type == "async":
            asyncio.run(run_async_spider(args))
        elif args.type == "sync":
            run_sync_spider(args)
        elif args.type == "selenium":
            run_selenium_spider(args)
        elif args.type == "proxy":
            run_proxy_spider(args)
    except KeyboardInterrupt:
        print("\n程序已中断。")
    except Exception as e:
        logging.error(f"程序运行出错: {e}")
    finally:
        print("\n感谢使用，再见！")

if __name__ == "__main__":
    main()