# -*- coding: utf-8 -*-
"""
配置加载器
功能：加载配置文件，提供配置参数给爬虫程序
"""

import json
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('config_loader')

class ConfigLoader:
    def __init__(self, config_file='config.json'):
        """
        初始化配置加载器
        :param config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """
        加载配置文件
        :return: 配置字典
        """
        try:
            if not os.path.exists(self.config_file):
                logger.warning(f"Config file {self.config_file} not found, using default config")
                return self.get_default_config()
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            logger.info(f"Config loaded from {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self.get_default_config()
    
    def get_default_config(self):
        """
        获取默认配置
        :return: 默认配置字典
        """
        return {
            "cookie": "",
            "user_crawl": {
                "enabled": True,
                "user_ids": ["1669879400"],
                "weibo_count": 20,
                "comment_count": 30,
                "include_replies": True
            },
            "topic_crawl": {
                "enabled": True,
                "topics": ["热门话题"],
                "weibo_count": 20,
                "comment_count": 30,
                "include_replies": True
            },
            "proxy": {
                "enabled": False,
                "proxy_list": []
            },
            "crawler_settings": {
                "max_concurrency": 5,
                "delay_min": 0.5,
                "delay_max": 1.5,
                "retry_times": 3,
                "timeout": 10
            },
            "data_analysis": {
                "sentiment_analysis": True,
                "keyword_extraction": True,
                "word_cloud": True,
                "interaction_analysis": True,
                "time_distribution": True
            },
            "output": {
                "json": True,
                "csv": True,
                "charts": True,
                "data_dir": "weibo_data"
            }
        }
    
    def save_config(self, config=None):
        """
        保存配置到文件
        :param config: 配置字典，如果为None则保存当前配置
        """
        try:
            if config is None:
                config = self.config
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            logger.info(f"Config saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def get_cookie(self):
        """
        获取Cookie
        :return: Cookie字符串
        """
        return self.config.get('cookie', '')
    
    def get_user_crawl_config(self):
        """
        获取用户爬取配置
        :return: 用户爬取配置字典
        """
        return self.config.get('user_crawl', {})
    
    def get_topic_crawl_config(self):
        """
        获取话题爬取配置
        :return: 话题爬取配置字典
        """
        return self.config.get('topic_crawl', {})
    
    def get_proxy_config(self):
        """
        获取代理配置
        :return: 代理配置字典
        """
        return self.config.get('proxy', {})
    
    def get_crawler_settings(self):
        """
        获取爬虫设置
        :return: 爬虫设置字典
        """
        return self.config.get('crawler_settings', {})
    
    def get_data_analysis_config(self):
        """
        获取数据分析配置
        :return: 数据分析配置字典
        """
        return self.config.get('data_analysis', {})
    
    def get_output_config(self):
        """
        获取输出配置
        :return: 输出配置字典
        """
        return self.config.get('output', {})
    
    def update_config(self, new_config):
        """
        更新配置
        :param new_config: 新配置字典
        :return: 是否成功更新
        """
        try:
            self.config.update(new_config)
            return self.save_config()
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            return False

# 使用示例
def main():
    # 创建配置加载器
    config_loader = ConfigLoader()
    
    # 获取配置
    cookie = config_loader.get_cookie()
    user_crawl_config = config_loader.get_user_crawl_config()
    topic_crawl_config = config_loader.get_topic_crawl_config()
    
    # 打印配置
    print(f"Cookie: {cookie[:10]}..." if cookie else "Cookie: Not set")
    print(f"User crawl enabled: {user_crawl_config.get('enabled', False)}")
    print(f"User IDs: {user_crawl_config.get('user_ids', [])}")
    print(f"Topic crawl enabled: {topic_crawl_config.get('enabled', False)}")
    print(f"Topics: {topic_crawl_config.get('topics', [])}")

if __name__ == '__main__':
    main()