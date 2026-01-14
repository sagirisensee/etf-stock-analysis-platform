import asyncio
import logging
import random
import time
import pandas as pd
from .data_fetcher import (
    get_all_etf_spot_realtime,
    get_etf_daily_history,
    get_etf_minute_history,
    get_all_stock_spot_realtime,
    get_stock_daily_history,
    get_stock_minute_history,
)
from .llm_analyzer import get_llm_score_and_analysis
from .llm_analyzer import extract_signal_from_comment
from .indicators import analyze_ma, analyze_macd, analyze_bollinger
from .indicators import (
    analyze_rsi,
    analyze_kdj,
    analyze_cci,
    analyze_obv,
    analyze_williams,
)
from .indicators import calculate_forward_indicators
from .indicators import calculate_minute_indicators
from .indicators import calculate_minute_support_resistance
from .indicators import calculate_entry_signals
from .indicators import judge_trend_status
from .indicators import calculate_macd_for_eastmoney
from .signal_system import SignalSystem
from .predictor import PricePredictor, PricePredictorDebug
from .alert_system import AlertSystem

logger = logging.getLogger(__name__)
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)


def _create_realtime_data_from_history(daily_trends_list, core_pool):
    """
    当实时数据获取失败时，使用历史数据的最新价格创建实时数据
    """
    try:
        logger.info("🔄 正在从历史数据创建实时数据...")

        realtime_data = []
        for item in core_pool:
            code = item["code"]
            name = item["name"]
            item_type = item.get("type", "stock")  # 获取标的类型

            # 查找对应的历史数据
            history_data = None
            for trend in daily_trends_list:
                if trend["code"] == code:
                    history_data = trend.get("raw_debug_data", {}).get("history_data")
                    break

            if history_data is not None and not history_data.empty:
                # 使用最新一天的数据作为实时数据
                latest = history_data.iloc[-1]

                # 涨跌幅统一处理：直接使用原始数据
                change_pct = latest.get("涨跌幅", 0)

                realtime_data.append(
                    {
                        "代码": code,
                        "名称": name,
                        "最新价": latest.get("close", 0),
                        "涨跌幅": change_pct,
                        "涨跌额": latest.get("涨跌额", 0),
                        "昨收": latest.get("close", 0),  # 使用收盘价作为昨收
                    }
                )
                logger.info(
                    f"✅ 从历史数据创建实时数据: {name}({code}) - 价格: {latest.get('close', 0)}"
                )
            else:
                logger.warning(f"⚠️ 无法找到 {name}({code}) 的历史数据")

        if realtime_data:
            df = pd.DataFrame(realtime_data)
            logger.info(f"✅ 成功创建实时数据，包含 {len(df)} 个标的")
            return df
        else:
            logger.error("❌ 无法从历史数据创建任何实时数据")
            return None

    except Exception as e:
        logger.error(f"❌ 从历史数据创建实时数据失败: {e}", exc_info=True)
        return None


