import akshare as ak
import pandas as pd
from cachetools import cached, TTLCache
import os
import logging
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, wait_fixed
import sqlite3
from contextlib import contextmanager
import time
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 从环境变量获取缓存过期时间，默认60秒
CACHE_EXPIRE = int(os.getenv('CACHE_EXPIRE_SECONDS', '60')) 
cache = TTLCache(maxsize=10, ttl=CACHE_EXPIRE)

# 数据库路径
DB_PATH = 'etf_analysis.db'

# 反爬虫控制
class AntiCrawlingController:
    """反爬虫控制器"""
    def __init__(self):
        self.last_request_time = {}
        self.request_count = {}
        self.base_delay = 6  # 基础延迟6秒（延长一倍）
        self.max_delay = 20  # 最大延迟20秒（延长一倍）
        self.request_window = 60  # 请求时间窗口（秒）
        self.max_requests_per_window = 10  # 每个时间窗口最大请求数
    
    def get_smart_delay(self, api_name: str) -> float:
        """获取智能延迟时间"""
        current_time = time.time()
        
        # 清理过期的请求记录
        if api_name in self.last_request_time:
            if current_time - self.last_request_time[api_name] > self.request_window:
                self.request_count[api_name] = 0
        
        # 计算延迟
        if api_name not in self.request_count:
            self.request_count[api_name] = 0
        
        # 根据请求频率动态调整延迟
        recent_requests = self.request_count.get(api_name, 0)
        if recent_requests >= self.max_requests_per_window:
            # 请求过于频繁，增加延迟
            delay = self.base_delay + random.uniform(2, 5)
        elif recent_requests >= self.max_requests_per_window * 0.7:
            # 请求较多，适度增加延迟
            delay = self.base_delay + random.uniform(1, 3)
        else:
            # 正常请求，使用基础延迟
            delay = self.base_delay + random.uniform(0, 2)
        
        # 确保延迟在合理范围内
        delay = min(max(delay, self.base_delay), self.max_delay)
        
        # 智能延迟控制已启用
        return delay
    
    def record_request(self, api_name: str):
        """记录请求"""
        current_time = time.time()
        self.last_request_time[api_name] = current_time
        self.request_count[api_name] = self.request_count.get(api_name, 0) + 1

# 全局反爬虫控制器
anti_crawling = AntiCrawlingController()

# 历史数据获取配置
class DataConfig:
    """数据获取配置"""
    def __init__(self):
        # 根据需要的技术指标调整天数
        # 当前使用: SMA_5, SMA_10, SMA_20, SMA_60, MACD(26), 布林带(20)
        # 为了判断60日均线趋势，需要至少61天数据（当前天 + 前一天）
        self.max_days = int(os.getenv('HISTORY_DATA_DAYS', '120'))  # 默认120天，确保有足够数据判断60日均线趋势
        self.min_days = 61  # 最少61天，保证60日均线趋势判断
    
    def get_date_range(self):
        """获取数据日期范围"""
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=self.max_days)).strftime('%Y%m%d')
        return start_date, end_date

# 全局数据配置
data_config = DataConfig()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_stock_pools_from_db(pool_type=None):
    """从数据库获取标的池"""
    try:
        with get_db() as conn:
            if pool_type:
                results = conn.execute(
                    'SELECT * FROM stock_pools WHERE type = ? ORDER BY name',
                    (pool_type,)
                ).fetchall()
            else:
                results = conn.execute(
                    'SELECT * FROM stock_pools ORDER BY type, name'
                ).fetchall()
            return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"从数据库获取标的池失败: {e}")
        return []

