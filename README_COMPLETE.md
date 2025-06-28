# 智能新闻爬虫系统

## 项目简介

这是一个功能丰富的智能新闻爬虫系统，从简单到复杂实现了完整的新闻数据采集、分析和展示功能。系统包含基础爬虫、高级爬虫和精美的Web展示界面。

## 🚀 核心功能

### 基础爬虫 (news_crawler_basic.py)
- ✅ 简单快速的新闻爬取
- ✅ 支持多个新闻网站
- ✅ 数据保存为CSV和JSON格式
- ✅ 基础的内容解析和清洗

### 高级爬虫 (news_crawler_advanced.py)
- ✅ 多线程并发爬取
- ✅ 智能代理IP支持
- ✅ User-Agent轮换
- ✅ 新闻内容详情抓取
- ✅ 中文情感分析
- ✅ 关键词提取
- ✅ 数据去重和断点续爬
- ✅ SQLite数据库存储
- ✅ 数据可视化图表生成
- ✅ 词云图生成

### 爬虫管理器 (crawler_manager.py)
- ✅ 统一的爬虫任务调度
- ✅ 实时状态监控
- ✅ 数据统一管理
- ✅ RESTful API接口
- ✅ Web界面支持

### Web展示界面 (templates/index.html)
- ✅ 现代化响应式设计
- ✅ 实时数据展示
- ✅ 交互式图表
- ✅ 爬虫控制面板
- ✅ 新闻列表展示
- ✅ 情感分析可视化
- ✅ 数据统计仪表板

## 📁 项目结构

```
spider/
├── news_crawler_basic.py      # 基础爬虫
├── news_crawler_advanced.py   # 高级爬虫
├── crawler_manager.py         # 爬虫管理器
├── crawler_config.json        # 配置文件
├── requirements.txt           # 依赖包列表
├── README_COMPLETE.md         # 项目文档
├── templates/
│   └── index.html            # Web展示界面
├── news_data/                # 数据存储目录
│   ├── *.csv                 # CSV数据文件
│   ├── *.json                # JSON数据文件
│   ├── *.db                  # SQLite数据库
│   └── *.xlsx                # Excel数据文件
├── charts/                   # 图表存储目录
│   ├── news_sources.png      # 新闻来源分布图
│   └── sentiment_distribution.png  # 情感分析分布图
└── wordclouds/               # 词云图存储目录
    └── keywords_wordcloud.png # 关键词词云图
```

## 🛠️ 安装和配置

### 1. 环境要求
- Python 3.8+
- Windows/Linux/macOS

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置设置
编辑 `crawler_config.json` 文件，根据需要调整爬虫参数：
- 请求延迟和超时设置
- 目标网站配置
- 代理设置
- 数据分析选项

## 🚀 使用方法

### 方法一：直接运行爬虫

#### 运行基础爬虫
```bash
python news_crawler_basic.py
```

#### 运行高级爬虫
```bash
python news_crawler_advanced.py
```

### 方法二：使用Web管理界面（推荐）

1. 启动Web服务器：
```bash
python crawler_manager.py
```

2. 打开浏览器访问：
```
http://localhost:5000
```

3. 在Web界面中：
   - 查看系统状态和统计数据
   - 启动/停止爬虫任务
   - 实时监控爬取进度
   - 浏览和筛选新闻数据
   - 查看数据分析图表

## 📊 数据分析功能

### 情感分析
- 基于中文关键词的情感倾向分析
- 正面、负面、中性情感分类
- 情感分数量化（-1到1之间）

### 关键词提取
- 使用jieba分词进行中文文本处理
- TF-IDF算法提取关键词
- 支持自定义关键词数量

### 数据可视化
- 新闻来源分布饼图
- 情感分析分布直方图
- 关键词词云图
- 爬虫类型统计柱状图

## 🎨 Web界面特色

### 现代化设计
- 响应式布局，支持移动端
- 渐变色彩和毛玻璃效果
- 流畅的动画和交互
- 直观的数据可视化

### 功能丰富
- 实时状态监控
- 交互式图表展示
- 新闻筛选和搜索
- 数据导出功能
- 爬虫控制面板

## 🔧 高级配置

### 代理设置
在 `crawler_config.json` 中配置代理：
```json
{
  "proxy_settings": {
    "enabled": true,
    "proxy_list": [
      "http://proxy1:8080",
      "http://proxy2:8080"
    ]
  }
}
```

### 自定义网站
添加新的目标网站：
```json
{
  "target_sites": [
    {
      "name": "自定义网站",
      "base_url": "https://example.com/",
      "selectors": {
        "title": "h1, .title",
        "content": ".content, .article"
      }
    }
  ]
}
```

## 📈 性能优化

### 并发控制
- 多线程并发爬取
- 智能请求频率控制
- 连接池复用

### 内存管理
- 流式数据处理
- 及时释放资源
- 数据库批量操作

### 错误处理
- 自动重试机制
- 异常日志记录
- 断点续爬功能

## 🛡️ 合规使用

### 重要提醒
- 遵守robots.txt协议
- 控制爬取频率，避免对目标网站造成压力
- 仅用于学习研究目的
- 尊重网站版权和用户协议

### 建议设置
- 请求间隔：1-3秒
- 并发线程：3-5个
- 单次爬取：50-100条新闻

## 🔍 故障排除

### 常见问题

1. **爬取失败**
   - 检查网络连接
   - 验证目标网站可访问性
   - 调整请求头和延迟设置

2. **数据解析错误**
   - 检查网站结构是否变化
   - 更新CSS选择器
   - 查看错误日志

3. **Web界面无法访问**
   - 确认Flask服务正常启动
   - 检查端口5000是否被占用
   - 查看防火墙设置

### 日志文件
- `crawler_manager.log` - 管理器日志
- `news_crawler.log` - 爬虫运行日志

## 🚀 扩展功能

### 可以添加的功能
- 分布式爬虫支持
- 更多数据源接入
- 高级NLP分析
- 实时推送通知
- 数据API接口
- 用户权限管理

### 技术栈升级
- 使用Scrapy框架
- Redis缓存支持
- Docker容器化
- 云服务部署

## 📄 许可证

MIT License - 详见LICENSE文件

## 👥 贡献

欢迎提交Issue和Pull Request来改进项目！

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 创建GitHub Issue
- 发送邮件反馈

---

**注意：本项目仅供学习和研究使用，请遵守相关法律法规和网站使用条款。**