async def generate_ai_driven_report(
    get_realtime_data_func, get_daily_history_func, core_pool
):
    logger.info("启动AI驱动的统一全面分析引擎...")
    final_report = []
    start_time = time.time()
    MAX_ANALYSIS_TIME = 600  # 10分钟超时

    try:
        # 并行获取实时数据和历史数据，添加超时控制
        realtime_data_df_task = asyncio.to_thread(get_realtime_data_func)
        daily_trends_task = _get_daily_trends_generic(get_daily_history_func, core_pool)

        try:
            # 设置超时：10分钟
            realtime_data_df, daily_trends_list = await asyncio.wait_for(
                asyncio.gather(
                    realtime_data_df_task, daily_trends_task, return_exceptions=True
                ),
                timeout=MAX_ANALYSIS_TIME,
            )
        except asyncio.TimeoutError:
            logger.error(f"分析超时（超过{MAX_ANALYSIS_TIME}秒），停止分析")
            # 超时时，只返回已处理的标的，不返回错误报告
            return final_report if final_report else []
        except Exception as e:
            logger.error(f"数据获取过程中发生错误: {e}", exc_info=True)
            # 如果数据获取失败，不返回错误报告，直接返回空列表
            return []

        # 处理实时数据获取结果
        if isinstance(realtime_data_df, Exception):
            logger.error(f"实时数据获取失败: {realtime_data_df}")
            realtime_data_df = None
        elif realtime_data_df is None:
            logger.warning("实时数据获取失败，尝试使用历史数据作为替代")

        # 处理历史数据获取结果
        if isinstance(daily_trends_list, Exception):
            logger.error(f"历史数据获取失败: {daily_trends_list}")
            daily_trends_list = []
        elif daily_trends_list is None:
            logger.warning("历史数据获取失败，使用空列表")
            daily_trends_list = []

        # 如果实时数据为空，尝试使用历史数据创建
        if realtime_data_df is None or (
            isinstance(realtime_data_df, pd.DataFrame) and realtime_data_df.empty
        ):
            logger.warning("实时数据为空，尝试使用历史数据创建")
            realtime_data_df = _create_realtime_data_from_history(
                daily_trends_list, core_pool
            )
            if realtime_data_df is None or (
                isinstance(realtime_data_df, pd.DataFrame) and realtime_data_df.empty
            ):
                logger.error(
                    "无法获取实时数据，也无法从历史数据创建，将使用空DataFrame继续分析"
                )
                # 创建空DataFrame，但确保有正确的列结构
                realtime_data_df = pd.DataFrame(
                    columns=["代码", "名称", "最新价", "涨跌幅"]
                )

        daily_trends_map = {item["code"]: item for item in daily_trends_list}

        # 根据core_pool中的type字段判断，而不是根据函数引用
        if core_pool and core_pool[0].get("type") == "stock":
            item_type = "stock"
        else:
            item_type = "etf"

        # 生成日内信号
        try:
            intraday_analyzer = _IntradaySignalGenerator(core_pool, item_type=item_type)
            intraday_signals = intraday_analyzer.generate_signals(realtime_data_df)
        except Exception as e:
            logger.error(f"生成日内信号时发生错误: {e}", exc_info=True)
            # 如果信号生成失败，为每个标的创建基础信号
            intraday_signals = []
            for item in core_pool:
                intraday_signals.append(
                    {
                        "code": item.get("code", ""),
                        "name": item.get("name", "未知"),
                        "price": None,
                        "change": 0,
                        "涨跌幅": 0,
                        "analysis_points": [f"信号生成失败: {str(e)}"],
                    }
                )

        # 处理每个标的的分析
        for i, signal in enumerate(intraday_signals):
            # 检查是否超时
            elapsed_time = time.time() - start_time
            if elapsed_time > MAX_ANALYSIS_TIME:
                logger.warning(
                    f"分析超时（已用时 {elapsed_time:.1f}秒），停止处理剩余标的"
                )
                break

            code = signal.get("code", "")
            name = signal.get("name", "未知")

            try:
                # 获取历史趋势数据
                daily_trend = daily_trends_map.get(
                    code,
                    {"status": "🟡 数据状态未知", "technical_indicators_summary": []},
                )

                # 检查数据是否充足：如果状态是数据不足或数据缺失，跳过不写入
                daily_trend_status = daily_trend.get("status", "")
                if not daily_trend_status:
                    daily_trend_status = "🟡 数据状态未知"

                # 如果数据不足，跳过不写入分析结果
                if any(
                    keyword in daily_trend_status
                    for keyword in [
                        "数据不足",
                        "数据缺失",
                        "数据状态未知",
                        "数据获取失败",
                        "分析失败",
                        "数据源暂时不可用",
                    ]
                ):
                    logger.info(f"跳过 {name}({code})：数据不足，不写入分析结果")
                    continue

                # 检查实时数据是否有效
                price = signal.get("price")
                if price is None:
                    logger.info(
                        f"跳过 {name}({code})：实时价格数据缺失，不写入分析结果"
                    )
                    continue

                # 获取前瞻性数据
                forward_indicators = daily_trend.get("raw_debug_data", {}).get(
                    "forward_indicators", {}
                )
                signal_data = daily_trend.get("signal_data", {})
                alert_data = daily_trend.get("alert_data", {})
                prediction_data = daily_trend.get("prediction_data", {})

                # 获取当前价格（用于支撑阻力计算）
                current_price = signal.get("price", 0)

                # 获取分钟线数据（仅对ETF）
                minute_30_data = None
                minute_60_data = None
                minute_support_resistance = {}
                minute_entry_signals = {}

                try:
                    if item_type == "etf":
                        # 获取30分钟线数据
                        minute_30_data = await asyncio.wait_for(
                            get_etf_minute_history(code, period="30", days=7),
                            timeout=30,
                        )
                        # 获取60分钟线数据
                        minute_60_data = await asyncio.wait_for(
                            get_etf_minute_history(code, period="60", days=7),
                            timeout=30,
                        )
                    elif item_type == "stock":
                        # 获取30分钟线数据
                        minute_30_data = await asyncio.wait_for(
                            get_stock_minute_history(code, period="30", days=7),
                            timeout=30,
                        )
                        # 获取60分钟线数据
                        minute_60_data = await asyncio.wait_for(
                            get_stock_minute_history(code, period="60", days=7),
                            timeout=30,
                        )
                    # 计算技术指标
                    if minute_30_data is not None and not minute_30_data.empty:
                        minute_30_data = calculate_minute_indicators(
                            minute_30_data, period="30"
                        )
                    # 计算技术指标
                    if minute_60_data is not None and not minute_60_data.empty:
                        minute_60_data = calculate_minute_indicators(
                            minute_60_data, period="60"
                        )

                    # 计算支撑阻力位和入场信号（需要两个周期都有数据）
                    if (
                        minute_30_data is not None
                        and not minute_30_data.empty
                        and minute_60_data is not None
                        and not minute_60_data.empty
                    ):
                        minute_support_resistance = calculate_minute_support_resistance(
                            minute_30_data, minute_60_data, current_price
                        )

                        # 计算入场信号
                        minute_entry_signals = calculate_entry_signals(
                            minute_30_data,
                            minute_60_data,
                            minute_support_resistance,
                            current_price,
                        )
                except asyncio.TimeoutError:
                    logger.warning(f"获取{name}({code})分钟线数据超时")
                except Exception as e:
                    logger.warning(f"获取{name}({code})分钟线数据失败: {e}")

                # 调用LLM分析（传入多周期数据）
                try:
                    ai_result = await asyncio.wait_for(
                        get_llm_score_and_analysis(
                            signal,
                            daily_trend,
                            forward_indicators_data=forward_indicators,
                            minute_30_data=minute_30_data,
                            minute_60_data=minute_60_data,
                            minute_support_resistance=minute_support_resistance,
                            minute_entry_signals=minute_entry_signals,
                            signal_data=signal_data,
                            alert_data=alert_data,
                            prediction_data=prediction_data,
                        ),
                        timeout=60,  # LLM分析单次超时60秒
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"LLM分析 {name}({code}) 超时，跳过")
                    continue
                except Exception as e:
                    logger.error(f"LLM分析 {name}({code}) 时发生错误: {e}")
                    # LLM分析失败时，跳过不写入
                    continue

                # 只有数据充足时才写入分析结果
                final_report.append(
                    {
                        **signal,
                        "ai_signal": ai_result.get("signal", "持有"),
                        "ai_confidence": ai_result.get("confidence", 50),
                        "ai_probability": ai_result.get("probability", "涨跌概率未知"),
                        "ai_detailed_probability": ai_result.get(
                            "detailed_probability", {}
                        ),
                        "ai_pred_1d": ai_result.get("pred_1d", {}),
                        "ai_pred_3d": ai_result.get("pred_3d", {}),
                        "ai_support": ai_result.get("support", "未知"),
                        "ai_resistance": ai_result.get("resistance", "未知"),
                        "ai_target": ai_result.get("target", "未知"),
                        "ai_stop_loss": ai_result.get("stop_loss", "未知"),
                        "ai_comment": ai_result.get("comment", "AI分析完成"),
                        "daily_trend_status": daily_trend_status,
                        "technical_indicators_summary": daily_trend.get(
                            "technical_indicators_summary", []
                        ),
                        # 新增：前瞻性指标数据
                        "forward_indicators": forward_indicators,
                        # 新增：买卖信号数据
                        "signal_data": signal_data,
                        # 价格预测数据（使用纯技术指标预测，用于参考）
                        "prediction_data": prediction_data,
                        # 新增：预警数据
                        "alert_data": alert_data,
                        # 标记使用AI驱动的概率
                        "use_ai_probability": True,
                    }
                )

            except Exception as e:
                logger.error(f"处理 {name}({code}) 分析时发生错误: {e}")
                # 发生错误时，跳过不写入错误报告
                continue

            # 随机延迟，但检查超时
            delay = random.uniform(1.0, 2.5)
            if elapsed_time + delay > MAX_ANALYSIS_TIME:
                break
            await asyncio.sleep(delay)

    except Exception as e:
        logger.error(f"分析过程中发生严重错误: {e}", exc_info=True)
        # 发生严重错误时，不返回错误报告，直接返回已处理的结果
        return final_report if final_report else []

    # 按AI评分排序，只返回有效的分析结果
    try:
        if not final_report:
            return []
        return sorted(
            final_report,
            key=lambda x: (
                -x.get("ai_score", 0)
                if isinstance(x.get("ai_score"), (int, float))
                else 0
            ),
            reverse=True,
        )
    except Exception as e:
        logger.error(f"排序结果时发生错误: {e}")
        return final_report if final_report else []


