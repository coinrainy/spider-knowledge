#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
爬虫系统演示脚本
展示基础爬虫和高级爬虫的功能
"""

import os
import time
import json
from news_crawler_basic import BasicNewsCrawler
from news_crawler_advanced import AdvancedNewsCrawler

def demo_basic_crawler():
    """
    演示基础爬虫功能
    """
    print("\n" + "="*60)
    print("🚀 基础爬虫演示")
    print("="*60)
    
    # 创建基础爬虫实例
    crawler = BasicNewsCrawler()
    
    print("📰 开始爬取新闻...")
    
    # 爬取新闻
    news_data = crawler.crawl(['news'], max_pages=2)
    
    if news_data:
        print(f"\n✅ 成功爬取 {len(news_data)} 条新闻")
        print("\n📋 前3条新闻预览:")
        for i, news in enumerate(news_data[:3], 1):
            print(f"\n{i}. {news['title'][:50]}...")
            print(f"   🕒 时间: {news['pub_time']}")
            print(f"   🔗 链接: {news['link'][:60]}...")
            if news['summary']:
                print(f"   📝 摘要: {news['summary'][:80]}...")
    else:
        print("❌ 未能获取到新闻数据")
    
    return news_data

def demo_advanced_crawler():
    """
    演示高级爬虫功能
    """
    print("\n" + "="*60)
    print("🔥 高级爬虫演示")
    print("="*60)
    
    # 配置高级爬虫
    config = {
        'max_workers': 3,
        'request_delay': (1, 2),
        'timeout': 15,
        'max_retries': 3,
        'use_proxy': False,
        'target_sites': [
            {
                'name': '网易新闻',
                'base_url': 'https://news.163.com/',
                'list_selector': 'a',
                'title_selector': 'h1',
                'content_selector': '.post_content_main, .post_text'
            }
        ]
    }
    
    # 创建高级爬虫实例
    crawler = AdvancedNewsCrawler(config)
    
    print("🤖 启动高级爬虫（多线程 + 情感分析 + 数据可视化）...")
    
    # 运行爬虫
    crawler.run(max_news_per_site=20)
    
    print(f"\n✅ 高级爬虫完成，共爬取 {len(crawler.news_data)} 条新闻")
    
    # 显示统计信息
    if os.path.exists('news_data/statistics.json'):
        with open('news_data/statistics.json', 'r', encoding='utf-8') as f:
            stats = json.load(f)
        
        print("\n📊 数据统计:")
        print(f"   📰 总新闻数: {stats.get('total_news', 0)}")
        print(f"   📝 平均字数: {stats.get('avg_word_count', 0):.0f}")
        print(f"   💭 平均情感分: {stats.get('avg_sentiment', 0):.3f}")
        
        if 'sources' in stats:
            print("   🌐 新闻来源:")
            for source, count in stats['sources'].items():
                print(f"      - {source}: {count}条")
    
    # 检查生成的文件
    print("\n📁 生成的文件:")
    data_files = [
        'news_data/news.db',
        'news_data/news_export.csv',
        'news_data/news_export.xlsx',
        'news_data/statistics.json',
        'charts/news_sources.png',
        'charts/sentiment_distribution.png',
        'wordclouds/keywords_wordcloud.png'
    ]
    
    for file_path in data_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} (未生成)")
    
    return crawler.news_data

def show_system_info():
    """
    显示系统信息
    """
    print("\n" + "="*60)
    print("📋 智能新闻爬虫系统信息")
    print("="*60)
    
    features = [
        "🔸 基础爬虫: 快速新闻采集",
        "🔸 高级爬虫: 多线程 + 情感分析 + 可视化",
        "🔸 Web管理界面: 实时监控和控制",
        "🔸 数据存储: CSV, JSON, Excel, SQLite",
        "🔸 情感分析: 中文文本情感倾向分析",
        "🔸 关键词提取: 基于jieba分词的TF-IDF",
        "🔸 数据可视化: 图表和词云生成",
        "🔸 智能反爬: User-Agent轮换 + 代理支持",
        "🔸 断点续爬: 避免重复爬取",
        "🔸 实时监控: Web界面状态展示"
    ]
    
    print("\n🚀 核心功能:")
    for feature in features:
        print(f"   {feature}")
    
    print("\n🌐 Web界面访问:")
    print("   📱 本地访问: http://127.0.0.1:5000")
    print("   🖥️  网络访问: http://192.168.10.121:5000")
    
    print("\n📚 使用方法:")
    print("   1. 运行 python crawler_manager.py 启动Web服务")
    print("   2. 浏览器访问 http://127.0.0.1:5000")
    print("   3. 在Web界面中控制爬虫和查看数据")
    
    print("\n⚠️  注意事项:")
    print("   • 请遵守网站robots.txt协议")
    print("   • 控制爬取频率，避免对目标网站造成压力")
    print("   • 仅用于学习研究目的")

def main():
    """
    主演示函数
    """
    print("🎉 欢迎使用智能新闻爬虫系统演示")
    
    # 显示系统信息
    show_system_info()
    
    # 询问用户选择
    print("\n" + "="*60)
    print("请选择演示模式:")
    print("1. 基础爬虫演示")
    print("2. 高级爬虫演示")
    print("3. 完整演示（基础 + 高级）")
    print("4. 仅显示系统信息")
    print("="*60)
    
    try:
        choice = input("\n请输入选择 (1-4): ").strip()
        
        if choice == '1':
            demo_basic_crawler()
        elif choice == '2':
            demo_advanced_crawler()
        elif choice == '3':
            print("\n🎯 开始完整演示...")
            demo_basic_crawler()
            time.sleep(2)
            demo_advanced_crawler()
        elif choice == '4':
            print("\n✅ 系统信息已显示")
        else:
            print("\n❌ 无效选择，请重新运行程序")
            return
        
        print("\n" + "="*60)
        print("🎉 演示完成！")
        print("💡 提示: 运行 'python crawler_manager.py' 启动Web界面")
        print("🌐 然后访问 http://127.0.0.1:5000 查看完整功能")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n👋 演示已取消")
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")

if __name__ == '__main__':
    main()