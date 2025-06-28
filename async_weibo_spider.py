# -*- coding: utf-8 -*-
"""
异步微博爬虫程序
功能：使用异步方式爬取微博文章和评论，并进行数据分析
"""

import asyncio
import aiohttp
import json
import time
import random
import re
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import logging
from bs4 import BeautifulSoup
from aiohttp import ClientSession, TCPConnector
from fake_useragent import UserAgent
import jieba
import jieba.analyse
from wordcloud import WordCloud
from collections import Counter
import numpy as np
from PIL import Image
import matplotlib.font_manager as fm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='async_weibo_spider.log'
)
logger = logging.getLogger('async_weibo_spider')

# 添加控制台输出
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)

class AsyncWeiboSpider:
    def __init__(self, cookie=None, max_concurrency=5):
        """
        初始化异步爬虫
        :param cookie: 微博登录后的cookie字符串
        :param max_concurrency: 最大并发请求数
        """
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.ua = UserAgent()
        
        # 基础请求头
        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://weibo.com/',
            'Connection': 'keep-alive'
        }
        
        # 如果提供了cookie，则添加到headers中
        if cookie:
            self.headers['Cookie'] = cookie
        
        # 创建数据存储目录
        self.data_dir = 'weibo_data'
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # 创建图表存储目录
        self.charts_dir = os.path.join(self.data_dir, 'charts')
        if not os.path.exists(self.charts_dir):
            os.makedirs(self.charts_dir)
    
    async def get_random_ua(self):
        """
        获取随机User-Agent
        :return: User-Agent字符串
        """
        return self.ua.random
    
    async def save_cookies(self, cookies, filename='weibo_cookies.json'):
        """
        保存cookies
        :param cookies: cookies字典
        :param filename: 保存的文件名
        """
        with open(os.path.join(self.data_dir, filename), 'w') as f:
            json.dump(cookies, f)
        logger.info(f'Cookies saved to {filename}')
    
    async def load_cookies(self, filename='weibo_cookies.json'):
        """
        加载cookies
        :param filename: cookies文件名
        :return: cookies字典或None
        """
        try:
            with open(os.path.join(self.data_dir, filename), 'r') as f:
                cookies = json.load(f)
            logger.info(f'Cookies loaded from {filename}')
            return cookies
        except Exception as e:
            logger.error(f'Failed to load cookies: {e}')
            return None
    
    async def make_request(self, session, url, method='GET', params=None, data=None, json_data=None):
        """
        发送HTTP请求
        :param session: aiohttp会话
        :param url: 请求URL
        :param method: 请求方法
        :param params: URL参数
        :param data: 表单数据
        :param json_data: JSON数据
        :return: 响应数据
        """
        async with self.semaphore:
            # 添加随机延时，避免请求过于频繁
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # 更新User-Agent
            headers = self.headers.copy()
            headers['User-Agent'] = await self.get_random_ua()
            
            try:
                if method.upper() == 'GET':
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            logger.warning(f'Request failed: {url}, status: {response.status}')
                            return None
                elif method.upper() == 'POST':
                    async with session.post(url, headers=headers, params=params, data=data, json=json_data) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            logger.warning(f'Request failed: {url}, status: {response.status}')
                            return None
            except Exception as e:
                logger.error(f'Request error: {url}, error: {e}')
                return None
    
    async def check_login_status(self, session):
        """
        检查是否已登录
        :param session: aiohttp会话
        :return: 是否已登录
        """
        try:
            # 访问个人主页API
            url = 'https://weibo.com/ajax/profile/info'
            data = await self.make_request(session, url)
            
            # 如果返回的数据中包含用户ID，则说明已登录
            if data and 'data' in data and 'user' in data['data']:
                logger.info(f"Login check successful, user: {data['data']['user']['screen_name']}")
                return True
            else:
                logger.info("Not logged in")
                return False
        except Exception as e:
            logger.error(f'Login check failed: {e}')
            return False
    
    async def get_weibo_by_user(self, session, user_id, count=20):
        """
        获取指定用户的微博列表
        :param session: aiohttp会话
        :param user_id: 用户ID
        :param count: 获取的微博数量
        :return: 微博列表
        """
        try:
            url = f'https://weibo.com/ajax/statuses/mymblog'
            params = {
                'uid': user_id,
                'page': 1,
                'feature': 0,
                'count': count
            }
            
            data = await self.make_request(session, url, params=params)
            
            if data and 'data' in data and 'list' in data['data']:
                weibo_list = data['data']['list']
                logger.info(f'Got {len(weibo_list)} weibos from user {user_id}')
                
                # 保存微博列表
                filename = f'user_{user_id}_weibos.json'
                with open(os.path.join(self.data_dir, filename), 'w', encoding='utf-8') as f:
                    json.dump(weibo_list, f, ensure_ascii=False, indent=4)
                
                return weibo_list
            else:
                logger.warning(f'No weibos found for user {user_id}')
                return []
        except Exception as e:
            logger.error(f'Failed to get weibos for user {user_id}: {e}')
            return []
    
    async def get_weibo_by_topic(self, session, topic, count=20):
        """
        获取指定话题的微博列表
        :param session: aiohttp会话
        :param topic: 话题关键词
        :param count: 获取的微博数量
        :return: 微博列表
        """
        try:
            # 对话题进行URL编码
            encoded_topic = topic.replace('#', '%23')
            url = 'https://m.weibo.cn/api/container/getIndex'
            params = {
                'containerid': f'100103type=1&q={encoded_topic}',
                'page_type': 'searchall'
            }
            
            data = await self.make_request(session, url, params=params)
            
            if data and 'data' in data and 'cards' in data['data']:
                weibo_cards = [card for card in data['data']['cards'] if card.get('card_type') == 9]
                logger.info(f'Got {len(weibo_cards)} weibos for topic {topic}')
                
                # 保存话题微博列表
                filename = f'topic_{topic}_weibos.json'
                with open(os.path.join(self.data_dir, filename), 'w', encoding='utf-8') as f:
                    json.dump(weibo_cards, f, ensure_ascii=False, indent=4)
                
                return weibo_cards
            else:
                logger.warning(f'No weibos found for topic {topic}')
                return []
        except Exception as e:
            logger.error(f'Failed to get weibos for topic {topic}: {e}')
            return []
    
    async def get_weibo_comments(self, session, weibo_id, count=20):
        """
        获取指定微博的评论
        :param session: aiohttp会话
        :param weibo_id: 微博ID
        :param count: 获取的评论数量
        :return: 评论列表
        """
        try:
            url = 'https://weibo.com/ajax/statuses/buildComments'
            params = {
                'flow': 0,
                'is_reload': 1,
                'id': weibo_id,
                'is_show_bulletin': 2,
                'is_mix': 0,
                'count': count,
                'uid': ''
            }
            
            data = await self.make_request(session, url, params=params)
            
            if data and 'data' in data:
                comments = data['data']
                logger.info(f'Got {len(comments)} comments for weibo {weibo_id}')
                
                # 保存评论列表
                filename = f'weibo_{weibo_id}_comments.json'
                with open(os.path.join(self.data_dir, filename), 'w', encoding='utf-8') as f:
                    json.dump(comments, f, ensure_ascii=False, indent=4)
                
                return comments
            else:
                logger.warning(f'No comments found for weibo {weibo_id}')
                return []
        except Exception as e:
            logger.error(f'Failed to get comments for weibo {weibo_id}: {e}')
            return []
    
    async def get_comment_replies(self, session, comment_id, count=20):
        """
        获取评论的回复
        :param session: aiohttp会话
        :param comment_id: 评论ID
        :param count: 获取的回复数量
        :return: 回复列表
        """
        try:
            url = 'https://weibo.com/ajax/statuses/buildComments'
            params = {
                'flow': 0,
                'is_reload': 1,
                'id': comment_id,
                'is_show_bulletin': 2,
                'is_mix': 0,
                'count': count,
                'uid': '',
                'fetch_level': 1
            }
            
            data = await self.make_request(session, url, params=params)
            
            if data and 'data' in data:
                replies = data['data']
                logger.info(f'Got {len(replies)} replies for comment {comment_id}')
                
                # 保存回复列表
                filename = f'comment_{comment_id}_replies.json'
                with open(os.path.join(self.data_dir, filename), 'w', encoding='utf-8') as f:
                    json.dump(replies, f, ensure_ascii=False, indent=4)
                
                return replies
            else:
                logger.warning(f'No replies found for comment {comment_id}')
                return []
        except Exception as e:
            logger.error(f'Failed to get replies for comment {comment_id}: {e}')
            return []
    
    def parse_weibo_content(self, weibo):
        """
        解析微博内容，提取文本、图片、视频等信息
        :param weibo: 微博数据
        :return: 解析后的微博数据
        """
        try:
            # 处理不同来源的微博数据结构
            if 'mblog' in weibo:
                weibo = weibo['mblog']
            
            parsed_weibo = {
                'id': weibo.get('id', ''),
                'mid': weibo.get('mid', ''),  # 微博MID，用于获取评论
                'user_id': weibo.get('user', {}).get('id', '') if 'user' in weibo else '',
                'screen_name': weibo.get('user', {}).get('screen_name', '') if 'user' in weibo else '',
                'created_at': weibo.get('created_at', ''),
                'text': re.sub(r'<[^>]+>', '', weibo.get('text', '')),  # 移除HTML标签
                'reposts_count': weibo.get('reposts_count', 0),
                'comments_count': weibo.get('comments_count', 0),
                'attitudes_count': weibo.get('attitudes_count', 0),  # 点赞数
                'source': weibo.get('source', ''),
            }
            
            # 提取图片URL
            if 'pic_ids' in weibo and weibo['pic_ids']:
                parsed_weibo['pic_urls'] = [f"https://wx1.sinaimg.cn/large/{pic_id}.jpg" for pic_id in weibo['pic_ids']]
            else:
                parsed_weibo['pic_urls'] = []
            
            # 提取视频URL
            if 'page_info' in weibo and weibo['page_info'].get('type') == 'video':
                parsed_weibo['video_url'] = weibo['page_info'].get('media_info', {}).get('stream_url', '')
            else:
                parsed_weibo['video_url'] = ''
            
            # 提取地理位置
            if 'geo' in weibo and weibo['geo']:
                parsed_weibo['location'] = weibo['geo'].get('detail', {}).get('address', '')
            else:
                parsed_weibo['location'] = ''
            
            return parsed_weibo
        except Exception as e:
            logger.error(f'Failed to parse weibo: {e}')
            return {}
    
    def parse_comment(self, comment):
        """
        解析评论内容
        :param comment: 评论数据
        :return: 解析后的评论数据
        """
        try:
            parsed_comment = {
                'id': comment.get('id', ''),
                'user_id': comment.get('user', {}).get('id', ''),
                'screen_name': comment.get('user', {}).get('screen_name', ''),
                'created_at': comment.get('created_at', ''),
                'text': re.sub(r'<[^>]+>', '', comment.get('text', '')),  # 移除HTML标签
                'like_count': comment.get('like_count', 0),
                'reply_count': comment.get('total_number', 0),
            }
            return parsed_comment
        except Exception as e:
            logger.error(f'Failed to parse comment: {e}')
            return {}
    
    async def save_to_csv(self, data, filename):
        """
        将数据保存为CSV文件
        :param data: 数据列表
        :param filename: 文件名
        """
        try:
            if not data:
                logger.warning(f'No data to save to {filename}')
                return
            
            df = pd.DataFrame(data)
            file_path = os.path.join(self.data_dir, filename)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            logger.info(f'Data saved to {file_path}')
        except Exception as e:
            logger.error(f'Failed to save data to CSV: {e}')
    
    async def crawl_user_weibos_and_comments(self, user_id, weibo_count=20, comment_count=20, include_replies=False):
        """
        爬取用户的微博及其评论
        :param user_id: 用户ID
        :param weibo_count: 爬取的微博数量
        :param comment_count: 每条微博爬取的评论数量
        :param include_replies: 是否包含评论的回复
        :return: (微博列表, 评论列表)
        """
        async with aiohttp.ClientSession(connector=TCPConnector(ssl=False)) as session:
            # 获取用户微博列表
            weibos = await self.get_weibo_by_user(session, user_id, weibo_count)
            
            if not weibos:
                logger.warning(f'No weibos found for user {user_id}')
                return [], []
            
            # 解析微博内容
            parsed_weibos = []
            all_comments = []
            
            # 创建评论爬取任务
            comment_tasks = []
            
            for weibo in weibos:
                # 解析微博
                parsed_weibo = self.parse_weibo_content(weibo)
                if parsed_weibo:
                    parsed_weibos.append(parsed_weibo)
                
                # 获取评论
                weibo_id = weibo.get('id', '')
                if weibo_id:
                    # 创建评论爬取任务
                    task = asyncio.create_task(self.get_weibo_comments(session, weibo_id, comment_count))
                    comment_tasks.append((weibo_id, task))
            
            # 等待所有评论爬取任务完成
            for weibo_id, task in comment_tasks:
                comments = await task
                
                for comment in comments:
                    parsed_comment = self.parse_comment(comment)
                    if parsed_comment:
                        # 添加微博ID，关联评论和微博
                        parsed_comment['weibo_id'] = weibo_id
                        all_comments.append(parsed_comment)
                        
                        # 如果需要获取评论的回复
                        if include_replies and parsed_comment.get('reply_count', 0) > 0:
                            comment_id = comment.get('id', '')
                            if comment_id:
                                # 添加随机延时，避免请求过于频繁
                                await asyncio.sleep(random.uniform(0.5, 1.5))
                                
                                replies = await self.get_comment_replies(session, comment_id, 20)
                                for reply in replies:
                                    parsed_reply = self.parse_comment(reply)
                                    if parsed_reply:
                                        # 添加微博ID和父评论ID，关联回复、评论和微博
                                        parsed_reply['weibo_id'] = weibo_id
                                        parsed_reply['parent_comment_id'] = comment_id
                                        all_comments.append(parsed_reply)
            
            # 保存数据
            await self.save_to_csv(parsed_weibos, f'user_{user_id}_weibos.csv')
            await self.save_to_csv(all_comments, f'user_{user_id}_comments.csv')
            
            return parsed_weibos, all_comments
    
    async def crawl_topic_weibos_and_comments(self, topic, weibo_count=20, comment_count=20, include_replies=False):
        """
        爬取话题相关的微博及其评论
        :param topic: 话题关键词
        :param weibo_count: 爬取的微博数量
        :param comment_count: 每条微博爬取的评论数量
        :param include_replies: 是否包含评论的回复
        :return: (微博列表, 评论列表)
        """
        async with aiohttp.ClientSession(connector=TCPConnector(ssl=False)) as session:
            # 获取话题微博列表
            weibo_cards = await self.get_weibo_by_topic(session, topic, weibo_count)
            
            if not weibo_cards:
                logger.warning(f'No weibos found for topic {topic}')
                return [], []
            
            # 解析微博内容
            parsed_weibos = []
            all_comments = []
            
            # 创建评论爬取任务
            comment_tasks = []
            
            for card in weibo_cards:
                if 'mblog' in card:
                    weibo = card['mblog']
                    
                    # 解析微博
                    parsed_weibo = self.parse_weibo_content(weibo)
                    if parsed_weibo:
                        # 添加话题标记
                        parsed_weibo['topic'] = topic
                        parsed_weibos.append(parsed_weibo)
                    
                    # 获取评论
                    weibo_id = weibo.get('id', '')
                    if weibo_id:
                        # 创建评论爬取任务
                        task = asyncio.create_task(self.get_weibo_comments(session, weibo_id, comment_count))
                        comment_tasks.append((weibo_id, task))
            
            # 等待所有评论爬取任务完成
            for weibo_id, task in comment_tasks:
                comments = await task
                
                for comment in comments:
                    parsed_comment = self.parse_comment(comment)
                    if parsed_comment:
                        # 添加微博ID和话题，关联评论、微博和话题
                        parsed_comment['weibo_id'] = weibo_id
                        parsed_comment['topic'] = topic
                        all_comments.append(parsed_comment)
                        
                        # 如果需要获取评论的回复
                        if include_replies and parsed_comment.get('reply_count', 0) > 0:
                            comment_id = comment.get('id', '')
                            if comment_id:
                                # 添加随机延时，避免请求过于频繁
                                await asyncio.sleep(random.uniform(0.5, 1.5))
                                
                                replies = await self.get_comment_replies(session, comment_id, 20)
                                for reply in replies:
                                    parsed_reply = self.parse_comment(reply)
                                    if parsed_reply:
                                        # 添加微博ID、父评论ID和话题，关联回复、评论、微博和话题
                                        parsed_reply['weibo_id'] = weibo_id
                                        parsed_reply['parent_comment_id'] = comment_id
                                        parsed_reply['topic'] = topic
                                        all_comments.append(parsed_reply)
            
            # 保存数据
            await self.save_to_csv(parsed_weibos, f'topic_{topic}_weibos.csv')
            await self.save_to_csv(all_comments, f'topic_{topic}_comments.csv')
            
            return parsed_weibos, all_comments
    
    def analyze_sentiment(self, text):
        """
        简单的情感分析，基于关键词匹配
        :param text: 文本内容
        :return: 情感得分（-1到1之间，负面到正面）
        """
        # 这里使用简单的关键词匹配方法，实际应用中可以使用更复杂的情感分析模型
        positive_words = ['喜欢', '赞', '好', '棒', '支持', '漂亮', '优秀', '开心', '感谢', '爱', 
                         '棒棒', '厉害', '牛', '强', '赞同', '欣赏', '满意', '期待', '祝福', '加油']
        negative_words = ['不喜欢', '差', '烂', '讨厌', '失望', '垃圾', '难看', '恶心', '讨厌', '恨', 
                         '坑', '弱', '反对', '批评', '不满', '担心', '诅咒', '放弃', '可怕', '糟糕']
        
        # 计算情感得分
        score = 0
        for word in positive_words:
            if word in text:
                score += 1
        for word in negative_words:
            if word in text:
                score -= 1
        
        # 归一化到-1到1之间
        if score > 0:
            return min(score / 5, 1)  # 最大为1
        elif score < 0:
            return max(score / 5, -1)  # 最小为-1
        else:
            return 0  # 中性
    
    def extract_keywords(self, text, topK=20):
        """
        提取文本关键词
        :param text: 文本内容
        :param topK: 提取的关键词数量
        :return: 关键词列表
        """
        # 使用jieba提取关键词
        keywords = jieba.analyse.extract_tags(text, topK=topK)
        return keywords
    
    def generate_wordcloud(self, text, output_file, mask_path=None, background_color='white'):
        """
        生成词云图
        :param text: 文本内容
        :param output_file: 输出文件路径
        :param mask_path: 蒙版图片路径
        :param background_color: 背景颜色
        """
        try:
            # 分词
            words = jieba.cut(text)
            words_space = ' '.join(words)
            
            # 设置字体，解决中文显示问题
            font_path = 'C:\Windows\Fonts\simhei.ttf'  # Windows系统黑体
            
            # 如果提供了蒙版图片，则使用蒙版
            if mask_path and os.path.exists(mask_path):
                mask = np.array(Image.open(mask_path))
                wc = WordCloud(font_path=font_path, background_color=background_color, mask=mask, max_words=200, width=800, height=400)
            else:
                wc = WordCloud(font_path=font_path, background_color=background_color, max_words=200, width=800, height=400)
            
            # 生成词云
            wc.generate(words_space)
            
            # 保存图片
            wc.to_file(output_file)
            logger.info(f'Word cloud saved to {output_file}')
        except Exception as e:
            logger.error(f'Failed to generate word cloud: {e}')
    
    async def analyze_weibo_data(self, weibos, comments, output_prefix):
        """
        分析微博数据，生成可视化图表
        :param weibos: 微博列表
        :param comments: 评论列表
        :param output_prefix: 输出文件前缀
        """
        try:
            if not weibos or not comments:
                logger.warning('No data to analyze')
                return
            
            # 1. 情感分析
            # 为微博和评论添加情感得分
            for weibo in weibos:
                weibo['sentiment'] = self.analyze_sentiment(weibo.get('text', ''))
            
            for comment in comments:
                comment['sentiment'] = self.analyze_sentiment(comment.get('text', ''))
            
            # 计算平均情感得分
            weibo_sentiment = sum(w.get('sentiment', 0) for w in weibos) / len(weibos) if weibos else 0
            comment_sentiment = sum(c.get('sentiment', 0) for c in comments) / len(comments) if comments else 0
            
            # 绘制情感分析柱状图
            plt.figure(figsize=(10, 6))
            plt.bar(['微博', '评论'], [weibo_sentiment, comment_sentiment], color=['blue', 'orange'])
            plt.title('微博与评论的平均情感得分')
            plt.ylabel('情感得分 (-1到1)')
            plt.axhline(y=0, color='r', linestyle='-', alpha=0.3)  # 添加零线
            plt.savefig(os.path.join(self.charts_dir, f'{output_prefix}_sentiment.png'))
            plt.close()
            
            # 2. 词频分析
            # 合并所有微博文本
            all_weibo_text = ' '.join([w.get('text', '') for w in weibos])
            all_comment_text = ' '.join([c.get('text', '') for c in comments])
            
            # 生成微博词云
            if all_weibo_text:
                self.generate_wordcloud(
                    all_weibo_text, 
                    os.path.join(self.charts_dir, f'{output_prefix}_weibo_wordcloud.png')
                )
            
            # 生成评论词云
            if all_comment_text:
                self.generate_wordcloud(
                    all_comment_text, 
                    os.path.join(self.charts_dir, f'{output_prefix}_comment_wordcloud.png')
                )
            
            # 3. 互动分析
            # 提取互动数据
            reposts = [w.get('reposts_count', 0) for w in weibos]
            comments_count = [w.get('comments_count', 0) for w in weibos]
            likes = [w.get('attitudes_count', 0) for w in weibos]
            
            # 计算平均互动数据
            avg_reposts = sum(reposts) / len(reposts) if reposts else 0
            avg_comments = sum(comments_count) / len(comments_count) if comments_count else 0
            avg_likes = sum(likes) / len(likes) if likes else 0
            
            # 绘制互动分析柱状图
            plt.figure(figsize=(10, 6))
            plt.bar(['转发', '评论', '点赞'], [avg_reposts, avg_comments, avg_likes], color=['blue', 'green', 'red'])
            plt.title('微博平均互动数据')
            plt.ylabel('平均数量')
            plt.savefig(os.path.join(self.charts_dir, f'{output_prefix}_interaction.png'))
            plt.close()
            
            # 4. 时间分布分析
            # 提取发布时间
            publish_times = []
            for weibo in weibos:
                try:
                    # 微博时间格式可能多样，这里简化处理
                    time_str = weibo.get('created_at', '')
                    if 'ago' in time_str or '前' in time_str:  # 处理"xx分钟前"格式
                        publish_times.append(datetime.now())
                    else:
                        # 尝试解析时间
                        dt = pd.to_datetime(time_str)
                        publish_times.append(dt)
                except:
                    continue
            
            if publish_times:
                # 转换为小时
                hours = [dt.hour for dt in publish_times]
                
                # 统计每小时发布数量
                hour_counts = Counter(hours)
                
                # 绘制时间分布图
                plt.figure(figsize=(12, 6))
                plt.bar(range(24), [hour_counts.get(h, 0) for h in range(24)], color='purple')
                plt.title('微博发布时间分布')
                plt.xlabel('小时')
                plt.ylabel('发布数量')
                plt.xticks(range(24))
                plt.savefig(os.path.join(self.charts_dir, f'{output_prefix}_time_distribution.png'))
                plt.close()
            
            logger.info(f'Data analysis completed for {output_prefix}')
        except Exception as e:
            logger.error(f'Failed to analyze data: {e}')