async def _get_daily_trends_generic(get_daily_history_func, core_pool):
    analysis_report = []
    start_time = time.time()
    MAX_DATA_FETCH_TIME = 480  # 8分钟超时（给分析留出时间）

    # 开始获取历史数据
    for i, item_info in enumerate(core_pool):
        # 检查超时
        elapsed_time = time.time() - start_time
        if elapsed_time > MAX_DATA_FETCH_TIME:
            logger.warning(
                f"历史数据获取超时（已用时 {elapsed_time:.1f}秒），停止获取剩余标的"
            )
            break

        code = item_info["code"]
        name = item_info["name"]
        item_type = item_info.get("type", "stock")

        try:
            # 调用数据获取函数，添加单次超时控制
            try:
                result = await asyncio.wait_for(
                    get_daily_history_func(code, item_type),
                    timeout=120,  # 单个标的数据获取超时2分钟
                )
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ {name}({code}) 历史数据获取超时，跳过")
                continue
            except Exception as e:
                logger.error(f"💥 {name}({code}) 历史数据获取异常: {e}")
                # 数据获取失败时，跳过不写入
                continue

            # 历史数据获取结果检查
            if result is None:
                logger.info(f"跳过 {name}({code})：历史数据返回None")
                continue
            elif result.empty:
                logger.info(f"跳过 {name}({code})：历史数据为空")
                continue
            else:
                # 数据获取成功
                pass

            # 字段标准化
            if "收盘" in result.columns:
                result.rename(columns={"收盘": "close"}, inplace=True)
            elif "close" not in result.columns and "Close" in result.columns:
                result.rename(columns={"Close": "close"}, inplace=True)

            if "最高" in result.columns:
                result.rename(columns={"最高": "high"}, inplace=True)
            elif "high" not in result.columns and "High" in result.columns:
                result.rename(columns={"High": "high"}, inplace=True)

            if "最低" in result.columns:
                result.rename(columns={"最低": "low"}, inplace=True)
            elif "low" not in result.columns and "Low" in result.columns:
                result.rename(columns={"Low": "low"}, inplace=True)

            if "日期" in result.columns:
                result["日期"] = pd.to_datetime(result["日期"])
                result.set_index("日期", inplace=True)
            elif "date" in result.columns:
                result["date"] = pd.to_datetime(result["date"])
                result.set_index("date", inplace=True)
            result.index.name = None
            result["close"] = pd.to_numeric(result["close"], errors="coerce")
            if "high" in result.columns:
                result["high"] = pd.to_numeric(result["high"], errors="coerce")
            if "low" in result.columns:
                result["low"] = pd.to_numeric(result["low"], errors="coerce")
            if "close" not in result.columns:
                logger.info(f"跳过 {name}({code})：缺少必要的'close'列")
                continue
            if len(result) < 61:
                logger.info(
                    f"跳过 {name}({code})：历史数据不足61天（实际{len(result)}天）"
                )
                continue
            if result["close"].isnull().all():
                logger.info(f"跳过 {name}({code})：'close'列数据全为空值")
                continue

            # 使用pandas内置功能计算技术指标
            result["SMA_5"] = result["close"].rolling(window=5).mean()
            result["SMA_10"] = result["close"].rolling(window=10).mean()
            result["SMA_20"] = result["close"].rolling(window=20).mean()

            # MACD计算 - 使用talib风格以匹配东方财富
            dif, dea, macd_bar = calculate_macd_for_eastmoney(result["close"])
            result["MACD_12_26_9"] = dif  # DIF
            result["MACDs_12_26_9"] = dea  # DEA (信号线)
            result["MACDh_12_26_9"] = macd_bar  # MACD柱（已×2）

            # 简化的布林带计算
            result["BBM_20_2.0"] = result["close"].rolling(window=20).mean()
            std = result["close"].rolling(window=20).std()
            result["BBU_20_2.0"] = result["BBM_20_2.0"] + (std * 2)
            result["BBL_20_2.0"] = result["BBM_20_2.0"] - (std * 2)

            # 计算前瞻性技术指标（RSI、KDJ、CCI、OBV、威廉指标）
            result = calculate_forward_indicators(result)

            # 添加成交量列（如果有的话）
            if "volume" not in result.columns and "成交量" in result.columns:
                result["volume"] = result["成交量"]

            if len(result) < 2:
                logger.info(
                    f"跳过 {name}({code})：历史数据不足2天（实际{len(result)}天）"
                )
                continue
            latest = result.iloc[-1]
            prev_latest = result.iloc[-2]
            trend_signals = []

            # 分析传统指标
            analyze_ma(result, latest, prev_latest, trend_signals)
            analyze_macd(result, latest, prev_latest, trend_signals)
            analyze_bollinger(result, latest, prev_latest, trend_signals)

            # 分析前瞻性指标
            analyze_rsi(result, latest, prev_latest, trend_signals)
            analyze_kdj(result, latest, prev_latest, trend_signals)
            analyze_cci(result, latest, prev_latest, trend_signals)
            analyze_obv(result, latest, prev_latest, trend_signals)
            analyze_williams(result, latest, prev_latest, trend_signals)

            # --- 状态判定 ---
            status = judge_trend_status(latest, prev_latest)

            # --- 预测和预警系统 ---
            # 初始化价格预测系统（使用调试版）
            price_predictor = PricePredictorDebug()

            # 生成价格预测（不再依赖signal_data）
            prediction_data = price_predictor.predict_price(result, latest, None)

            # 初始化预警系统
            alert_system = AlertSystem()

            # 生成预警信息（不再依赖signal_data）
            alert_data = alert_system.generate_alerts(result, latest, prev_latest, None)

            # 信号系统由AI决策，不再使用规则系统
            signal_data = {}

            # 分析完成

            analysis_report.append(
                {
                    **item_info,
                    "status": status,
                    "technical_indicators_summary": trend_signals,
                    "raw_debug_data": {
                        "history_data": result,  # 保存历史数据用于创建实时数据
                        "forward_indicators": {
                            "RSI_12": latest.get("RSI_12"),
                            "KDJ_K": latest.get("KDJ_K"),
                            "KDJ_D": latest.get("KDJ_D"),
                            "KDJ_J": latest.get("KDJ_J"),
                            "CCI_14": latest.get("CCI_14"),
                            "OBV": latest.get("OBV"),
                            "OBV_change": (
                                latest.get("OBV", 0) - prev_latest.get("OBV", 0)
                            )
                            if pd.notna(latest.get("OBV"))
                            else None,
                            "WR1": latest.get("WR1"),
                            "WR2": latest.get("WR2"),
                        },
                    },
                    "signal_data": signal_data,  # 买卖信号数据
                    "prediction_data": prediction_data,  # 价格预测数据
                    "alert_data": alert_data,  # 预警数据
                }
            )
        except Exception as e:
            # 发生错误时，跳过不写入分析结果，只记录日志
            error_type = str(e)
            if (
                "RetryError" in error_type
                or "ConnectionError" in error_type
                or "RemoteDisconnected" in error_type
            ):
                logger.info(f"跳过 {name}({code})：网络连接问题，数据获取失败")
            elif "Timeout" in error_type:
                logger.info(f"跳过 {name}({code})：数据获取超时")
            else:
                logger.info(f"跳过 {name}({code})：分析过程出错 - {type(e).__name__}")
            # 不写入错误报告，直接跳过
            continue
    return analysis_report


