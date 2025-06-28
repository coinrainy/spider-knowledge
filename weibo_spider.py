# -*- coding: utf-8 -*-
"""
微博爬虫程序
功能：爬取微博文章和评论
"""

import requests
import json
import time
import random
import re
import os
import pandas as pd
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='weibo_spider.log'
)
logger = logging.getLogger('weibo_spider')

class WeiboSpider:
    def __init__(self, cookie=None):
        """
        初始化爬虫
        :param cookie: 微博登录后的cookie字符串
        """
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://weibo.com/',
            'Connection': 'keep-alive'
        }
        
        # 如果提供了cookie，则添加到headers中
        if cookie:
            self.headers['Cookie'] = cookie
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 创建数据存储目录
        self.data_dir = 'weibo_data'
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def save_cookies(self, filename='weibo_cookies.json'):
        """
        保存当前会话的cookies
        :param filename: 保存的文件名
        """
        with open(os.path.join(self.data_dir, filename), 'w') as f:
            json.dump(self.session.cookies.get_dict(), f)
        logger.info(f'Cookies saved to {filename}')
    
    def load_cookies(self, filename='weibo_cookies.json'):
        """
        加载cookies
        :param filename: cookies文件名
        :return: 是否成功加载
        """
        try:
            with open(os.path.join(self.data_dir, filename), 'r') as f:
                cookies = json.load(f)
                self.session.cookies.update(cookies)
            logger.info(f'Cookies loaded from {filename}')
            return True
        except Exception as e:
            logger.error(f'Failed to load cookies: {e}')
            return False
    
    def check_login_status(self):
        """
        检查是否已登录
        :return: 是否已登录
        """
        try:
            # 访问个人主页API
            url = 'https://weibo.com/ajax/profile/info'
            response = self.session.get(url)
            data = response.json()
            
            # 如果返回的数据中包含用户ID，则说明已登录
            if 'data' in data and 'user' in data['data']:
                logger.info(f"Login check successful, user: {data['data']['user']['screen_name']}")
                return True
            else:
                logger.info("Not logged in")
                return False
        except Exception as e:
            logger.error(f'Login check failed: {e}')
            return False
    
    def get_weibo_by_user(self, user_id, count=20):
        """
        获取指定用户的微博列表
        :param user_id: 用户ID
        :param count: 获取的微博数量
        :return: 微博列表
        """
        try:
            url = f'https://weibo.com/ajax/statuses/mymblog?uid={user_id}&page=1&feature=0'
            response = self.session.get(url)
            data = response.json()
            
            if 'data' in data and 'list' in data['data']:
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
    
    def get_weibo_by_topic(self, topic, count=20):
        """
        获取指定话题的微博列表
        :param topic: 话题关键词
        :param count: 获取的微博数量
        :return: 微博列表
        """
        try:
            # 对话题进行URL编码
            encoded_topic = requests.utils.quote(topic)
            url = f'https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D{encoded_topic}&page_type=searchall'
            
            response = self.session.get(url)
            data = response.json()
            
            if 'data' in data and 'cards' in data['data']:
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
    
    def get_weibo_comments(self, weibo_id, count=20):
        """
        获取指定微博的评论
        :param weibo_id: 微博ID
        :param count: 获取的评论数量
        :return: 评论列表
        """
        try:
            url = f'https://weibo.com/ajax/statuses/buildComments?flow=0&is_reload=1&id={weibo_id}&is_show_bulletin=2&is_mix=0&count={count}'
            response = self.session.get(url)
            data = response.json()
            
            if 'data' in data:
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
    
    def parse_weibo_content(self, weibo):
        """
        解析微博内容，提取文本、图片、视频等信息
        :param weibo: 微博数据
        :return: 解析后的微博数据
        """
        try:
            parsed_weibo = {
                'id': weibo.get('id', ''),
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
    
    def save_to_csv(self, data, filename):
        """
        将数据保存为CSV文件
        :param data: 数据列表
        :param filename: 文件名
        """
        try:
            df = pd.DataFrame(data)
            file_path = os.path.join(self.data_dir, filename)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            logger.info(f'Data saved to {file_path}')
        except Exception as e:
            logger.error(f'Failed to save data to CSV: {e}')
    
    def crawl_user_weibos_and_comments(self, user_id, weibo_count=20, comment_count=20):
        """
        爬取用户的微博及其评论
        :param user_id: 用户ID
        :param weibo_count: 爬取的微博数量
        :param comment_count: 每条微博爬取的评论数量
        """
        # 获取用户微博列表
        weibos = self.get_weibo_by_user(user_id, weibo_count)
        
        if not weibos:
            logger.warning(f'No weibos found for user {user_id}')
            return
        
        # 解析微博内容
        parsed_weibos = []
        all_comments = []
        
        for weibo in weibos:
            # 解析微博
            parsed_weibo = self.parse_weibo_content(weibo)
            if parsed_weibo:
                parsed_weibos.append(parsed_weibo)
            
            # 获取评论
            weibo_id = weibo.get('id', '')
            if weibo_id:
                # 添加随机延时，避免请求过于频繁
                time.sleep(random.uniform(1, 3))
                
                comments = self.get_weibo_comments(weibo_id, comment_count)
                for comment in comments:
                    parsed_comment = self.parse_comment(comment)
                    if parsed_comment:
                        # 添加微博ID，关联评论和微博
                        parsed_comment['weibo_id'] = weibo_id
                        all_comments.append(parsed_comment)
        
        # 保存数据
        if parsed_weibos:
            self.save_to_csv(parsed_weibos, f'user_{user_id}_weibos.csv')
        
        if all_comments:
            self.save_to_csv(all_comments, f'user_{user_id}_comments.csv')
    
    def crawl_topic_weibos_and_comments(self, topic, weibo_count=20, comment_count=20):
        """
        爬取话题相关的微博及其评论
        :param topic: 话题关键词
        :param weibo_count: 爬取的微博数量
        :param comment_count: 每条微博爬取的评论数量
        """
        # 获取话题微博列表
        weibo_cards = self.get_weibo_by_topic(topic, weibo_count)
        
        if not weibo_cards:
            logger.warning(f'No weibos found for topic {topic}')
            return
        
        # 解析微博内容
        parsed_weibos = []
        all_comments = []
        
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
                    # 添加随机延时，避免请求过于频繁
                    time.sleep(random.uniform(1, 3))
                    
                    comments = self.get_weibo_comments(weibo_id, comment_count)
                    for comment in comments:
                        parsed_comment = self.parse_comment(comment)
                        if parsed_comment:
                            # 添加微博ID和话题，关联评论、微博和话题
                            parsed_comment['weibo_id'] = weibo_id
                            parsed_comment['topic'] = topic
                            all_comments.append(parsed_comment)
        
        # 保存数据
        if parsed_weibos:
            self.save_to_csv(parsed_weibos, f'topic_{topic}_weibos.csv')
        
        if all_comments:
            self.save_to_csv(all_comments, f'topic_{topic}_comments.csv')

# 使用示例
def main():
    # 创建爬虫实例
    # 如果有cookie，可以传入cookie参数
    spider = WeiboSpider()
    
    # 尝试加载已保存的cookies
    if spider.load_cookies():
        # 检查登录状态
        if spider.check_login_status():
            print("已登录，开始爬取数据")
            
            # 爬取指定用户的微博和评论
            # 这里需要替换为实际的用户ID
            user_id = '1669879400'  # 例如：1669879400是微博官方账号
            spider.crawl_user_weibos_and_comments(user_id, weibo_count=10, comment_count=20)
            
            # 爬取指定话题的微博和评论
            topic = '热门话题'  # 替换为实际要爬取的话题
            spider.crawl_topic_weibos_and_comments(topic, weibo_count=10, comment_count=20)
        else:
            print("未登录，请先登录微博")
            print("登录后，可以使用浏览器开发者工具获取cookie，然后传入WeiboSpider的cookie参数")
    else:
        print("未找到已保存的cookies，请先登录微博")
        print("登录后，可以使用浏览器开发者工具获取cookie，然后传入WeiboSpider的cookie参数")

if __name__ == '__main__':
    main()