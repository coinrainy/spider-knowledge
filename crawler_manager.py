# -*- coding: utf-8 -*-
"""
爬虫管理器 - 统一管理基础和高级爬虫
功能：
1. 统一配置管理
2. 爬虫任务调度
3. 数据统一处理
4. 实时监控
5. Web API接口
"""

import json
import os
import time
import threading
from datetime import datetime
import sqlite3
import pandas as pd
from flask import Flask, render_template, jsonify, request
import logging
from news_crawler_basic import BasicNewsCrawler
from news_crawler_advanced import AdvancedNewsCrawler

class CrawlerManager:
    def __init__(self, config_file='crawler_config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        self.basic_crawler = None
        self.advanced_crawler = None
        self.crawl_status = {
            'is_running': False,
            'current_task': None,
            'progress': 0,
            'total_news': 0,
            'start_time': None,
            'end_time': None,
            'errors': []
        }
        self.lock = threading.Lock()
        
        # 初始化数据库
        self.init_database()
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('crawler_manager.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        logging.info('爬虫管理器初始化完成')
    
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f'加载配置文件失败: {e}')
            return self.default_config()
    
    def default_config(self):
        """默认配置"""
        return {
            "basic_crawler": {
                "settings": {
                    "request_delay": [1, 3],
                    "timeout": 10,
                    "max_retries": 3,
                    "max_pages": 3
                }
            },
            "advanced_crawler": {
                "settings": {
                    "max_workers": 5,
                    "request_delay": [1, 3],
                    "timeout": 15,
                    "max_retries": 3,
                    "max_news_per_site": 100
                }
            }
        }
    
    def init_database(self):
        """初始化数据库"""
        if not os.path.exists('news_data'):
            os.makedirs('news_data')
        
        self.db_path = 'news_data/crawler_manager.db'
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建任务记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crawl_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                status TEXT,
                total_news INTEGER,
                success_count INTEGER,
                error_count INTEGER,
                config TEXT
            )
        ''')
        
        # 创建新闻汇总表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                content TEXT,
                summary TEXT,
                pub_time TEXT,
                crawl_time TEXT,
                source TEXT,
                category TEXT,
                keywords TEXT,
                sentiment_score REAL,
                word_count INTEGER,
                crawler_type TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_basic_crawl(self, categories=['news'], max_pages=3):
        """启动基础爬虫"""
        def crawl_task():
            try:
                with self.lock:
                    self.crawl_status['is_running'] = True
                    self.crawl_status['current_task'] = '基础爬虫'
                    self.crawl_status['start_time'] = datetime.now().isoformat()
                    self.crawl_status['errors'] = []
                
                self.basic_crawler = BasicNewsCrawler()
                news_data = self.basic_crawler.crawl(categories, max_pages)
                
                # 保存到汇总数据库
                self.save_to_summary_db(news_data, 'basic')
                
                with self.lock:
                    self.crawl_status['is_running'] = False
                    self.crawl_status['end_time'] = datetime.now().isoformat()
                    self.crawl_status['total_news'] = len(news_data)
                
                logging.info(f'基础爬虫完成，共爬取 {len(news_data)} 条新闻')
                
            except Exception as e:
                with self.lock:
                    self.crawl_status['is_running'] = False
                    self.crawl_status['errors'].append(str(e))
                logging.error(f'基础爬虫执行失败: {e}')
        
        thread = threading.Thread(target=crawl_task)
        thread.daemon = True
        thread.start()
        
        return {'status': 'started', 'message': '基础爬虫已启动'}
    
    def start_advanced_crawl(self, max_news_per_site=50):
        """启动高级爬虫"""
        def crawl_task():
            try:
                with self.lock:
                    self.crawl_status['is_running'] = True
                    self.crawl_status['current_task'] = '高级爬虫'
                    self.crawl_status['start_time'] = datetime.now().isoformat()
                    self.crawl_status['errors'] = []
                
                # 获取完整的高级爬虫配置
                config = self.config.get('advanced_crawler', {})
                self.advanced_crawler = AdvancedNewsCrawler(config)
                self.advanced_crawler.run(max_news_per_site)
                
                # 从高级爬虫数据库读取数据并保存到汇总数据库
                self.sync_advanced_data()
                
                with self.lock:
                    self.crawl_status['is_running'] = False
                    self.crawl_status['end_time'] = datetime.now().isoformat()
                    self.crawl_status['total_news'] = len(self.advanced_crawler.news_data)
                
                logging.info(f'高级爬虫完成，共爬取 {len(self.advanced_crawler.news_data)} 条新闻')
                
            except Exception as e:
                with self.lock:
                    self.crawl_status['is_running'] = False
                    self.crawl_status['errors'].append(str(e))
                logging.error(f'高级爬虫执行失败: {e}')
        
        thread = threading.Thread(target=crawl_task)
        thread.daemon = True
        thread.start()
        
        return {'status': 'started', 'message': '高级爬虫已启动'}
    
    def save_to_summary_db(self, news_data, crawler_type):
        """保存到汇总数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for news in news_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO news_summary 
                    (title, url, content, summary, pub_time, crawl_time, source, 
                     category, keywords, sentiment_score, word_count, crawler_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    news.get('title', ''),
                    news.get('link', news.get('url', '')),
                    news.get('content', ''),
                    news.get('summary', ''),
                    news.get('pub_time', ''),
                    news.get('crawl_time', ''),
                    news.get('source', ''),
                    news.get('category', ''),
                    news.get('keywords', ''),
                    news.get('sentiment_score', 0.0),
                    news.get('word_count', 0),
                    crawler_type
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f'保存到汇总数据库失败: {e}')
    
    def sync_advanced_data(self):
        """同步高级爬虫数据"""
        try:
            # 从高级爬虫数据库读取数据
            advanced_db = 'news_data/news.db'
            if os.path.exists(advanced_db):
                conn_advanced = sqlite3.connect(advanced_db)
                df = pd.read_sql_query('SELECT * FROM news', conn_advanced)
                conn_advanced.close()
                
                # 保存到汇总数据库
                conn_summary = sqlite3.connect(self.db_path)
                for _, row in df.iterrows():
                    cursor = conn_summary.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO news_summary 
                        (title, url, content, summary, pub_time, crawl_time, source, 
                         keywords, sentiment_score, word_count, crawler_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['title'],
                        row['url'],
                        row['content'],
                        row['summary'],
                        row['pub_time'],
                        row['crawl_time'],
                        row['source'],
                        row['keywords'],
                        row['sentiment_score'],
                        row['word_count'],
                        'advanced'
                    ))
                
                conn_summary.commit()
                conn_summary.close()
                
        except Exception as e:
            logging.error(f'同步高级爬虫数据失败: {e}')
    
    def get_crawl_status(self):
        """获取爬取状态"""
        with self.lock:
            return self.crawl_status.copy()
    
    def get_news_data(self, limit=100, offset=0, source=None, crawler_type=None):
        """获取新闻数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = 'SELECT * FROM news_summary WHERE 1=1'
            params = []
            
            if source:
                query += ' AND source = ?'
                params.append(source)
            
            if crawler_type:
                query += ' AND crawler_type = ?'
                params.append(crawler_type)
            
            query += ' ORDER BY crawl_time DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            return df.to_dict('records')
            
        except Exception as e:
            logging.error(f'获取新闻数据失败: {e}')
            return []
    
    def get_statistics(self):
        """获取统计数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 基本统计
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM news_summary')
            total_news = cursor.fetchone()[0]
            
            cursor.execute('SELECT crawler_type, COUNT(*) FROM news_summary GROUP BY crawler_type')
            crawler_stats = dict(cursor.fetchall())
            
            cursor.execute('SELECT source, COUNT(*) FROM news_summary GROUP BY source')
            source_stats = dict(cursor.fetchall())
            
            cursor.execute('SELECT AVG(sentiment_score) FROM news_summary WHERE sentiment_score IS NOT NULL')
            avg_sentiment = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT AVG(word_count) FROM news_summary WHERE word_count > 0')
            avg_word_count = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_news': total_news,
                'crawler_stats': crawler_stats,
                'source_stats': source_stats,
                'avg_sentiment': round(avg_sentiment, 3),
                'avg_word_count': round(avg_word_count, 0)
            }
            
        except Exception as e:
            logging.error(f'获取统计数据失败: {e}')
            return {}
    
    def stop_crawl(self):
        """停止爬取"""
        with self.lock:
            if self.crawl_status['is_running']:
                self.crawl_status['is_running'] = False
                self.crawl_status['end_time'] = datetime.now().isoformat()
                return {'status': 'stopped', 'message': '爬虫已停止'}
            else:
                return {'status': 'not_running', 'message': '爬虫未在运行'}

# 创建全局管理器实例
crawler_manager = CrawlerManager()

# Flask Web应用
app = Flask(__name__)

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """获取爬取状态API"""
    return jsonify(crawler_manager.get_crawl_status())

@app.route('/api/statistics')
def api_statistics():
    """获取统计数据API"""
    return jsonify(crawler_manager.get_statistics())

@app.route('/api/news')
def api_news():
    """获取新闻数据API"""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    source = request.args.get('source')
    crawler_type = request.args.get('crawler_type')
    
    news_data = crawler_manager.get_news_data(limit, offset, source, crawler_type)
    return jsonify(news_data)

@app.route('/api/start_basic', methods=['POST'])
def api_start_basic():
    """启动基础爬虫API"""
    data = request.get_json() or {}
    categories = data.get('categories', ['news'])
    max_pages = data.get('max_pages', 3)
    
    result = crawler_manager.start_basic_crawl(categories, max_pages)
    return jsonify(result)

@app.route('/api/start_advanced', methods=['POST'])
def api_start_advanced():
    """启动高级爬虫API"""
    data = request.get_json() or {}
    max_news = data.get('max_news_per_site', 50)
    
    result = crawler_manager.start_advanced_crawl(max_news)
    return jsonify(result)

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """停止爬虫API"""
    result = crawler_manager.stop_crawl()
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)