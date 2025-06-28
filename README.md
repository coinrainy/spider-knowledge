# 微博爬虫项目

## 项目简介

本项目提供了两个微博爬虫程序，用于爬取微博文章和评论数据，并进行数据分析和可视化。

- `weibo_spider.py`: 基础版微博爬虫，使用同步方式爬取数据
- `async_weibo_spider.py`: 高级版微博爬虫，使用异步方式提高爬取效率，并增加了数据分析和可视化功能

## 功能特点

### 基础版爬虫 (weibo_spider.py)

- 爬取指定用户的微博列表
- 爬取指定话题的微博列表
- 爬取微博评论
- 解析微博和评论内容（文本、图片、视频等）
- 数据保存为JSON和CSV格式
- Cookie管理（保存和加载）

### 高级版爬虫 (async_weibo_spider.py)

- 异步爬取，提高效率
- 支持所有基础版功能
- 爬取评论的回复
- 随机User-Agent
- 并发控制
- 数据分析功能：
  - 情感分析
  - 关键词提取
  - 词云生成
  - 互动数据分析（转发、评论、点赞）
  - 发布时间分布分析
- 数据可视化（图表生成）

## 环境要求

- Python 3.7+
- 依赖库：
  - requests
  - aiohttp (异步版本)
  - pandas
  - matplotlib
  - jieba
  - wordcloud
  - beautifulsoup4
  - fake_useragent (异步版本)
  - numpy
  - pillow

## 安装依赖

```bash
pip install requests aiohttp pandas matplotlib jieba wordcloud beautifulsoup4 fake_useragent numpy pillow
```

## 使用方法

### 基础版爬虫

1. 首先，需要获取微博的Cookie：
   - 登录微博网页版
   - 使用浏览器开发者工具获取Cookie

2. 修改代码中的用户ID和话题：

```python
# 在main函数中修改以下内容
user_id = '1669879400'  # 替换为要爬取的用户ID
topic = '热门话题'  # 替换为要爬取的话题
```

3. 运行爬虫：

```bash
python weibo_spider.py
```

### 高级版爬虫

1. 同样需要获取微博Cookie

2. 修改代码中的用户ID和话题

3. 运行爬虫：

```bash
python async_weibo_spider.py
```

## 数据存储

爬取的数据将保存在`weibo_data`目录下：

- JSON文件：原始数据
- CSV文件：结构化数据
- charts目录：数据可视化图表（仅异步版本）

## 注意事项

1. **合法合规使用**：
   - 请遵守微博的使用条款和robots.txt规定
   - 控制爬取频率，避免对服务器造成压力
   - 仅用于学习和研究目的，不得用于商业用途

2. **Cookie获取**：
   - Cookie是敏感信息，请勿分享给他人
   - Cookie有效期有限，过期后需要重新获取

3. **爬取限制**：
   - 微博有反爬机制，频繁爬取可能导致账号被限制
   - 建议使用代理IP轮换（代码中未实现，可自行添加）

4. **数据分析**：
   - 情感分析使用简单的关键词匹配，准确性有限
   - 可以集成更专业的NLP模型提高分析准确性

## 功能扩展

可以根据需要扩展以下功能：

1. 代理IP池：避免IP被封
2. 更复杂的登录机制：自动模拟登录获取Cookie
3. 分布式爬虫：使用Redis等实现多机协作
4. 更专业的NLP分析：使用专业情感分析模型
5. 数据库存储：将数据保存到MySQL、MongoDB等数据库

## 常见问题

1. **无法获取数据**：
   - 检查Cookie是否有效
   - 检查网络连接
   - 检查是否触发了微博的反爬机制

2. **程序运行错误**：
   - 检查依赖库是否安装完整
   - 查看日志文件了解详细错误信息

3. **数据分析失败**：
   - 检查数据是否成功爬取
   - 检查字体文件路径是否正确（词云生成需要）

## 许可证

MIT License