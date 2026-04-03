import akshare as ak
import pandas as pd
from cachetools import cached, TTLCache
import os
import logging
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
    retry_if_exception_type,
)
import sqlite3
from contextlib import contextmanager
import time
import random
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)

# 从环境变量获取缓存过期时间，默认60秒
CACHE_EXPIRE = int(os.getenv("CACHE_EXPIRE_SECONDS", "60"))
cache = TTLCache(maxsize=10, ttl=CACHE_EXPIRE)

# 数据库路径
DB_PATH = "etf_analysis.db"


# ========== 反爬虫增强：伪装 User-Agent ==========
# 随机 User-Agent 池（模拟真实浏览器）
USER_AGENT_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

# 保存原始的 requests.Session.request 方法
_original_request = requests.Session.request


def _patched_request(self, method, url, **kwargs):
    """
    给所有 requests 请求自动添加随机 User-Agent、headers 和增加 timeout
    """
    # 如果用户没有指定 headers，添加默认 headers
    if "headers" not in kwargs:
        kwargs["headers"] = {}

    # 随机选择 User-Agent（模拟真实用户）
    if "User-Agent" not in kwargs["headers"]:
        kwargs["headers"]["User-Agent"] = random.choice(USER_AGENT_POOL)

    # 添加其他常见的浏览器 headers
    if "Accept" not in kwargs["headers"]:
        kwargs["headers"]["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    if "Accept-Language" not in kwargs["headers"]:
        kwargs["headers"]["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8"
    if "Accept-Encoding" not in kwargs["headers"]:
        kwargs["headers"]["Accept-Encoding"] = "gzip, deflate, br"
    if "Connection" not in kwargs["headers"]:
        kwargs["headers"]["Connection"] = "keep-alive"
    if "Upgrade-Insecure-Requests" not in kwargs["headers"]:
        kwargs["headers"]["Upgrade-Insecure-Requests"] = "1"

    # 增加 timeout 时间（防止读取超时）
    if "timeout" not in kwargs:
        # 默认 60 秒超时（连接超时10秒 + 读取超时60秒）
        kwargs["timeout"] = (10, 60)

    # 调用原始方法
    return _original_request(self, method, url, **kwargs)


# 应用猴子补丁（Monkey Patch）
requests.Session.request = _patched_request
logger.info("🛡️ 反爬虫增强已启用：随机 User-Agent、浏览器 headers 伪装、超时时间 60 秒")
# ========== 反爬虫增强结束 ==========



# 反爬虫控制
class AntiCrawlingController:
    """反爬虫控制器 - 增强版"""

    def __init__(self):
        self.last_request_time = {}
        self.request_count = {}
        self.base_delay = 5  # 基础延迟增加到5秒（防止被ban）
        self.max_delay = 15  # 最大延迟15秒
        self.request_window = 60  # 请求时间窗口（秒）
        self.max_requests_per_window = 3  # 每60秒最多3个请求（降低频率）
        self.last_global_request_time = 0  # 全局最后请求时间
        self.min_global_interval = 4  # 全局最小请求间隔增加到4秒

    def get_smart_delay(self, api_name: str) -> float:
        """获取智能延迟时间（增强版）"""
        current_time = time.time()

        # 清理过期的请求记录
        if api_name in self.last_request_time:
            if current_time - self.last_request_time[api_name] > self.request_window:
                self.request_count[api_name] = 0

        # 计算延迟
        if api_name not in self.request_count:
            self.request_count[api_name] = 0

        # 全局请求间隔控制
        time_since_last_global = current_time - self.last_global_request_time
        if time_since_last_global < self.min_global_interval:
            # 如果距离上次全局请求时间太短，需要等待
            global_wait = self.min_global_interval - time_since_last_global
        else:
            global_wait = 0

        # 根据请求频率动态调整延迟（更保守）
        recent_requests = self.request_count.get(api_name, 0)
        if recent_requests >= self.max_requests_per_window:
            # 请求过于频繁，大幅增加延迟
            delay = self.base_delay + random.uniform(5, 8)
        elif recent_requests >= self.max_requests_per_window * 0.6:
            # 请求较多，适度增加延迟
            delay = self.base_delay + random.uniform(2, 4)
        else:
            # 正常请求，使用基础延迟 + 更大的随机波动（模拟人类）
            delay = self.base_delay + random.uniform(1, 3)

        # 确保延迟在合理范围内
        delay = min(max(delay, self.base_delay), self.max_delay)

        # 返回全局等待时间 + 计算的延迟
        total_delay = global_wait + delay
        return total_delay

    def record_request(self, api_name: str):
        """记录请求"""
        current_time = time.time()
        self.last_request_time[api_name] = current_time
        self.request_count[api_name] = self.request_count.get(api_name, 0) + 1
        self.last_global_request_time = current_time  # 更新全局最后请求时间


# 全局反爬虫控制器
anti_crawling = AntiCrawlingController()

# 全局请求信号量，限制同时进行的请求数量（最多2个并发请求）
_request_semaphore = None


def get_request_semaphore():
    """获取请求信号量（延迟初始化）"""
    global _request_semaphore
    if _request_semaphore is None:
        _request_semaphore = asyncio.Semaphore(1)  # 降低到1个并发（更安全）
    return _request_semaphore


# 历史数据获取配置
class DataConfig:
    """数据获取配置"""

    def __init__(self):
        # 根据需要的技术指标调整天数
        # 当前使用: SMA_5, SMA_10, SMA_20, MACD(12,26,9), 布林带(20), 前瞻性指标(RSI/KDJ/CCI/OBV/威廉)
        # 为了判断20日均线趋势，需要至少21天数据（当前天 + 前一天）
        self.max_days = int(
            os.getenv("HISTORY_DATA_DAYS", "120")
        )  # 默认120天，确保有足够数据分析
        self.min_days = 21  # 最少21天，保证20日均线趋势判断

    def get_date_range(self):
        """获取数据日期范围"""
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=self.max_days)).strftime("%Y%m%d")
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
                    "SELECT * FROM stock_pools WHERE type = ? ORDER BY name",
                    (pool_type,),
                ).fetchall()
            else:
                results = conn.execute(
                    "SELECT * FROM stock_pools ORDER BY type, name"
                ).fetchall()
            return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"从数据库获取标的池失败: {e}")
        return []