class _IntradaySignalGenerator:
    def __init__(self, item_list, item_type):
        self.item_list = item_list
        self.item_type = item_type

    def generate_signals(self, all_item_data_df):
        results = []
        # 如果数据框为空，为所有标的创建基础信号
        if all_item_data_df is None or all_item_data_df.empty:
            logger.warning("实时数据为空，为所有标的创建基础信号")
            for item in self.item_list:
                results.append(
                    {
                        "code": item.get("code", ""),
                        "name": item.get("name", "未知"),
                        "price": None,
                        "change": 0,
                        "涨跌幅": 0,
                        "analysis_points": ["实时数据获取失败，无法进行日内信号分析"],
                    }
                )
            return results

        # 检查数据框是否有必要的列
        if "代码" not in all_item_data_df.columns:
            logger.warning("实时数据缺少'代码'列，为所有标的创建基础信号")
            for item in self.item_list:
                results.append(
                    {
                        "code": item.get("code", ""),
                        "name": item.get("name", "未知"),
                        "price": None,
                        "change": 0,
                        "涨跌幅": 0,
                        "analysis_points": ["实时数据格式异常，无法进行日内信号分析"],
                    }
                )
            return results

        # 正常处理：为每个标的生成信号
        for item in self.item_list:
            code = item.get("code", "")
            name = item.get("name", "未知")

            try:
                item_data_row = all_item_data_df[all_item_data_df["代码"] == code]
                if not item_data_row.empty:
                    current_data = item_data_row.iloc[0]
                    results.append(self._create_signal_dict(current_data, item))
                else:
                    # 如果找不到该标的的数据，创建基础信号
                    logger.warning(
                        f"标的 {name}({code}) 在实时数据中未找到，创建基础信号"
                    )
                    results.append(
                        {
                            "code": code,
                            "name": name,
                            "price": None,
                            "change": 0,
                            "涨跌幅": 0,
                            "analysis_points": [
                                "实时数据中未找到该标的，无法进行日内信号分析"
                            ],
                        }
                    )
            except Exception as e:
                # 如果处理过程中出错，创建错误信号
                logger.error(f"处理标的 {name}({code}) 信号时出错: {e}")
                results.append(
                    {
                        "code": code,
                        "name": name,
                        "price": None,
                        "change": 0,
                        "涨跌幅": 0,
                        "analysis_points": [f"信号生成失败: {str(e)[:100]}"],
                    }
                )

        return results

    def _create_signal_dict(self, item_series, item_info):
        points = []
        code = item_series.get("代码")
        raw_change = item_series.get("涨跌幅", 0)
        # 根据标的类型处理涨跌幅
        # 涨跌幅统一处理：直接使用原始数据
        change = raw_change
        if change > 2.5:
            points.append("日内大幅上涨")
        if change < -2.5:
            points.append("日内大幅下跌")
        return {
            "code": code,
            "name": item_info.get("name"),
            "price": item_series.get("最新价"),
            "change": change,
            "涨跌幅": change,  # 添加涨跌幅字段，与前端保持一致
            "analysis_points": points if points else ["盘中信号平稳"],
        }


