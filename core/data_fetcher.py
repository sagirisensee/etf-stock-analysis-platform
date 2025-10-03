import akshare as ak
import pandas as pd
from cachetools import cached, TTLCache
import os
import logging
import asyncio
from tenacity import retry, stop_after_attempt, wait_fixed
import sqlite3
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# 从环境变量获取缓存过期时间，默认60秒
CACHE_EXPIRE = int(os.getenv('CACHE_EXPIRE_SECONDS', '60')) 
cache = TTLCache(maxsize=10, ttl=CACHE_EXPIRE)

# 数据库路径
DB_PATH = 'etf_analysis.db'

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
    """获取所有ETF的实时行情数据 (带缓存)"""
    logger.info("正在从AKShare获取所有ETF实时数据...(缓存有效期: %s秒)", CACHE_EXPIRE)
    try:
        df = ak.fund_etf_spot_em()
        
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
        df = df.rename(columns=column_mapping)
        
        numeric_cols = ['最新价', '昨收', '成交额']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=numeric_cols, inplace=True)
        # 计算涨跌幅
        df['涨跌幅'] = 0.0
        mask = df['昨收'] != 0
        df.loc[mask, '涨跌幅'] = ((df.loc[mask, '最新价'] - df.loc[mask, '昨收']) / df.loc[mask, '昨收']) * 100
        return df
    except Exception as e:
        logger.error(f" 获取ETF实时数据失败: {e}", exc_info=True)
        return None

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_etf_daily_history(etf_code: str):
    """获取单支ETF的历史日线数据 (带自动重试)"""
    logger.info(f"正在获取 {etf_code} 的历史日线数据...")
    try:
        daily_df = await asyncio.to_thread(
            ak.fund_etf_hist_em,
            symbol=etf_code,
            period="daily",
            adjust="qfq"
        )
        
        # 标准化列名
        if '收盘' in daily_df.columns:
            daily_df.rename(columns={'收盘': 'close'}, inplace=True)
        if '最高' in daily_df.columns:
            daily_df.rename(columns={'最高': 'high'}, inplace=True)
        if '最低' in daily_df.columns:
            daily_df.rename(columns={'最低': 'low'}, inplace=True)
        if '日期' in daily_df.columns:
            daily_df.rename(columns={'日期': 'date'}, inplace=True)
        
        return daily_df
    except Exception as e:
        logger.warning(f"⚠️ 获取 {etf_code} 日线数据时出错 (将进行重试): {e}")
        raise e

@cached(cache)
def get_all_stock_spot_realtime():
    """获取所有A股的实时行情数据 (带缓存)"""
    logger.info("正在从AKShare获取所有A股实时数据...(缓存有效期: %s秒)", CACHE_EXPIRE)
    try:
        # 使用专门获取股票实时行情的接口
        df = ak.stock_zh_a_spot_em()
        
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
        df = df.rename(columns=column_mapping)
        
        numeric_cols = ['最新价', '昨收', '成交额']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=numeric_cols, inplace=True)
        # 计算涨跌幅
        df['涨跌幅'] = 0.0
        mask = df['昨收'] != 0
        df.loc[mask, '涨跌幅'] = ((df.loc[mask, '最新价'] - df.loc[mask, '昨收']) / df.loc[mask, '昨收'])
        return df
    except Exception as e:
        logger.error(f" 获取股票实时数据失败: {e}", exc_info=True)
        return None

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_stock_daily_history(stock_code: str):
    """获取单支股票的历史日线数据 (带自动重试)"""
    logger.info(f"正在获取 {stock_code} 的历史日线数据...")
    try:
        # 使用专门获取股票历史数据的接口
        daily_df = await asyncio.to_thread(
            ak.stock_zh_a_hist,
            symbol=stock_code,
            period="daily",
            adjust="qfq"  # 使用前复权数据
        )
        
        # 标准化列名
        if '收盘' in daily_df.columns:
            daily_df.rename(columns={'收盘': 'close'}, inplace=True)
        if '最高' in daily_df.columns:
            daily_df.rename(columns={'最高': 'high'}, inplace=True)
        if '最低' in daily_df.columns:
            daily_df.rename(columns={'最低': 'low'}, inplace=True)
        if '日期' in daily_df.columns:
            daily_df.rename(columns={'日期': 'date'}, inplace=True)
        
        return daily_df
    except Exception as e:
        logger.warning(f" 获取 {stock_code} 日线数据时出错 (将进行重试): {e}")
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