@cached(cache)
def get_all_etf_spot_realtime():
    """获取所有ETF的实时行情数据 (带缓存和多数据源)"""
    logger.info("正在从AKShare获取所有ETF实时数据...(缓存有效期: %s秒)", CACHE_EXPIRE)

    etf_data_sources = [
        {
            "name": "fund_etf_spot_em",
            "func": ak.fund_etf_spot_em,
            "description": "东方财富ETF实时数据",
        },
        {
            "name": "fund_etf_spot_ths",
            "func": ak.fund_etf_spot_ths,
            "description": "同花顺ETF实时数据",
        },
    ]

    for source in etf_data_sources:
        try:
            # 应用智能延迟控制
            delay = anti_crawling.get_smart_delay(source["name"])
            time.sleep(delay)

            # 尝试数据源
            df = source["func"]()

            # 记录成功请求
            anti_crawling.record_request(source["name"])
            # 数据获取成功

            # 根据数据源进行不同的列名映射
            if source["name"] == "fund_etf_spot_em":
                # 东方财富数据源
                column_mapping = {
                    "代码": "代码",
                    "名称": "名称",
                    "最新价": "最新价",
                    "涨跌幅": "涨跌幅",
                    "涨跌额": "涨跌额",
                    "昨收": "昨收",
                }
            elif source["name"] == "fund_etf_spot_ths":
                # 同花顺数据源
                column_mapping = {
                    "基金代码": "代码",
                    "基金名称": "名称",
                    "当前-单位净值": "最新价",
                    "增长率": "涨跌幅",
                    "增长值": "涨跌额",
                    "前一日-单位净值": "昨收",
                }
            else:
                # 默认映射
                column_mapping = {
                    "代码": "代码",
                    "名称": "名称",
                    "最新价": "最新价",
                    "涨跌幅": "涨跌幅",
                    "涨跌额": "涨跌额",
                    "昨收": "昨收",
                }

            # 重命名列
            df = df.rename(columns=column_mapping)

            # 根据数据源确定需要处理的数值列
            if source["name"] == "fund_etf_spot_ths":
                # 同花顺数据源没有成交额，只处理其他列
                numeric_cols = ["最新价", "昨收"]
            else:
                # 其他数据源
                numeric_cols = ["最新价", "昨收", "成交额"]

            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # 只对存在的列进行dropna
            available_cols = [col for col in numeric_cols if col in df.columns]
            df.dropna(subset=available_cols, inplace=True)
            # 涨跌幅数据处理：保持原始格式
            if "涨跌幅" in df.columns:
                df["涨跌幅"] = pd.to_numeric(df["涨跌幅"], errors="coerce")
                logger.info("✅ [ETF实时数据] 涨跌幅保持原始格式")
            else:
                # 如果没有涨跌幅列，则计算
                df["涨跌幅"] = 0.0
                mask = df["昨收"] != 0
                df.loc[mask, "涨跌幅"] = (
                    (df.loc[mask, "最新价"] - df.loc[mask, "昨收"])
                    / df.loc[mask, "昨收"]
                ) * 100
            return df

        except Exception as e:
            logger.warning(f"⚠️ [ETF实时数据] {source['description']} 获取失败: {e}")
            continue  # 尝试下一个数据源

    # 所有数据源都失败
    logger.error(f"💥 [ETF实时数据] 所有数据源都获取失败")
    return None