async def get_detailed_analysis_report_for_debug(
    get_realtime_data_func, get_daily_history_func, core_pool
):
    logger.info("启动AI驱动的调试分析引擎，不调用LLM...")
    realtime_data_df_task = asyncio.to_thread(get_realtime_data_func)
    daily_trends_task = _get_daily_trends_generic(get_daily_history_func, core_pool)
    realtime_data_df, daily_trends_list = await asyncio.gather(
        realtime_data_df_task, daily_trends_task
    )
    if realtime_data_df is None:
        return [
            {"name": "错误", "code": "", "ai_comment": "获取实时数据失败，无法分析。"}
        ]
    daily_trends_map = {item["code"]: item for item in daily_trends_list}
    if get_realtime_data_func == get_all_stock_spot_realtime:
        item_type = "stock"
    else:
        item_type = "etf"
    intraday_analyzer = _IntradaySignalGenerator(core_pool, item_type=item_type)
    intraday_signals = intraday_analyzer.generate_signals(realtime_data_df)
    debug_report = []
    for i, signal in enumerate(intraday_signals):
        code = signal["code"]
        name = signal["name"]
        logger.info(f"正在准备调试报告: {name} ({i + 1}/{len(intraday_signals)})")
        daily_trend_info = daily_trends_map.get(
            code,
            {
                "status": "未知",
                "technical_indicators_summary": [],
                "raw_debug_data": {},
            },
        )
        raw_debug_data = daily_trend_info.get("raw_debug_data", {})
        if not raw_debug_data:
            raw_debug_data = {}
        debug_report.append(
            {
                "code": code,
                "name": name,
                "price": signal.get("price"),
                "change": signal.get("change"),
                "intraday_signals": signal.get("analysis_points"),
                "daily_trend_status": daily_trend_info.get("status"),
                "technical_indicators_summary": daily_trend_info.get(
                    "technical_indicators_summary"
                ),
                "raw_debug_data": raw_debug_data,
            }
        )
        await asyncio.sleep(random.uniform(0.5, 1.0))
    return debug_report