@cached(cache)
def get_all_etf_spot_realtime():
    """获取所有ETF的实时行情数据 (带缓存和多数据源)"""
    logger.info("正在从AKShare获取所有ETF实时数据...(缓存有效期: %s秒)", CACHE_EXPIRE)
    
    # 数据源列表，按优先级排序
    etf_data_sources = [
        {
            'name': 'fund_etf_spot_em',
            'func': ak.fund_etf_spot_em,
            'description': '东方财富ETF实时数据'
        },
        {
            'name': 'fund_etf_spot_ths', 
            'func': ak.fund_etf_spot_ths,
            'description': '同花顺ETF实时数据'
        }
    ]
    
    for source in etf_data_sources:
        try:
            # 应用智能延迟控制
            delay = anti_crawling.get_smart_delay(source['name'])
            time.sleep(delay)
            
            # 尝试数据源
            df = source['func']()
            
            # 记录成功请求
            anti_crawling.record_request(source['name'])
            # 数据获取成功
            
            # 根据数据源进行不同的列名映射
            if source['name'] == 'fund_etf_spot_em':
                # 东方财富数据源
                column_mapping = {
                    '代码': '代码',
                    '名称': '名称',
                    '最新价': '最新价',
                    '涨跌幅': '涨跌幅',
                    '涨跌额': '涨跌额',
                    '昨收': '昨收'
                }
            elif source['name'] == 'fund_etf_spot_ths':
                # 同花顺数据源
                column_mapping = {
                    '基金代码': '代码',
                    '基金名称': '名称',
                    '当前-单位净值': '最新价',
                    '增长率': '涨跌幅',
                    '增长值': '涨跌额',
                    '前一日-单位净值': '昨收'
                }
            else:
                # 默认映射
                column_mapping = {
                    '代码': '代码',
                    '名称': '名称',
                    '最新价': '最新价',
                    '涨跌幅': '涨跌幅',
                    '涨跌额': '涨跌额',
                    '昨收': '昨收'
                }
            
            # 重命名列
            df = df.rename(columns=column_mapping)
            
            # 根据数据源确定需要处理的数值列
            if source['name'] == 'fund_etf_spot_ths':
                # 同花顺数据源没有成交额，只处理其他列
                numeric_cols = ['最新价', '昨收']
            else:
                # 其他数据源
                numeric_cols = ['最新价', '昨收', '成交额']
            
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 只对存在的列进行dropna
            available_cols = [col for col in numeric_cols if col in df.columns]
            df.dropna(subset=available_cols, inplace=True)
            # ETF涨跌幅处理：ETF类型，必须乘以100转换为百分比
            if '涨跌幅' in df.columns:
                df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
                # ETF数据源返回小数形式，必须转换为百分比
                df['涨跌幅'] = df['涨跌幅'] * 100
                logger.info("🔄 [ETF实时数据] 涨跌幅从小数转换为百分比")
            else:
                # 如果没有涨跌幅列，则计算
                df['涨跌幅'] = 0.0
                mask = df['昨收'] != 0
                df.loc[mask, '涨跌幅'] = ((df.loc[mask, '最新价'] - df.loc[mask, '昨收']) / df.loc[mask, '昨收']) * 100
            return df
            
        except Exception as e:
            logger.warning(f"⚠️ [ETF实时数据] {source['description']} 获取失败: {e}")
            continue  # 尝试下一个数据源
    
    # 所有数据源都失败
    logger.error(f"💥 [ETF实时数据] 所有数据源都获取失败")
    return None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=8, max=120))
async def get_etf_daily_history(etf_code: str, data_type: str = "etf"):
    """获取单支ETF的历史日线数据 (带自动重试)"""
    logger.info(f"🔍 [ETF历史数据] 正在获取 {etf_code} 的历史日线数据，类型: {data_type}")
    try:
        # 应用智能延迟控制
        api_name = f"fund_etf_hist_em_{etf_code}"
        delay = anti_crawling.get_smart_delay(api_name)
        await asyncio.sleep(delay)
        
        # 获取配置的日期范围
        start_date, end_date = data_config.get_date_range()
        # 调用历史数据接口
        # 数据范围配置
        
        daily_df = await asyncio.to_thread(
            ak.fund_etf_hist_em,
            symbol=etf_code,
            period="daily",
            adjust="qfq",
            start_date=start_date,
            end_date=end_date
        )
        
        # 记录成功请求
        anti_crawling.record_request(api_name)
        # 历史数据获取完成
        
        # 标准化列名
        if '收盘' in daily_df.columns:
            daily_df.rename(columns={'收盘': 'close'}, inplace=True)
        if '最高' in daily_df.columns:
            daily_df.rename(columns={'最高': 'high'}, inplace=True)
        if '最低' in daily_df.columns:
            daily_df.rename(columns={'最低': 'low'}, inplace=True)
        if '日期' in daily_df.columns:
            daily_df.rename(columns={'日期': 'date'}, inplace=True)
        
        # 数据处理完成
        return daily_df
    except Exception as e:
        logger.error(f"💥 [ETF历史数据] 获取 {etf_code} 日线数据时出错 (将进行重试): {e}", exc_info=True)
        raise e

