#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础新闻爬虫 - 从简单开始
目标网站：新浪新闻（示例）
功能：爬取新闻标题、链接、时间、摘要
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import csv
import json
from datetime import datetime
import os

class BasicNewsCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 创建数据存储目录
        if not os.path.exists('news_data'):
            os.makedirs('news_data')
    
    def get_news_list(self, category='news', page=1):
        """
        获取新闻列表
        """
        # 使用网易新闻作为示例（更容易解析）
        url = f'https://news.163.com/'
        
        try:
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_list = []
            
            # 更健壮的新闻链接提取
            # 查找所有包含新闻链接的a标签
            all_links = soup.find_all('a', href=True)
            
            news_count = 0
            for link_elem in all_links:
                if news_count >= 20:  # 限制数量
                    break
                    
                try:
                    href = link_elem.get('href')
                    
                    # 过滤有效的新闻链接
                    if not href:
                        continue
                        
                    # 检查是否为新闻链接
                    news_indicators = ['news', 'article', '2024', '2025']
                    if not any(indicator in href for indicator in news_indicators):
                        continue
                    
                    # 构建完整URL
                    if href.startswith('//'):
                        link = 'https:' + href
                    elif href.startswith('/'):
                        link = 'https://news.163.com' + href
                    elif href.startswith('http'):
                        link = href
                    else:
                        continue
                    
                    # 提取标题
                    title = link_elem.get_text(strip=True)
                    if not title or len(title) < 5 or len(title) > 100:
                        # 尝试从父元素获取标题
                        parent = link_elem.parent
                        if parent:
                            title = parent.get_text(strip=True)
                    
                    # 过滤无效标题
                    if not title or len(title) < 5 or len(title) > 100:
                        continue
                        
                    # 过滤重复和无效内容
                    invalid_keywords = ['更多', '查看', '点击', '登录', '注册', '首页', '导航']
                    if any(keyword in title for keyword in invalid_keywords):
                        continue
                    
                    # 提取时间（默认当前时间）
                    pub_time = datetime.now().strftime('%Y-%m-%d %H:%M')
                    
                    # 尝试从链接周围提取更多信息
                    summary = ''
                    parent = link_elem.parent
                    if parent:
                        summary_elem = parent.find('p') or parent.find(class_='summary')
                        if summary_elem:
                            summary = summary_elem.get_text(strip=True)[:200]
                    
                    news_list.append({
                        'title': title,
                        'link': link,
                        'summary': summary,
                        'pub_time': pub_time,
                        'category': category,
                        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
                    news_count += 1
                    print(f'找到新闻: {title[:30]}...')
                        
                except Exception as e:
                    print(f'解析新闻项时出错: {e}')
                    continue
            
            return news_list
            
        except Exception as e:
            print(f'获取新闻列表失败: {e}')
            return []
    
    def get_news_detail(self, news_url):
        """
        获取新闻详情
        """
        try:
            response = self.session.get(news_url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取正文内容
            content_selectors = [
                '.post_content_main',
                '.post_text',
                '.content',
                'article',
                '.article-content'
            ]
            
            content = ''
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem.get_text(strip=True)
                    break
            
            # 提取图片
            images = []
            img_tags = soup.find_all('img')
            for img in img_tags[:5]:  # 限制图片数量
                src = img.get('src') or img.get('data-src')
                if src and 'http' in src:
                    images.append(src)
            
            return {
                'content': content,
                'images': images
            }
            
        except Exception as e:
            print(f'获取新闻详情失败: {e}')
            return {'content': '', 'images': []}
    
    def save_to_csv(self, news_list, filename='news_basic.csv'):
        """
        保存到CSV文件
        """
        filepath = os.path.join('news_data', filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['title', 'link', 'summary', 'pub_time', 'category', 'crawl_time']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for news in news_list:
                writer.writerow(news)
        
        print(f'数据已保存到 {filepath}')
    
    def save_to_json(self, news_list, filename='news_basic.json'):
        """
        保存到JSON文件
        """
        filepath = os.path.join('news_data', filename)
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(news_list, jsonfile, ensure_ascii=False, indent=2)
        
        print(f'数据已保存到 {filepath}')
    
    def crawl(self, categories=['news'], max_pages=3):
        """
        主爬取函数
        """
        all_news = []
        
        for category in categories:
            print(f'\n开始爬取分类: {category}')
            
            for page in range(1, max_pages + 1):
                print(f'爬取第 {page} 页...')
                
                news_list = self.get_news_list(category, page)
                
                if news_list:
                    all_news.extend(news_list)
                    print(f'获取到 {len(news_list)} 条新闻')
                else:
                    print('未获取到新闻，可能已到最后一页')
                    break
                
                # 添加延时，避免请求过快
                time.sleep(random.uniform(1, 3))
        
        print(f'\n总共爬取到 {len(all_news)} 条新闻')
        
        # 保存数据
        if all_news:
            self.save_to_csv(all_news)
            self.save_to_json(all_news)
        
        return all_news

def main():
    """
    主函数
    """
    print('=== 基础新闻爬虫启动 ===')
    
    crawler = BasicNewsCrawler()
    
    # 爬取新闻
    categories = ['news']  # 可以扩展更多分类
    news_data = crawler.crawl(categories, max_pages=2)
    
    print('\n=== 爬取完成 ===')
    print(f'共获取 {len(news_data)} 条新闻')
    
    # 显示前几条新闻
    if news_data:
        print('\n前5条新闻预览:')
        for i, news in enumerate(news_data[:5], 1):
            print(f'{i}. {news["title"]}')
            print(f'   时间: {news["pub_time"]}')
            print(f'   链接: {news["link"]}')
            print()

if __name__ == '__main__':
    main()