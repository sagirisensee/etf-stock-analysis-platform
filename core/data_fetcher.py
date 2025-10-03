# data_fetcher.py - 数据获取模块
import os
import logging
import pandas as pd
import akshare as ak
from cachetools import TTLCache
from tenacity import retry, stop_after_attempt, wait_exponential
import random
import time
# 移除了未使用的requests相关导入

logger = logging.getLogger(__name__)

# 从环境变量获取缓存过期时间，默认60秒
CACHE_EXPIRE = int(os.getenv('CACHE_EXPIRE_SECONDS', '60')) 
cache = TTLCache(maxsize=10, ttl=CACHE_EXPIRE)

# 用户代理池，随机选择避免被识别
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0'
]

def get_random_headers():
    """获取随机请求头"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }

# 请求频率限制器
_request_times = []
MAX_REQUESTS_PER_MINUTE = 10  # 每分钟最多10次请求

def smart_delay():
    """智能延迟，避免被ban"""
    global _request_times
    
    # 清理1分钟前的请求记录
    current_time = time.time()
    _request_times = [t for t in _request_times if current_time - t < 60]
    
    # 如果请求过于频繁，增加延迟
    if len(_request_times) >= MAX_REQUESTS_PER_MINUTE:
        extra_delay = random.uniform(15, 30)
        logger.warning(f"请求过于频繁，额外延迟 {extra_delay:.2f} 秒")
        time.sleep(extra_delay)
        _request_times = []  # 清空记录
    
    # 记录当前请求时间
    _request_times.append(current_time)
    
    # 基础延迟 + 随机延迟，增加延迟时间
    base_delay = random.uniform(5, 10)
    random_delay = random.uniform(0, 5)
    total_delay = base_delay + random_delay
    logger.info(f"智能延迟 {total_delay:.2f} 秒")
    time.sleep(total_delay)

# Web服务使用数据库管理标的池，不再需要环境变量配置


@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=5, min=10, max=60),
    reraise=True
)
def _fetch_data_with_retry(data_type, fetch_func):
    """通用数据获取函数，带重试机制"""
    try:
        # 智能延迟避免被ban
        smart_delay()
        
        logger.info(f"正在获取{data_type}实时数据...")
        
        # akshare没有set_config方法，直接使用默认配置
        
        data = fetch_func()
        
        if data is not None and not data.empty:
            logger.info(f"成功获取{data_type}数据，共{len(data)}条记录")
            return data
        else:
            logger.warning(f"{data_type}数据为空，可能被限制访问")
            raise Exception("数据为空，可能被限制访问")
            
    except Exception as e:
        logger.error(f"获取{data_type}数据失败: {e}")
        # 失败后增加额外延迟
        time.sleep(random.uniform(5, 10))
        raise

def _fetch_etf_data_with_retry():
    """获取ETF实时数据，带重试机制"""
    return _fetch_data_with_retry("ETF", ak.fund_etf_spot_em)

def _fetch_stock_data_with_retry():
    """获取股票实时数据，带重试机制"""
    return _fetch_data_with_retry("股票", ak.stock_zh_a_spot_em)

def get_all_etf_spot_realtime():
    """获取所有ETF实时数据"""
    cache_key = 'etf_spot_realtime'
    
    # 检查缓存
    if cache_key in cache:
        logger.info("从缓存获取ETF数据")
        return cache[cache_key]
    
    try:
        data = _fetch_etf_data_with_retry()
        if data is not None and not data.empty:
            cache[cache_key] = data
            return data
        else:
            logger.warning("ETF数据为空")
            return None
    except Exception as e:
        logger.error(f"获取ETF数据失败: {e}")
        return None

def get_all_stock_spot_realtime():
    """获取所有股票实时数据"""
    cache_key = 'stock_spot_realtime'
    
    # 检查缓存
    if cache_key in cache:
        logger.info("从缓存获取股票数据")
        return cache[cache_key]
    
    try:
        data = _fetch_stock_data_with_retry()
        if data is not None and not data.empty:
            cache[cache_key] = data
            return data
        else:
            logger.warning("股票数据为空")
            return None
    except Exception as e:
        logger.error(f"获取股票数据失败: {e}")
        return None

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=2, min=3, max=15),
    reraise=True
)
def _get_daily_history_with_retry(code, data_type, fetch_func, period="daily", adjust=""):
    """通用历史数据获取函数，带重试机制"""
    try:
        # 智能延迟避免被ban
        smart_delay()
        
        logger.info(f"获取{data_type} {code} 历史数据...")
        
        # akshare没有set_config方法，直接使用默认配置
        
        data = fetch_func(symbol=code, period=period, adjust=adjust)
        
        if data is not None and not data.empty:
            # 如果是ETF，重命名列以匹配股票数据格式
            if data_type == "ETF":
                data = data.rename(columns={
                    '日期': '日期',
                    '开盘': '开盘',
                    '收盘': '收盘', 
                    '最高': '最高',
                    '最低': '最低',
                    '成交量': '成交量',
                    '成交额': '成交额',
                    '振幅': '振幅',
                    '涨跌幅': '涨跌幅',
                    '涨跌额': '涨跌额',
                    '换手率': '换手率'
                })
            logger.info(f"成功获取{data_type} {code} 历史数据，共{len(data)}条记录")
            return data
        else:
            logger.warning(f"{data_type} {code} 历史数据为空")
            return None
    except Exception as e:
        logger.error(f"获取{data_type} {code} 历史数据失败: {e}")
        # 失败后增加额外延迟
        time.sleep(random.uniform(3, 8))
        return None

def get_etf_daily_history(code, period="daily", adjust=""):
    """获取ETF历史数据"""
    return _get_daily_history_with_retry(code, "ETF", ak.fund_etf_hist_em, period, adjust)

def get_stock_daily_history(code, period="daily", adjust=""):
    """获取股票历史数据"""
    return _get_daily_history_with_retry(code, "股票", ak.stock_zh_a_hist, period, adjust)