# 使用示例
async def main():
    # 创建爬虫实例
    # 如果有cookie，可以传入cookie参数
    spider = AsyncWeiboSpider()
    
    # 尝试加载已保存的cookies
    cookies = await spider.load_cookies()
    if cookies:
        async with aiohttp.ClientSession(connector=TCPConnector(ssl=False)) as session:
            # 检查登录状态
            if await spider.check_login_status(session):
                print("已登录，开始爬取数据")
                
                # 爬取指定用户的微博和评论
                # 这里需要替换为实际的用户ID
                user_id = '1669879400'  # 例如：1669879400是微博官方账号
                weibos, comments = await spider.crawl_user_weibos_and_comments(
                    user_id, weibo_count=10, comment_count=20, include_replies=True
                )
                
                # 分析用户微博数据
                await spider.analyze_weibo_data(weibos, comments, f'user_{user_id}')
                
                # 爬取指定话题的微博和评论
                topic = '热门话题'  # 替换为实际要爬取的话题
                weibos, comments = await spider.crawl_topic_weibos_and_comments(
                    topic, weibo_count=10, comment_count=20, include_replies=True
                )
                
                # 分析话题微博数据
                await spider.analyze_weibo_data(weibos, comments, f'topic_{topic}')
            else:
                print("未登录，请先登录微博")
                print("登录后，可以使用浏览器开发者工具获取cookie，然后传入AsyncWeiboSpider的cookie参数")
    else:
        print("未找到已保存的cookies，请先登录微博")
        print("登录后，可以使用浏览器开发者工具获取cookie，然后传入AsyncWeiboSpider的cookie参数")

if __name__ == '__main__':
    # 运行异步主函数
    asyncio.run(main())