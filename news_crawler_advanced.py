#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级新闻爬虫 - 功能丰富版本
功能：
1. 多线程并发爬取
2. 代理IP支持
3. User-Agent轮换
4. 新闻内容详情抓取
5. 情感分析
6. 关键词提取
7. 数据去重
8. 断点续爬
9. 实时监控
10. 多种数据存储格式
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import csv
import json
import sqlite3
from datetime import datetime, timedelta
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import re
from urllib.parse import urljoin, urlparse
import logging
from fake_useragent import UserAgent
import jieba
import jieba.analyse
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import pandas as pd
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('news_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class AdvancedNewsCrawler:
    def __init__(self, config=None):
        self.config = config or self.default_config()
        self.ua = UserAgent()
        self.session = requests.Session()
        self.crawled_urls = set()
        self.news_data = []
        self.lock = threading.Lock()
        
        # 初始化数据库
        self.init_database()
        
        # 创建数据目录
        for directory in ['news_data', 'charts', 'wordclouds']:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        # 加载已爬取的URL（断点续爬）
        self.load_crawled_urls()
        
        logging.info('高级新闻爬虫初始化完成')
    
    def default_config(self):
        return {
            'max_workers': 5,
            'request_delay': (1, 3),
            'timeout': 10,
            'max_retries': 3,
            'use_proxy': False,
            'proxy_list': [],
            'target_sites': [
                {
                    'name': '网易新闻',
                    'base_url': 'https://news.163.com/',
                    'list_selector': 'a',
                    'title_selector': '',
                    'content_selector': '.post_content_main, .post_text'
                },
                {
                    'name': '新浪新闻',
                    'base_url': 'https://news.sina.com.cn/',
                    'list_selector': 'a',
                    'title_selector': '',
                    'content_selector': '.article, .content'
                }
            ]
        }
    
    def init_database(self):
        """
        初始化SQLite数据库
        """
        self.db_path = 'news_data/news.db'
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                content TEXT,
                summary TEXT,
                pub_time TEXT,
                crawl_time TEXT,
                category TEXT,
                source TEXT,
                keywords TEXT,
                sentiment_score REAL,
                word_count INTEGER,
                url_hash TEXT UNIQUE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crawl_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                status TEXT,
                error_msg TEXT,
                crawl_time TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_crawled_urls(self):
        """
        加载已爬取的URL
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT url FROM news')
            self.crawled_urls = {row[0] for row in cursor.fetchall()}
            conn.close()
            logging.info(f'加载了 {len(self.crawled_urls)} 个已爬取的URL')
        except Exception as e:
            logging.error(f'加载已爬取URL失败: {e}')
    
    def get_headers(self):
        """
        获取随机请求头
        """
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def get_proxy(self):
        """
        获取代理
        """
        if self.config['use_proxy'] and self.config['proxy_list']:
            return random.choice(self.config['proxy_list'])
        return None
    
    def make_request(self, url, **kwargs):
        """
        发送HTTP请求（带重试机制）
        """
        for attempt in range(self.config['max_retries']):
            try:
                headers = self.get_headers()
                proxy = self.get_proxy()
                proxies = {'http': proxy, 'https': proxy} if proxy else None
                
                response = requests.get(
                    url,
                    headers=headers,
                    proxies=proxies,
                    timeout=self.config['timeout'],
                    **kwargs
                )
                
                if response.status_code == 200:
                    return response
                else:
                    logging.warning(f'请求失败，状态码: {response.status_code}, URL: {url}')
                    
            except Exception as e:
                logging.error(f'请求出错 (尝试 {attempt + 1}/{self.config["max_retries"]}): {e}')
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(random.uniform(1, 3))
        
        return None
    
    def extract_news_links(self, site_config, max_links=50):
        """
        提取新闻链接
        """
        response = self.make_request(site_config['base_url'])
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        
        # 查找所有链接
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # 处理相对链接
            if href.startswith('/'):
                href = urljoin(site_config['base_url'], href)
            
            # 过滤有效的新闻链接
            if (href.startswith('http') and 
                any(keyword in href for keyword in ['news', 'article', 'story']) and
                href not in self.crawled_urls):
                
                title = link.get_text(strip=True)
                if title and len(title) > 5:
                    links.append({
                        'url': href,
                        'title': title,
                        'source': site_config['name']
                    })
                    
                    if len(links) >= max_links:
                        break
        
        return links
    
    def extract_news_content(self, url, site_config):
        """
        提取新闻内容
        """
        response = self.make_request(url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取标题
        title_selectors = ['h1', '.title', '.headline', 'title']
        title = ''
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                break
        
        # 提取内容
        content = ''
        content_selectors = site_config['content_selector'].split(', ') if site_config['content_selector'] else [
            '.content', '.article-content', '.post-content', 'article', '.news-content'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 移除脚本和样式标签
                for script in content_elem(["script", "style"]):
                    script.decompose()
                content = content_elem.get_text(strip=True)
                break
        
        # 提取发布时间
        pub_time = ''
        time_selectors = ['.time', '.date', '.publish-time', '.pub-time']
        for selector in time_selectors:
            time_elem = soup.select_one(selector)
            if time_elem:
                pub_time = time_elem.get_text(strip=True)
                break
        
        # 提取摘要
        summary = content[:200] + '...' if len(content) > 200 else content
        
        return {
            'title': title,
            'url': url,
            'content': content,
            'summary': summary,
            'pub_time': pub_time,
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': site_config['name'],
            'word_count': len(content)
        }
    
    def analyze_sentiment(self, text):
        """
        简单的情感分析（基于关键词）
        """
        positive_words = ['好', '棒', '优秀', '成功', '胜利', '喜悦', '高兴', '满意', '赞', '支持']
        negative_words = ['坏', '差', '失败', '问题', '困难', '担心', '反对', '批评', '危险', '损失']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count + negative_count == 0:
            return 0.0
        
        return (positive_count - negative_count) / (positive_count + negative_count)
    
    def extract_keywords(self, text, top_k=10):
        """
        提取关键词
        """
        try:
            keywords = jieba.analyse.extract_tags(text, topK=top_k, withWeight=False)
            return ', '.join(keywords)
        except:
            return ''
    
    def save_to_database(self, news_item):
        """
        保存到数据库
        """
        try:
            # 计算URL哈希
            url_hash = hashlib.md5(news_item['url'].encode()).hexdigest()
            
            # 分析情感和关键词
            sentiment_score = self.analyze_sentiment(news_item['content'])
            keywords = self.extract_keywords(news_item['content'])
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO news 
                (title, url, content, summary, pub_time, crawl_time, source, 
                 keywords, sentiment_score, word_count, url_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                news_item['title'],
                news_item['url'],
                news_item['content'],
                news_item['summary'],
                news_item['pub_time'],
                news_item['crawl_time'],
                news_item['source'],
                keywords,
                sentiment_score,
                news_item['word_count'],
                url_hash
            ))
            
            conn.commit()
            conn.close()
            
            logging.info(f'保存新闻: {news_item["title"][:50]}...')
            
        except Exception as e:
            logging.error(f'保存到数据库失败: {e}')
    
    def crawl_single_news(self, news_link, site_config):
        """
        爬取单条新闻
        """
        try:
            # 添加延时
            time.sleep(random.uniform(*self.config['request_delay']))
            
            news_content = self.extract_news_content(news_link['url'], site_config)
            
            if news_content and news_content['content']:
                with self.lock:
                    self.crawled_urls.add(news_link['url'])
                    self.news_data.append(news_content)
                
                # 保存到数据库
                self.save_to_database(news_content)
                
                return news_content
            
        except Exception as e:
            logging.error(f'爬取新闻失败 {news_link["url"]}: {e}')
        
        return None
    
    def crawl_site(self, site_config, max_news=100):
        """
        爬取单个网站
        """
        logging.info(f'开始爬取网站: {site_config["name"]}')
        
        # 获取新闻链接
        news_links = self.extract_news_links(site_config, max_news)
        logging.info(f'找到 {len(news_links)} 个新闻链接')
        
        # 多线程爬取
        with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
            futures = [
                executor.submit(self.crawl_single_news, link, site_config)
                for link in news_links
            ]
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        logging.info(f'成功爬取: {result["title"][:50]}...')
                except Exception as e:
                    logging.error(f'线程执行失败: {e}')
    
    def generate_statistics(self):
        """
        生成统计报告
        """
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query('SELECT * FROM news', conn)
            conn.close()
            
            if df.empty:
                logging.warning('没有数据可供分析')
                return
            
            # 基本统计
            stats = {
                'total_news': len(df),
                'avg_word_count': df['word_count'].mean(),
                'avg_sentiment': df['sentiment_score'].mean(),
                'sources': df['source'].value_counts().to_dict(),
                'crawl_date_range': {
                    'start': df['crawl_time'].min(),
                    'end': df['crawl_time'].max()
                }
            }
            
            # 保存统计报告
            with open('news_data/statistics.json', 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
            
            logging.info(f'统计报告已生成: {stats}')
            
            # 生成图表
            self.generate_charts(df)
            
        except Exception as e:
            logging.error(f'生成统计失败: {e}')
    
    def generate_charts(self, df):
        """
        生成数据可视化图表
        """
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 1. 新闻来源分布
        plt.figure(figsize=(10, 6))
        source_counts = df['source'].value_counts()
        plt.pie(source_counts.values, labels=source_counts.index, autopct='%1.1f%%')
        plt.title('新闻来源分布')
        plt.savefig('charts/news_sources.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. 情感分析分布
        plt.figure(figsize=(10, 6))
        plt.hist(df['sentiment_score'], bins=20, alpha=0.7, color='skyblue')
        plt.xlabel('情感得分')
        plt.ylabel('新闻数量')
        plt.title('新闻情感分析分布')
        plt.savefig('charts/sentiment_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. 词云图
        all_keywords = ' '.join(df['keywords'].dropna())
        if all_keywords:
            wordcloud = WordCloud(
                font_path='simhei.ttf',  # 需要中文字体
                width=800, height=400,
                background_color='white'
            ).generate(all_keywords)
            
            plt.figure(figsize=(12, 6))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            plt.title('新闻关键词词云')
            plt.savefig('wordclouds/keywords_wordcloud.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        logging.info('图表生成完成')
    
    def export_data(self):
        """
        导出数据到多种格式
        """
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query('SELECT * FROM news', conn)
            conn.close()
            
            if df.empty:
                logging.warning('没有数据可导出')
                return
            
            # 导出到CSV
            df.to_csv('news_data/news_export.csv', index=False, encoding='utf-8')
            
            # 导出到Excel
            df.to_excel('news_data/news_export.xlsx', index=False)
            
            # 导出到JSON
            df.to_json('news_data/news_export.json', orient='records', force_ascii=False, indent=2)
            
            logging.info('数据导出完成')
            
        except Exception as e:
            logging.error(f'数据导出失败: {e}')
    
    def run(self, max_news_per_site=50):
        """
        运行爬虫
        """
        logging.info('=== 高级新闻爬虫开始运行 ===')
        
        start_time = time.time()
        
        # 爬取各个网站
        for site_config in self.config['target_sites']:
            try:
                self.crawl_site(site_config, max_news_per_site)
            except Exception as e:
                logging.error(f'爬取网站 {site_config["name"]} 失败: {e}')
        
        end_time = time.time()
        
        logging.info(f'爬取完成，耗时: {end_time - start_time:.2f}秒')
        logging.info(f'总共爬取 {len(self.news_data)} 条新闻')
        
        # 生成统计和导出数据
        self.generate_statistics()
        self.export_data()
        
        logging.info('=== 爬虫运行结束 ===')

def main():
    """
    主函数
    """
    # 配置
    config = {
        'max_workers': 3,
        'request_delay': (1, 2),
        'timeout': 15,
        'max_retries': 3,
        'use_proxy': False,
        'proxy_list': [],
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
    
    # 创建爬虫实例
    crawler = AdvancedNewsCrawler(config)
    
    # 运行爬虫
    crawler.run(max_news_per_site=30)

if __name__ == '__main__':
    main()