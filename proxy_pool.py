import requests
import random
import time
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("proxy_pool.log"),
        logging.StreamHandler()
    ]
)

class ProxyPool:
    """代理IP池管理器
    
    实现代理IP的获取、验证、管理和自动更新功能
    """
    
    def __init__(self, min_proxies=20, check_interval=300, timeout=5):
        """初始化代理池
        
        Args:
            min_proxies: 最小代理数量，低于此数量时自动获取新代理
            check_interval: 代理检查间隔（秒）
            timeout: 代理验证超时时间（秒）
        """
        self.proxies = Queue()  # 可用代理队列
        self.proxies_set = set()  # 用于快速检查代理是否存在
        self.min_proxies = min_proxies
        self.check_interval = check_interval
        self.timeout = timeout
        self.test_url = "https://www.baidu.com"  # 用于测试代理的URL
        self.lock = threading.Lock()  # 线程锁
        self.is_updating = False  # 是否正在更新代理池
        
        # 代理API列表（免费代理源）
        self.proxy_apis = [
            "https://www.kuaidaili.com/free/inha/",
            "https://www.kuaidaili.com/free/intr/",
            "http://www.ip3366.net/free/?stype=1",
            "http://www.ip3366.net/free/?stype=2",
            "http://www.89ip.cn/index_{}.html",
            "https://www.xicidaili.com/nn/",
            "https://www.xicidaili.com/nt/",
            "https://www.xicidaili.com/wt/",
            "https://ip.jiangxianli.com/?page={}",
            "https://www.kuaidaili.com/ops/proxylist/{}/"
        ]
        
        # 启动代理池维护线程
        self.daemon_thread = threading.Thread(target=self._maintain_pool, daemon=True)
        self.daemon_thread.start()
        
        logging.info("代理池初始化完成")
    
    def _maintain_pool(self):
        """维护代理池的守护线程"""
        while True:
            try:
                # 检查代理池大小
                if self.proxies.qsize() < self.min_proxies and not self.is_updating:
                    logging.info(f"代理池数量不足 ({self.proxies.qsize()}/{self.min_proxies})，开始更新代理池")
                    self.update_pool()
                
                # 定期检查代理有效性
                self._check_proxies()
                
                # 等待下一次检查
                time.sleep(self.check_interval)
            except Exception as e:
                logging.error(f"代理池维护线程出错: {e}")
                time.sleep(60)  # 出错后等待一分钟再继续
    
    def _check_proxies(self):
        """检查代理池中代理的有效性"""
        if self.proxies.empty():
            return
        
        logging.info("开始检查代理有效性")
        
        # 将所有代理取出来检查
        proxies_to_check = []
        while not self.proxies.empty():
            try:
                proxy = self.proxies.get_nowait()
                proxies_to_check.append(proxy)
            except Empty:
                break
        
        valid_proxies = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(self._validate_proxy, proxies_to_check))
            
            for proxy, is_valid in zip(proxies_to_check, results):
                if is_valid:
                    valid_proxies.append(proxy)
        
        # 将有效代理放回队列
        with self.lock:
            for proxy in valid_proxies:
                self.proxies.put(proxy)
        
        logging.info(f"代理检查完成，有效代理: {len(valid_proxies)}/{len(proxies_to_check)}")
    
    def update_pool(self):
        """更新代理池"""
        with self.lock:
            if self.is_updating:
                return
            self.is_updating = True
        
        try:
            logging.info("开始更新代理池")
            
            # 从多个免费代理源获取代理
            new_proxies = []
            for api in self.proxy_apis:
                try:
                    if "{}" in api:
                        # 对于分页的API，获取前3页
                        for page in range(1, 4):
                            proxies = self._fetch_proxies_from_api(api.format(page))
                            new_proxies.extend(proxies)
                            time.sleep(random.uniform(1, 3))  # 随机等待，避免请求过快
                    else:
                        proxies = self._fetch_proxies_from_api(api)
                        new_proxies.extend(proxies)
                        time.sleep(random.uniform(1, 3))
                except Exception as e:
                    logging.error(f"从API获取代理失败: {api}, 错误: {e}")
            
            logging.info(f"从API获取到 {len(new_proxies)} 个代理，开始验证")
            
            # 验证新获取的代理
            valid_proxies = []
            with ThreadPoolExecutor(max_workers=20) as executor:
                results = list(executor.map(self._validate_proxy, new_proxies))
                
                for proxy, is_valid in zip(new_proxies, results):
                    if is_valid and proxy not in self.proxies_set:
                        valid_proxies.append(proxy)
                        self.proxies_set.add(proxy)
            
            # 将有效代理添加到代理池
            with self.lock:
                for proxy in valid_proxies:
                    self.proxies.put(proxy)
            
            logging.info(f"代理池更新完成，新增有效代理: {len(valid_proxies)}/{len(new_proxies)}，当前代理池大小: {self.proxies.qsize()}")
        except Exception as e:
            logging.error(f"更新代理池时出错: {e}")
        finally:
            with self.lock:
                self.is_updating = False
    
    def _fetch_proxies_from_api(self, api_url):
        """从API获取代理列表
        
        Args:
            api_url: 代理API的URL
            
        Returns:
            list: 代理列表，格式为 "http://ip:port" 或 "https://ip:port"
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 解析HTML获取代理IP和端口
            # 注意：不同的代理网站有不同的HTML结构，这里使用简单的正则表达式匹配
            import re
            ip_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            port_pattern = r'<td.*?>(\d+)</td>'
            
            ips = re.findall(ip_pattern, response.text)
            ports = re.findall(port_pattern, response.text)
            
            # 组合IP和端口
            proxies = []
            for i in range(min(len(ips), len(ports))):
                proxy_http = f"http://{ips[i]}:{ports[i]}"
                proxy_https = f"https://{ips[i]}:{ports[i]}"
                proxies.append(proxy_http)
                proxies.append(proxy_https)
            
            return proxies
        except Exception as e:
            logging.error(f"从API获取代理失败: {api_url}, 错误: {e}")
            return []
    
    def _validate_proxy(self, proxy):
        """验证代理是否有效
        
        Args:
            proxy: 代理地址，格式为 "http://ip:port" 或 "https://ip:port"
            
        Returns:
            bool: 代理是否有效
        """
        proxies = {
            "http": proxy,
            "https": proxy
        }
        
        try:
            protocol = proxy.split("://")[0]
            response = requests.get(
                self.test_url,
                proxies=proxies,
                timeout=self.timeout,
                verify=False  # 不验证SSL证书
            )
            return response.status_code == 200
        except:
            return False
    
    def get_proxy(self):
        """获取一个代理
        
        Returns:
            str: 代理地址，格式为 "http://ip:port" 或 "https://ip:port"，如果没有可用代理则返回None
        """
        try:
            # 如果代理池为空，尝试更新
            if self.proxies.empty() and not self.is_updating:
                logging.warning("代理池为空，尝试更新代理池")
                self.update_pool()
            
            # 等待一段时间，如果还是没有代理，返回None
            try:
                return self.proxies.get(timeout=10)
            except Empty:
                logging.error("无法获取代理，代理池为空")
                return None
        except Exception as e:
            logging.error(f"获取代理时出错: {e}")
            return None
    
    def report_proxy(self, proxy, success=True):
        """报告代理使用情况
        
        Args:
            proxy: 代理地址
            success: 代理是否成功使用
        """
        if not proxy:
            return
        
        with self.lock:
            if success:
                # 如果代理使用成功，放回队列继续使用
                self.proxies.put(proxy)
            else:
                # 如果代理使用失败，从代理集合中移除
                if proxy in self.proxies_set:
                    self.proxies_set.remove(proxy)
                logging.info(f"代理使用失败，已移除: {proxy}")

# 使用示例
def test_proxy_pool():
    # 创建代理池实例
    pool = ProxyPool(min_proxies=10, check_interval=60)
    
    # 等待代理池初始化
    time.sleep(5)
    
    # 获取并测试代理
    for i in range(5):
        proxy = pool.get_proxy()
        if proxy:
            print(f"获取到代理: {proxy}")
            
            # 模拟使用代理
            success = random.choice([True, False])
            print(f"代理使用{'成功' if success else '失败'}")
            
            # 报告代理使用情况
            pool.report_proxy(proxy, success)
        else:
            print("无法获取代理")
        
        time.sleep(1)
    
    print(f"当前代理池大小: {pool.proxies.qsize()}")

if __name__ == "__main__":
    test_proxy_pool()