@cached(cache)
def get_all_stock_spot_realtime():
    """获取所有A股的实时行情数据 (带缓存)"""
    logger.info("正在从AKShare获取所有A股实时数据...(缓存有效期: %s秒)", CACHE_EXPIRE)
    try:
        # 应用智能延迟控制
        api_name = "stock_zh_a_spot_em"
        delay = anti_crawling.get_smart_delay(api_name)
        logger.info(f"⏱️ [股票实时数据] 延迟 {delay:.2f} 秒后开始获取数据")
        time.sleep(delay)
        
        # 使用专门获取股票实时行情的接口
        # 调用股票实时数据接口
        logger.info("📡 [股票实时数据] 正在调用 ak.stock_zh_a_spot_em()")
        df = ak.stock_zh_a_spot_em()
        logger.info(f"✅ [股票实时数据] 原始数据获取成功，形状: {df.shape}")
        
        # 记录成功请求
        anti_crawling.record_request(api_name)
        
        # 标准化列名映射
        column_mapping = {
            '代码': '代码',
            '名称': '名称',
            '最新价': '最新价',
            '涨跌幅': '涨跌幅',
            '涨跌额': '涨跌额',
            '昨收': '昨收'
        }
        
        # 重命名列
        logger.info(f"📋 [股票实时数据] 原始列名: {list(df.columns)}")
        df = df.rename(columns=column_mapping)
        logger.info(f"📋 [股票实时数据] 重命名后列名: {list(df.columns)}")
        
        numeric_cols = ['最新价', '昨收', '成交额']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=numeric_cols, inplace=True)
        logger.info(f"📊 [股票实时数据] 数据清理后形状: {df.shape}")
        
        # 股票涨跌幅处理：股票类型，直接使用（已经是百分比形式）
        if '涨跌幅' in df.columns:
            df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
            # 股票数据源返回百分比形式，直接使用
            logger.info("✅ [股票实时数据] 涨跌幅已经是百分比形式，直接使用")
        else:
            # 如果没有涨跌幅列，则计算
            df['涨跌幅'] = 0.0
            mask = df['昨收'] != 0
            df.loc[mask, '涨跌幅'] = ((df.loc[mask, '最新价'] - df.loc[mask, '昨收']) / df.loc[mask, '昨收']) * 100
        
        logger.info(f"✅ [股票实时数据] 处理完成，最终形状: {df.shape}")
        return df
    except Exception as e:
        logger.error(f"💥 [股票实时数据] 获取失败: {e}", exc_info=True)
        return None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=8, max=120))
async def get_stock_daily_history(stock_code: str, data_type: str = "stock"):
    """获取单支股票的历史日线数据 (带自动重试)"""
    logger.info(f"🔍 [股票历史数据] 正在获取 {stock_code} 的历史日线数据，类型: {data_type}")
    try:
        # 应用智能延迟控制
        api_name = f"stock_zh_a_hist_{stock_code}"
        delay = anti_crawling.get_smart_delay(api_name)
        await asyncio.sleep(delay)
        
        # 获取配置的日期范围
        start_date, end_date = data_config.get_date_range()
        # 调用股票历史数据接口
        # 数据范围配置
        
        # 使用专门获取股票历史数据的接口
        daily_df = await asyncio.to_thread(
            ak.stock_zh_a_hist,
            symbol=stock_code,
            period="daily",
            adjust="qfq",  # 使用前复权数据
            start_date=start_date,
            end_date=end_date
        )
        
        # 记录成功请求
        anti_crawling.record_request(api_name)
        logger.info(f"📈 [股票历史数据] {stock_code} 原始数据获取结果: {type(daily_df)}, 形状: {daily_df.shape if daily_df is not None else 'None'}")
        if daily_df is not None and not daily_df.empty:
            logger.info(f"📋 [股票历史数据] {stock_code} 原始列名: {list(daily_df.columns)}")
            logger.info(f"📋 [股票历史数据] {stock_code} 前3行:\n{daily_df.head(3)}")
        
        # 标准化列名
        if '收盘' in daily_df.columns:
            daily_df.rename(columns={'收盘': 'close'}, inplace=True)
        if '最高' in daily_df.columns:
            daily_df.rename(columns={'最高': 'high'}, inplace=True)
        if '最低' in daily_df.columns:
            daily_df.rename(columns={'最低': 'low'}, inplace=True)
        if '日期' in daily_df.columns:
            daily_df.rename(columns={'日期': 'date'}, inplace=True)
        
        logger.info(f"✅ [股票历史数据] {stock_code} 处理完成，最终列名: {list(daily_df.columns) if daily_df is not None else 'None'}")
        return daily_df
    except Exception as e:
        logger.error(f"💥 [股票历史数据] 获取 {stock_code} 日线数据时出错 (将进行重试): {e}", exc_info=True)
        raise e

# 为了兼容现有代码，保留同步版本的历史数据获取函数
def get_etf_daily_history_sync(etf_code: str, period="daily", adjust=""):
    """获取ETF历史数据（同步版本）"""
    try:
        return ak.fund_etf_hist_em(symbol=etf_code, period=period, adjust=adjust)
    except Exception as e:
        logger.error(f"获取ETF {etf_code} 历史数据失败: {e}")
        return None

def get_stock_daily_history_sync(stock_code: str, period="daily", adjust=""):
    """获取股票历史数据（同步版本）"""
    try:
        return ak.stock_zh_a_hist(symbol=stock_code, period=period, adjust=adjust)
    except Exception as e:
        logger.error(f"获取股票 {stock_code} 历史数据失败: {e}")
        return None