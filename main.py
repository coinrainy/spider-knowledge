# -*- coding: utf-8 -*-
"""
微博爬虫主程序
功能：根据配置文件调用不同的爬虫程序
"""

import os
import sys
import logging
import argparse
import asyncio
from config_loader import ConfigLoader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('weibo_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('weibo_crawler')

def parse_arguments():
    """
    解析命令行参数
    :return: 解析后的参数
    """
    parser = argparse.ArgumentParser(description='微博爬虫程序')
    parser.add_argument('--config', type=str, default='config.json', help='配置文件路径')
    parser.add_argument('--mode', type=str, choices=['sync', 'async', 'both'], default='async', 
                        help='爬虫模式：sync(同步), async(异步), both(两者都运行)')
    parser.add_argument('--user', type=str, help='指定爬取的用户ID，覆盖配置文件')
    parser.add_argument('--topic', type=str, help='指定爬取的话题，覆盖配置文件')
    parser.add_argument('--count', type=int, help='指定爬取的微博数量，覆盖配置文件')
    parser.add_argument('--no-analysis', action='store_true', help='不进行数据分析')
    
    return parser.parse_args()

def run_sync_crawler(config_loader):
    """
    运行同步爬虫
    :param config_loader: 配置加载器
    """
    try:
        from weibo_spider import WeiboSpider
        
        # 获取配置
        cookie = config_loader.get_cookie()
        user_crawl_config = config_loader.get_user_crawl_config()
        topic_crawl_config = config_loader.get_topic_crawl_config()
        
        # 创建爬虫实例
        spider = WeiboSpider(cookie=cookie)
        
        # 爬取用户微博
        if user_crawl_config.get('enabled', False):
            for user_id in user_crawl_config.get('user_ids', []):
                logger.info(f"Crawling user {user_id} with sync crawler")
                spider.crawl_user_weibos_and_comments(
                    user_id,
                    weibo_count=user_crawl_config.get('weibo_count', 20),
                    comment_count=user_crawl_config.get('comment_count', 20)
                )
        
        # 爬取话题微博
        if topic_crawl_config.get('enabled', False):
            for topic in topic_crawl_config.get('topics', []):
                logger.info(f"Crawling topic {topic} with sync crawler")
                spider.crawl_topic_weibos_and_comments(
                    topic,
                    weibo_count=topic_crawl_config.get('weibo_count', 20),
                    comment_count=topic_crawl_config.get('comment_count', 20)
                )
        
        logger.info("Sync crawler finished")
    except ImportError:
        logger.error("Failed to import WeiboSpider, please check if weibo_spider.py exists")
    except Exception as e:
        logger.error(f"Error in sync crawler: {e}")

async def run_async_crawler(config_loader, run_analysis=True):
    """
    运行异步爬虫
    :param config_loader: 配置加载器
    :param run_analysis: 是否运行数据分析
    """
    try:
        from async_weibo_spider import AsyncWeiboSpider
        
        # 获取配置
        cookie = config_loader.get_cookie()
        user_crawl_config = config_loader.get_user_crawl_config()
        topic_crawl_config = config_loader.get_topic_crawl_config()
        crawler_settings = config_loader.get_crawler_settings()
        
        # 创建爬虫实例
        spider = AsyncWeiboSpider(
            cookie=cookie,
            max_concurrency=crawler_settings.get('max_concurrency', 5)
        )
        
        # 爬取用户微博
        user_weibos = {}
        user_comments = {}
        
        if user_crawl_config.get('enabled', False):
            for user_id in user_crawl_config.get('user_ids', []):
                logger.info(f"Crawling user {user_id} with async crawler")
                weibos, comments = await spider.crawl_user_weibos_and_comments(
                    user_id,
                    weibo_count=user_crawl_config.get('weibo_count', 20),
                    comment_count=user_crawl_config.get('comment_count', 20),
                    include_replies=user_crawl_config.get('include_replies', True)
                )
                user_weibos[user_id] = weibos
                user_comments[user_id] = comments
        
        # 爬取话题微博
        topic_weibos = {}
        topic_comments = {}
        
        if topic_crawl_config.get('enabled', False):
            for topic in topic_crawl_config.get('topics', []):
                logger.info(f"Crawling topic {topic} with async crawler")
                weibos, comments = await spider.crawl_topic_weibos_and_comments(
                    topic,
                    weibo_count=topic_crawl_config.get('weibo_count', 20),
                    comment_count=topic_crawl_config.get('comment_count', 20),
                    include_replies=topic_crawl_config.get('include_replies', True)
                )
                topic_weibos[topic] = weibos
                topic_comments[topic] = comments
        
        # 数据分析
        if run_analysis:
            data_analysis_config = config_loader.get_data_analysis_config()
            if data_analysis_config.get('sentiment_analysis', True) or \
               data_analysis_config.get('word_cloud', True) or \
               data_analysis_config.get('interaction_analysis', True) or \
               data_analysis_config.get('time_distribution', True):
                
                # 分析用户微博数据
                for user_id, weibos in user_weibos.items():
                    if weibos and user_id in user_comments:
                        logger.info(f"Analyzing user {user_id} data")
                        await spider.analyze_weibo_data(weibos, user_comments[user_id], f'user_{user_id}')
                
                # 分析话题微博数据
                for topic, weibos in topic_weibos.items():
                    if weibos and topic in topic_comments:
                        logger.info(f"Analyzing topic {topic} data")
                        await spider.analyze_weibo_data(weibos, topic_comments[topic], f'topic_{topic}')
        
        logger.info("Async crawler finished")
    except ImportError:
        logger.error("Failed to import AsyncWeiboSpider, please check if async_weibo_spider.py exists")
    except Exception as e:
        logger.error(f"Error in async crawler: {e}")

async def main():
    # 解析命令行参数
    args = parse_arguments()
    
    # 加载配置
    config_loader = ConfigLoader(args.config)
    
    # 如果命令行指定了用户ID，覆盖配置文件
    if args.user:
        user_crawl_config = config_loader.get_user_crawl_config()
        user_crawl_config['enabled'] = True
        user_crawl_config['user_ids'] = [args.user]
        config_loader.update_config({'user_crawl': user_crawl_config})
    
    # 如果命令行指定了话题，覆盖配置文件
    if args.topic:
        topic_crawl_config = config_loader.get_topic_crawl_config()
        topic_crawl_config['enabled'] = True
        topic_crawl_config['topics'] = [args.topic]
        config_loader.update_config({'topic_crawl': topic_crawl_config})
    
    # 如果命令行指定了爬取数量，覆盖配置文件
    if args.count:
        user_crawl_config = config_loader.get_user_crawl_config()
        topic_crawl_config = config_loader.get_topic_crawl_config()
        user_crawl_config['weibo_count'] = args.count
        topic_crawl_config['weibo_count'] = args.count
        config_loader.update_config({
            'user_crawl': user_crawl_config,
            'topic_crawl': topic_crawl_config
        })
    
    # 根据模式运行爬虫
    if args.mode in ['sync', 'both']:
        run_sync_crawler(config_loader)
    
    if args.mode in ['async', 'both']:
        await run_async_crawler(config_loader, not args.no_analysis)

if __name__ == '__main__':
    # 运行异步主函数
    asyncio.run(main())