@retry(
    stop=stop_after_attempt(1),  # 只尝试1次，不重试（被ban了重试也没用）
    wait=wait_fixed(0),  # 不等待
    retry=retry_if_exception_type(()),  # 不重试任何异常
)
async def get_etf_daily_history(etf_code: str, data_type: str = "etf"):
    """获取单支ETF的历史日线数据（不重试，被ban直接失败）"""
    logger.info(
        f"🔍 [ETF历史数据] 正在获取 {etf_code} 的历史日线数据，类型: {data_type}"
    )

    async with get_request_semaphore():
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
                end_date=end_date,
            )

            # 记录成功请求
            anti_crawling.record_request(api_name)
            # 历史数据获取完成

            # 标准化列名
            if "收盘" in daily_df.columns:
                daily_df.rename(columns={"收盘": "close"}, inplace=True)
            if "最高" in daily_df.columns:
                daily_df.rename(columns={"最高": "high"}, inplace=True)
            if "最低" in daily_df.columns:
                daily_df.rename(columns={"最低": "low"}, inplace=True)
            if "日期" in daily_df.columns:
                daily_df.rename(columns={"日期": "date"}, inplace=True)

            # 涨跌幅数据处理：保持原始格式
            if "涨跌幅" in daily_df.columns:
                daily_df["涨跌幅"] = pd.to_numeric(daily_df["涨跌幅"], errors="coerce")
                logger.info("✅ [ETF历史数据] 涨跌幅保持原始格式")

            return daily_df
        except (
            ConnectionError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            logger.error(
                f"💥 [ETF历史数据] 获取 {etf_code} 日线数据时连接错误（已被限流/ban）: {e}"
            )
            # 不再重试，直接抛出异常
            raise e
        except Exception as e:
            logger.error(
                f"💥 [ETF历史数据] 获取 {etf_code} 日线数据时出错: {e}",
                exc_info=True,
            )
            raise e


@cached(cache)
async def get_etf_minute_history(etf_code: str, period: str = "60", days: int = 7):
    """
    获取单支ETF的分钟线历史数据 (带自动重试)

    参数:
        etf_code: ETF代码
        period: 分钟周期，可选值: "1", "5", "15", "30", "60"
        days: 获取最近N天的数据，默认7天以提供更多历史数据

    返回:
        DataFrame: 分钟线数据
    """
    logger.info(
        f"🔍 [ETF分钟线] 正在获取 {etf_code} 的{period}分钟线数据，最近{days}天"
    )

    async with get_request_semaphore():
        try:
            # 应用智能延迟控制
            api_name = f"fund_etf_hist_min_em_{etf_code}_{period}"
            delay = anti_crawling.get_smart_delay(api_name)
            await asyncio.sleep(delay)

            # 计算时间范围
            from datetime import datetime, timedelta

            end_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            start_date = (datetime.now() - timedelta(days=days)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # 调用分钟线历史数据接口
            minute_df = await asyncio.to_thread(
                ak.fund_etf_hist_min_em,
                symbol=etf_code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )

            # 记录成功请求
            anti_crawling.record_request(api_name)

            # 标准化列名
            if "收盘" in minute_df.columns:
                minute_df.rename(columns={"收盘": "close"}, inplace=True)
            if "最高" in minute_df.columns:
                minute_df.rename(columns={"最高": "high"}, inplace=True)
            if "最低" in minute_df.columns:
                minute_df.rename(columns={"最低": "low"}, inplace=True)
            if "时间" in minute_df.columns:
                minute_df.rename(columns={"时间": "date"}, inplace=True)
            if "成交量" in minute_df.columns:
                minute_df.rename(columns={"成交量": "volume"}, inplace=True)

            # 确保有close列
            if "close" not in minute_df.columns:
                logger.warning(f"⚠️ [ETF分钟线] {etf_code} 数据缺少close列")
                return pd.DataFrame()

            # 删除空值行
            minute_df.dropna(subset=["close"], inplace=True)

            logger.info(
                f"✅ [ETF分钟线] 获取成功: {etf_code}, 数据量: {len(minute_df)}条"
            )
            return minute_df

        except (
            ConnectionError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            logger.error(f"💥 [ETF分钟线] 获取 {etf_code} 分钟线数据时连接错误: {e}")
            extra_delay = random.uniform(5, 10)
            await asyncio.sleep(extra_delay)
            raise e
        except Exception as e:
            logger.error(
                f"💥 [ETF分钟线] 获取 {etf_code} 分钟线数据时出错: {e}", exc_info=True
            )
            raise e


async def get_stock_minute_history(stock_code: str, period: str = "60", days: int = 7):
    """
    获取单支股票的分钟线历史数据 (带自动重试)

    参数:
        stock_code: 股票代码
        period: 分钟周期，可选值: "1", "5", "15", "30", "60"
        days: 获取最近N天的数据，默认7天

    返回:
        DataFrame: 分钟线数据
    """
    logger.info(
        f"🔍 [股票分钟线] 正在获取 {stock_code} 的{period}分钟线数据，最近{days}天"
    )

    async with get_request_semaphore():
        try:
            # 应用智能延迟控制
            api_name = f"stock_zh_a_hist_min_em_{stock_code}_{period}"
            delay = anti_crawling.get_smart_delay(api_name)
            await asyncio.sleep(delay)

            # 计算时间范围
            from datetime import datetime, timedelta

            end_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            start_date = (datetime.now() - timedelta(days=days)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # 调用分钟线历史数据接口
            minute_df = await asyncio.to_thread(
                ak.stock_zh_a_hist_min_em,
                symbol=stock_code,
                period=period,
                adjust="qfq",
                start_date=(datetime.now() - timedelta(days=days)).strftime(
                    "%Y-%m-%d 09:30:00"
                ),
                end_date=datetime.now().strftime("%Y-%m-%d 15:00:00"),
            )

            # 记录成功请求
            anti_crawling.record_request(api_name)

            # 标准化列名
            if "收盘" in minute_df.columns:
                minute_df.rename(columns={"收盘": "close"}, inplace=True)
            if "最高" in minute_df.columns:
                minute_df.rename(columns={"最高": "high"}, inplace=True)
            if "最低" in minute_df.columns:
                minute_df.rename(columns={"最低": "low"}, inplace=True)
            if "时间" in minute_df.columns:
                minute_df.rename(columns={"时间": "date"}, inplace=True)
            if "成交量" in minute_df.columns:
                minute_df.rename(columns={"成交量": "volume"}, inplace=True)

            # 确保有close列
            if "close" not in minute_df.columns:
                logger.warning(f"⚠️ [股票分钟线] {stock_code} 数据缺少close列")
                return pd.DataFrame()

            # 删除空值行
            minute_df.dropna(subset=["close"], inplace=True)

            logger.info(f"✅ [股票分钟线] 获取成功: {stock_code}")
            return minute_df

        except (
            ConnectionError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            logger.error(f"💥 [股票分钟线] 获取 {stock_code} 分钟线数据时连接错误: {e}")
            extra_delay = random.uniform(5, 10)
            await asyncio.sleep(extra_delay)
            raise e
        except Exception as e:
            logger.error(
                f"💥 [股票分钟线] 获取 {stock_code} 分钟线数据时出错: {e}",
                exc_info=True,
            )
            raise e


@cached(cache)
def get_all_stock_spot_realtime():
    """获取所有A股的实时行情数据 (带缓存)"""
    logger.info("正在从AKShare获取所有A股实时数据...(缓存有效期: %s秒)", CACHE_EXPIRE)
    try:
        api_name = "stock_zh_a_spot_em"
        delay = anti_crawling.get_smart_delay(api_name)
        time.sleep(delay)

        df = ak.stock_zh_a_spot_em()

        anti_crawling.record_request(api_name)

        column_mapping = {
            "代码": "代码",
            "名称": "名称",
            "最新价": "最新价",
            "涨跌幅": "涨跌幅",
            "涨跌额": "涨跌额",
            "昨收": "昨收",
        }

        df = df.rename(columns=column_mapping)

        numeric_cols = ["最新价", "昨收", "成交额"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df.dropna(subset=numeric_cols, inplace=True)

        if "涨跌幅" in df.columns:
            df["涨跌幅"] = pd.to_numeric(df["涨跌幅"], errors="coerce")
            logger.info("✅ [股票实时数据] 涨跌幅保持原始格式")
        else:
            df["涨跌幅"] = 0.0
            mask = df["昨收"] != 0
            df.loc[mask, "涨跌幅"] = (
                (df.loc[mask, "最新价"] - df.loc[mask, "昨收"]) / df.loc[mask, "昨收"]
            ) * 100

        return df
    except Exception as e:
        logger.error(f"💥 [股票实时数据] 获取失败: {e}", exc_info=True)
        return None


@retry(
    stop=stop_after_attempt(1),  # 只尝试1次，不重试（被ban了重试也没用）
    wait=wait_fixed(0),  # 不等待
    retry=retry_if_exception_type(()),  # 不重试任何异常
)
async def get_stock_daily_history(stock_code: str, data_type: str = "stock"):
    """获取单支股票的历史日线数据（不重试，被ban直接失败）"""
    logger.info(
        f"🔍 [股票历史数据] 正在获取 {stock_code} 的历史日线数据，类型: {data_type}"
    )

    async with get_request_semaphore():
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
                adjust="qfq",
                start_date=start_date,
                end_date=end_date,
            )

            anti_crawling.record_request(api_name)

            if "收盘" in daily_df.columns:
                daily_df.rename(columns={"收盘": "close"}, inplace=True)
            if "最高" in daily_df.columns:
                daily_df.rename(columns={"最高": "high"}, inplace=True)
            if "最低" in daily_df.columns:
                daily_df.rename(columns={"最低": "low"}, inplace=True)
            if "日期" in daily_df.columns:
                daily_df.rename(columns={"日期": "date"}, inplace=True)

            logger.info(f"✅ [股票历史数据] 获取成功: {stock_code}")
            return daily_df
        except (
            ConnectionError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            logger.error(
                f"💥 [股票历史数据] 获取 {stock_code} 日线数据时连接错误（已被限流/ban）: {e}"
            )
            # 不再重试，直接抛出异常
            raise e
        except Exception as e:
            logger.error(
                f"💥 [股票历史数据] 获取 {stock_code} 日线数据时出错: {e}",
                exc_info=True,
            )
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
