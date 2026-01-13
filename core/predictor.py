"""
价格预测系统 - 基于技术指标的历史数据预测未来价格趋势
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class PricePredictor:
    """
    价格预测系统
    基于技术指标和历史数据进行短期价格预测（1-3天）
    """

    def __init__(self):
        self.prediction_days = [1, 2, 3]  # 预测未来1、2、3天
        self.confidence_levels = ["low", "medium", "high"]

    def predict_price(self, historical_data, latest, signal_data=None):
        """
        预测未来价格

        参数:
            historical_data: 历史数据DataFrame
            latest: 最新一天的数据
            signal_data: 信号系统数据（可选）

        返回:
            dict: {
                'prediction_1d': {'high': 100, 'low': 95, 'target': 97.5, 'trend': '上涨', 'confidence': 'high'},
                'prediction_2d': {...},
                'prediction_3d': {...},
                'support_resistance': {'support': [90, 85], 'resistance': [105, 110]},
                'trend_probability': {'up': 60, 'down': 25, 'sideways': 15}
            }
        """
        try:
            current_price = latest.get("close")
            if pd.isna(current_price) or current_price <= 0:
                return self._empty_prediction()

            predictions = {}

            # 计算支撑阻力位
            support_resistance = self._calculate_support_resistance(
                historical_data, current_price
            )

            # 预测趋势概率
            trend_probability = self._predict_trend_probability(
                historical_data, latest, signal_data
            )

            # 预测未来1-3天的价格
            for day in self.prediction_days:
                prediction = self._predict_single_day(
                    historical_data, latest, day, support_resistance, trend_probability
                )
                predictions[f"prediction_{day}d"] = prediction

            return {
                "predictions": predictions,
                "support_resistance": support_resistance,
                "trend_probability": trend_probability,
                "current_price": current_price,
            }

        except Exception as e:
            logger.error(f"价格预测失败: {e}", exc_info=True)
            return self._empty_prediction()

    def _empty_prediction(self):
        """返回空预测结果"""
        return {
            "predictions": {},
            "support_resistance": {"support": [], "resistance": []},
            "trend_probability": {"up": 33, "down": 33, "sideways": 34},
            "current_price": None,
        }

    def _calculate_support_resistance(self, historical_data, current_price):
        """
        计算支撑位和阻力位
        """
        result, _ = self._calculate_support_resistance_debug(
            historical_data, current_price
        )
        return result

    def _calculate_support_resistance_debug(self, historical_data, current_price):
        """
        计算支撑位和阻力位（调试版，返回详细信息）

        返回: (结果, 调试信息)
        """
        debug_info = {}

        try:
            debug_info["input_data_length"] = (
                len(historical_data) if hasattr(historical_data, "__len__") else 0
            )

            if not isinstance(historical_data, pd.DataFrame):
                debug_info["error"] = "数据不是DataFrame类型"
                return {"support": [], "resistance": []}, debug_info

            if len(historical_data) < 20:
                debug_info["error"] = f"数据不足20天，只有{len(historical_data)}天"
                return {"support": [], "resistance": []}, debug_info

            # 获取 high/low 列，如果没有则使用 close
            if "high" in historical_data.columns:
                high_series = historical_data["high"]
            else:
                high_series = historical_data["close"]

            if "low" in historical_data.columns:
                low_series = historical_data["low"]
            else:
                low_series = historical_data["close"]

            recent_data = historical_data.iloc[-20:]
            high = float(high_series.iloc[-20:].max())
            low = float(low_series.iloc[-20:].min())
            close = float(historical_data["close"].iloc[-1])

            debug_info["recent_high"] = high
            debug_info["recent_low"] = low
            debug_info["current_close"] = close

            # 获取最新一行的Series
            latest = historical_data.iloc[-1]

            # 计算ATR（真实波动范围）
            if len(historical_data) >= 14:
                prev_close = historical_data["close"].shift(1)
                tr1 = high_series - low_series
                tr2 = (high_series - prev_close).abs()
                tr3 = (low_series - prev_close).abs()
                atr = (
                    pd.concat([tr1, tr2, tr3], axis=1)
                    .max(axis=1)
                    .rolling(14)
                    .mean()
                    .iloc[-1]
                )
            else:
                atr = (high - low) * 0.1  # 简化计算

            # 支撑位
            support_levels = []

            # 1. 近期低点
            support_levels.append(low)

            # 2. 布林下轨
            if "BBL_20_2.0" in latest.index:
                bb_lower = latest["BBL_20_2.0"]
                if pd.notna(bb_lower):
                    support_levels.append(bb_lower)

            # 3. 均线支撑（20日、60日）
            for ma_period in [20, 60]:
                ma_col = f"SMA_{ma_period}"
                if ma_col in latest.index:
                    ma_value = latest[ma_col]
                    if pd.notna(ma_value) and ma_value < current_price:
                        support_levels.append(ma_value)

            # 4. ATR支撑
            support_levels.append(current_price - atr * 1.5)
            support_levels.append(current_price - atr * 3)

            # 支撑位去重并排序（从小到大）
            support_levels = sorted(
                list(set([round(v, 2) for v in support_levels if v > 0]))
            )
            support_levels = [v for v in support_levels if v < current_price]

            # 阻力位
            resistance_levels = []

            # 1. 近期高点
            resistance_levels.append(high)

            # 2. 布林上轨
            if "BBU_20_2.0" in latest.index:
                bb_upper = latest["BBU_20_2.0"]
                if pd.notna(bb_upper):
                    resistance_levels.append(bb_upper)

            # 3. 均线阻力
            for ma_period in [5, 10, 20]:
                ma_col = f"SMA_{ma_period}"
                if ma_col in latest.index:
                    ma_value = latest[ma_col]
                    if pd.notna(ma_value) and ma_value > current_price:
                        resistance_levels.append(ma_value)

            # 4. ATR阻力
            resistance_levels.append(current_price + atr * 1.5)
            resistance_levels.append(current_price + atr * 3)

            # 阻力位去重并排序（从小到大）
            resistance_levels = sorted(
                list(set([round(v, 2) for v in resistance_levels if v > 0]))
            )
            resistance_levels = [v for v in resistance_levels if v > current_price]

            # 只保留最近的3个支撑位和3个阻力位
            support = support_levels[-3:] if len(support_levels) > 3 else support_levels
            resistance = (
                resistance_levels[:3]
                if len(resistance_levels) > 3
                else resistance_levels
            )

            return {
                "support": support,
                "resistance": resistance,
                "atr": atr if "atr" in locals() else None,
            }

        except Exception as e:
            logger.error(f"计算支撑阻力位失败: {e}")
            return {"support": [], "resistance": []}

    def _predict_trend_probability(self, historical_data, latest, signal_data):
        """
        预测趋势概率（上涨/下跌/横盘）

        基于以下因素：
        1. 技术指标信号
        2. 均线趋势
        3. 价格动量
        4. RSI、KDJ等指标
        """
        try:
            up_score = 0
            down_score = 0
            sideways_score = 10  # 基础横盘分数，确保不为0

            # 1. 技术指标信号（权重50%）
            if signal_data:
                signal_score = signal_data.get("signal_score", 50)
                if signal_score > 50:
                    up_score += (signal_score - 50) * 0.5
                elif signal_score < 50:
                    down_score += (50 - signal_score) * 0.5
                else:
                    sideways_score += 0.5

            # 2. 均线趋势（权重20%）
            if isinstance(latest, pd.Series):
                close = latest.get("close") if "close" in latest.index else None
                sma_5 = latest.get("SMA_5") if "SMA_5" in latest.index else None
                sma_10 = latest.get("SMA_10") if "SMA_10" in latest.index else None
                sma_20 = latest.get("SMA_20") if "SMA_20" in latest.index else None
            else:
                close = latest.get("close") if isinstance(latest, dict) else None
                sma_5 = latest.get("SMA_5") if isinstance(latest, dict) else None
                sma_10 = latest.get("SMA_10") if isinstance(latest, dict) else None
                sma_20 = latest.get("SMA_20") if isinstance(latest, dict) else None

            if pd.notna(sma_5) and pd.notna(sma_20):
                if pd.notna(close):
                    if close > sma_5 > sma_20:
                        up_score += 20
                    elif close < sma_5 < sma_20:
                        down_score += 20
                    else:
                        sideways_score += 20

            # 3. 价格动量（权重15%）
            if len(historical_data) >= 3:
                recent_changes = historical_data["close"].pct_change().tail(3)
                avg_change = recent_changes.mean()
                if avg_change > 0.005:  # 上涨超过0.5%
                    up_score += 15
                elif avg_change < -0.005:  # 下跌超过0.5%
                    down_score += 15
                else:
                    sideways_score += 15

            # 4. RSI指标（权重10%）
            rsi = latest.get("RSI_14")
            if pd.notna(rsi):
                if rsi < 40:
                    up_score += 10
                elif rsi > 60:
                    down_score += 10
                else:
                    sideways_score += 10

            # 5. KDJ指标（权重5%）
            kdj_k = latest.get("KDJ_K")
            kdj_d = latest.get("KDJ_D")
            if pd.notna(kdj_k) and pd.notna(kdj_d):
                if kdj_k < 20:
                    up_score += 5
                elif kdj_k > 80:
                    down_score += 5
                else:
                    sideways_score += 5

            # 归一化概率
            total = up_score + down_score + sideways_score
            if total > 0:
                up_prob = up_score / total
                down_prob = down_score / total
                sideways_prob = sideways_score / total
            else:
                up_prob = down_prob = sideways_prob = 0.333

            return {
                "up": round(up_prob * 100, 1),
                "down": round(down_prob * 100, 1),
                "sideways": round(sideways_prob * 100, 1),
            }

        except Exception as e:
            logger.error(f"预测趋势概率失败: {e}")
            return {"up": 33, "down": 33, "sideways": 34}

    def _predict_single_day(
        self, historical_data, latest, day, support_resistance, trend_probability
    ):
        """
        预测单日价格

        参数:
            historical_data: 历史数据
            latest: 最新数据
            day: 预测天数
            support_resistance: 支撑阻力位
            trend_probability: 趋势概率

        返回:
            dict: {
                'high': 预测最高价,
                'low': 预测最低价,
                'target': 预测目标价,
                'trend': '上涨/下跌/横盘',
                'confidence': 'low/medium/high'
            }
        """
        try:
            current_price = latest.get("close")

            # 计算历史波动率
            if len(historical_data) >= 20:
                volatility = historical_data["close"].pct_change().tail(
                    20
                ).std() * np.sqrt(252)  # 年化波动率
                daily_volatility = volatility / np.sqrt(252)  # 日波动率
            else:
                daily_volatility = 0.02  # 默认2%日波动率

            # 根据趋势概率调整预测方向
            up_prob = trend_probability.get("up", 33) / 100
            down_prob = trend_probability.get("down", 33) / 100
            sideways_prob = trend_probability.get("sideways", 34) / 100

            # 计算预期涨跌幅
            expected_change = (up_prob - down_prob) * daily_volatility * day

            # 计算预测目标价
            target_price = current_price * (1 + expected_change)

            # 计算价格区间（基于波动率）
            range_multiplier = 1.5  # 区间倍数
            high_price = target_price * (
                1 + range_multiplier * daily_volatility * np.sqrt(day)
            )
            low_price = target_price * (
                1 - range_multiplier * daily_volatility * np.sqrt(day)
            )

            # 考虑支撑阻力位
            resistance_levels = support_resistance.get("resistance", [])
            support_levels = support_resistance.get("support", [])

            # 如果预测接近阻力位，限制上涨空间
            if resistance_levels and high_price > resistance_levels[0]:
                high_price = min(high_price, resistance_levels[0] * 1.01)

            # 如果预测接近支撑位，限制下跌空间
            if support_levels and low_price < support_levels[-1]:
                low_price = max(low_price, support_levels[-1] * 0.99)

            # 判定趋势
            if up_prob > 50:
                trend = "上涨"
            elif down_prob > 50:
                trend = "下跌"
            else:
                trend = "横盘"

            # 计算置信度
            # 置信度基于预测方向的概率
            if trend == "上涨":
                confidence_score = int(up_prob)
            elif trend == "下跌":
                confidence_score = int(down_prob)
            else:  # 横盘
                confidence_score = int(sideways_prob)

            if confidence_score >= 60:
                confidence = "high"
            elif confidence_score >= 45:
                confidence = "medium"
            else:
                confidence = "low"

            return {
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "target": round(target_price, 2),
                "trend": trend,
                "confidence": confidence,
                "confidence_score": confidence_score,
                "trend_probability": trend_probability,
                "volatility": round(daily_volatility * 100, 2),  # 转换为百分比
            }

        except Exception as e:
            logger.error(f"预测单日价格失败: {e}")
            return {
                "high": None,
                "low": None,
                "target": None,
                "trend": "横盘",
                "confidence": "low",
            }


def generate_prediction_summary(prediction_data):
    """
    生成预测摘要文本

    参数:
        prediction_data: PricePredictor.predict_price() 返回的数据

    返回:
        str: 预测摘要
    """
    try:
        if not prediction_data.get("predictions"):
            return "价格预测数据不足"

        current_price = prediction_data.get("current_price")
        if pd.isna(current_price):
            return "当前价格数据缺失"

        trend_prob = prediction_data.get("trend_probability", {})
        up_prob = trend_prob.get("up", 0)
        down_prob = trend_prob.get("down", 0)
        sideways_prob = trend_prob.get("sideways", 0)

        predictions = prediction_data.get("predictions", {})
        pred_1d = predictions.get("prediction_1d", {})
        pred_3d = predictions.get("prediction_3d", {})

        support_resistance = prediction_data.get("support_resistance", {})

        # 生成摘要
        summary_parts = []

        # 当前价格
        summary_parts.append(f"当前价格：{current_price:.2f}")

        # 趋势判断
        if up_prob > down_prob:
            summary_parts.append(f"未来趋势偏向上涨（概率：{up_prob:.0f}%）")
        elif down_prob > up_prob:
            summary_parts.append(f"未来趋势偏向下跌（概率：{down_prob:.0f}%）")
        else:
            summary_parts.append(f"未来趋势偏向横盘（概率：{sideways_prob:.0f}%）")

        # 1日预测
        if pred_1d.get("target"):
            target_1d = pred_1d["target"]
            change_1d = ((target_1d - current_price) / current_price) * 100
            direction_1d = "上涨" if change_1d > 0 else "下跌"
            summary_parts.append(
                f"1日预测：{direction_1d}至{target_1d:.2f}（预期变化：{change_1d:+.2f}%）"
            )

        # 3日预测
        if pred_3d.get("target"):
            target_3d = pred_3d["target"]
            change_3d = ((target_3d - current_price) / current_price) * 100
            direction_3d = "上涨" if change_3d > 0 else "下跌"
            summary_parts.append(
                f"3日预测：{direction_3d}至{target_3d:.2f}（预期变化：{change_3d:+.2f}%）"
            )

        # 支撑阻力位
        support = support_resistance.get("support", [])
        resistance = support_resistance.get("resistance", [])

        if support:
            support_str = "、".join([f"{s:.2f}" for s in support[-2:]])
            summary_parts.append(f"主要支撑位：{support_str}")

        if resistance:
            resistance_str = "、".join([f"{r:.2f}" for r in resistance[:2]])
            summary_parts.append(f"主要阻力位：{resistance_str}")

        return "；".join(summary_parts) + "。"

    except Exception as e:
        logger.error(f"生成预测摘要失败: {e}")
        return "预测摘要生成失败"


class PricePredictorDebug(PricePredictor):
    """价格预测调试版 - 返回详细的调试信息"""

    def predict_price(self, historical_data, latest, signal_data=None):
        """预测未来价格（带调试信息）"""
        try:
            debug_info = {}

            current_price = latest.get("close")
            if pd.isna(current_price) or current_price <= 0:
                return self._empty_prediction_debug()

            predictions = {}

            support_resistance, sr_debug = self._calculate_support_resistance_debug(
                historical_data, current_price
            )
            debug_info["support_resistance_calculation"] = sr_debug

            trend_probability, tp_debug = self._predict_trend_probability_debug(
                historical_data, latest, signal_data
            )
            debug_info["trend_probability_calculation"] = tp_debug

            for day in self.prediction_days:
                prediction, pred_debug = self._predict_single_day_debug(
                    historical_data, latest, day, support_resistance, trend_probability
                )
                predictions[f"prediction_{day}d"] = prediction
                debug_info[f"prediction_{day}d_calculation"] = pred_debug

            return {
                "predictions": predictions,
                "support_resistance": support_resistance,
                "trend_probability": trend_probability,
                "current_price": current_price,
                "debug_info": debug_info,
            }

        except Exception as e:
            logger.error(f"价格预测失败: {e}", exc_info=True)
            return self._empty_prediction_debug()

    def _empty_prediction_debug(self):
        return {
            "predictions": {},
            "support_resistance": {"support": [], "resistance": []},
            "trend_probability": {"up": 33, "down": 33, "sideways": 34},
            "current_price": None,
            "debug_info": {"error": "预测失败或数据不足"},
        }

    def _calculate_support_resistance_debug(self, historical_data, current_price):
        """计算支撑阻力位（调试版）"""
        debug_info = {}
        try:
            debug_info["data_length"] = len(historical_data)

            if not isinstance(historical_data, pd.DataFrame):
                debug_info["error"] = "数据不是DataFrame"
                return {"support": [], "resistance": []}, debug_info

            if len(historical_data) < 20:
                debug_info["error"] = f"数据不足20天，只有{len(historical_data)}天"
                return {"support": [], "resistance": []}, debug_info

            high_series = historical_data.get("high", historical_data["close"])
            low_series = historical_data.get("low", historical_data["close"])

            high = float(high_series.iloc[-20:].max())
            low = float(low_series.iloc[-20:].min())
            close = float(historical_data["close"].iloc[-1])

            debug_info["recent_20d_high"] = high
            debug_info["recent_20d_low"] = low
            debug_info["current_close"] = close

            latest = historical_data.iloc[-1]

            atr = 0
            if len(historical_data) >= 14:
                prev_close = historical_data["close"].shift(1)
                tr1 = high_series - low_series
                tr2 = (high_series - prev_close).abs()
                tr3 = (low_series - prev_close).abs()
                atr = float(
                    pd.concat([tr1, tr2, tr3], axis=1)
                    .max(axis=1)
                    .rolling(14)
                    .mean()
                    .iloc[-1]
                )
                debug_info["atr_14d"] = atr
            else:
                atr = (high - low) * 0.1
                debug_info["atr_estimated"] = atr

            support_levels = []
            support_details = []

            support_levels.append(low)
            support_details.append({"source": "20日最低", "value": low})

            if "BBL_20_2.0" in latest.index:
                bb_lower = (
                    float(latest["BBL_20_2.0"])
                    if pd.notna(latest["BBL_20_2.0"])
                    else None
                )
                if bb_lower:
                    support_levels.append(bb_lower)
                    support_details.append({"source": "布林下轨", "value": bb_lower})

            for ma_period in [20, 60]:
                ma_col = f"SMA_{ma_period}"
                if ma_col in latest.index:
                    ma_value = (
                        float(latest[ma_col]) if pd.notna(latest[ma_col]) else None
                    )
                    if ma_value and ma_value < current_price:
                        support_levels.append(ma_value)
                        support_details.append(
                            {"source": f"{ma_period}日均线", "value": ma_value}
                        )

            support_levels.append(current_price - atr * 1.5)
            support_details.append(
                {"source": "ATR-1.5倍", "value": current_price - atr * 1.5}
            )
            support_levels.append(current_price - atr * 3)
            support_details.append(
                {"source": "ATR-3倍", "value": current_price - atr * 3}
            )

            support_levels = sorted(
                list(set([round(v, 2) for v in support_levels if v > 0]))
            )
            support_levels = [v for v in support_levels if v < current_price]

            resistance_levels = []
            resistance_details = []

            resistance_levels.append(high)
            resistance_details.append({"source": "20日最高", "value": high})

            if "BBU_20_2.0" in latest.index:
                bb_upper = (
                    float(latest["BBU_20_2.0"])
                    if pd.notna(latest["BBU_20_2.0"])
                    else None
                )
                if bb_upper:
                    resistance_levels.append(bb_upper)
                    resistance_details.append({"source": "布林上轨", "value": bb_upper})

            for ma_period in [5, 10, 20]:
                ma_col = f"SMA_{ma_period}"
                if ma_col in latest.index:
                    ma_value = (
                        float(latest[ma_col]) if pd.notna(latest[ma_col]) else None
                    )
                    if ma_value and ma_value > current_price:
                        resistance_levels.append(ma_value)
                        resistance_details.append(
                            {"source": f"{ma_period}日均线", "value": ma_value}
                        )

            resistance_levels.append(current_price + atr * 1.5)
            resistance_details.append(
                {"source": "ATR+1.5倍", "value": current_price + atr * 1.5}
            )
            resistance_levels.append(current_price + atr * 3)
            resistance_details.append(
                {"source": "ATR+3倍", "value": current_price + atr * 3}
            )

            resistance_levels = sorted(
                list(set([round(v, 2) for v in resistance_levels if v > 0]))
            )
            resistance_levels = [v for v in resistance_levels if v > current_price]

            support = support_levels[-3:] if len(support_levels) > 3 else support_levels
            resistance = (
                resistance_levels[:3]
                if len(resistance_levels) > 3
                else resistance_levels
            )

            debug_info["support_levels_all"] = support_details
            debug_info["resistance_levels_all"] = resistance_details
            debug_info["final_support"] = support
            debug_info["final_resistance"] = resistance

            return {
                "support": support,
                "resistance": resistance,
                "atr": atr,
            }, debug_info

        except Exception as e:
            logger.error(f"计算支撑阻力位失败: {e}")
            debug_info["error"] = str(e)
            return {"support": [], "resistance": []}, debug_info

    def _predict_trend_probability_debug(self, historical_data, latest, signal_data):
        """预测趋势概率（调试版）"""
        debug_info = {}

        try:
            up_score = 0
            down_score = 0
            sideways_score = 10

            debug_info["signal_score"] = {}
            if signal_data:
                signal_score = signal_data.get("signal_score", 50)
                debug_info["signal_score"]["input_score"] = signal_score
                if signal_score > 50:
                    up_score += (signal_score - 50) * 0.5
                    debug_info["signal_score"]["result"] = (
                        f"上涨+{(signal_score - 50) * 0.5:.1f}"
                    )
                elif signal_score < 50:
                    down_score += (50 - signal_score) * 0.5
                    debug_info["signal_score"]["result"] = (
                        f"下跌+{(50 - signal_score) * 0.5:.1f}"
                    )
                else:
                    sideways_score += 0.5
                    debug_info["signal_score"]["result"] = "横盘+0.5"
            else:
                debug_info["signal_score"]["result"] = "无信号数据"

            if isinstance(latest, pd.Series):
                close = latest.get("close") if "close" in latest.index else None
                sma_5 = latest.get("SMA_5") if "SMA_5" in latest.index else None
                sma_10 = latest.get("SMA_10") if "SMA_10" in latest.index else None
                sma_20 = latest.get("SMA_20") if "SMA_20" in latest.index else None
            else:
                close = latest.get("close") if isinstance(latest, dict) else None
                sma_5 = latest.get("SMA_5") if isinstance(latest, dict) else None
                sma_10 = latest.get("SMA_10") if isinstance(latest, dict) else None
                sma_20 = latest.get("SMA_20") if isinstance(latest, dict) else None

            debug_info["ma_trend"] = {
                "close": close,
                "sma_5": sma_5,
                "sma_10": sma_10,
                "sma_20": sma_20,
            }

            if sma_5 and sma_20 and close:
                if close > sma_5 > sma_20:
                    up_score += 20
                    debug_info["ma_trend"]["result"] = "上涨+20（多头排列）"
                elif close < sma_5 < sma_20:
                    down_score += 20
                    debug_info["ma_trend"]["result"] = "下跌+20（空头排列）"
                else:
                    sideways_score += 20
                    debug_info["ma_trend"]["result"] = "横盘+20（均线纠缠）"
            else:
                debug_info["ma_trend"]["result"] = "均线数据不足"

            debug_info["momentum"] = {}
            if len(historical_data) >= 3:
                recent_changes = historical_data["close"].pct_change().tail(3)
                avg_change = float(recent_changes.mean())
                debug_info["momentum"]["avg_change_3d"] = f"{avg_change * 100:.2f}%"
                if avg_change > 0.005:
                    up_score += 15
                    debug_info["momentum"]["result"] = "上涨+15（上涨动能）"
                elif avg_change < -0.005:
                    down_score += 15
                    debug_info["momentum"]["result"] = "下跌+15（下跌动能）"
                else:
                    sideways_score += 15
                    debug_info["momentum"]["result"] = "横盘+15（动能中性）"

            debug_info["rsi_analysis"] = {}
            rsi = latest.get("RSI_14")
            if rsi is not None:
                debug_info["rsi_analysis"]["rsi_value"] = float(rsi)
                if rsi < 40:
                    up_score += 10
                    debug_info["rsi_analysis"]["result"] = "上涨+10（RSI超卖）"
                elif rsi > 60:
                    down_score += 10
                    debug_info["rsi_analysis"]["result"] = "下跌+10（RSI超买）"
                else:
                    sideways_score += 10
                    debug_info["rsi_analysis"]["result"] = "横盘+10（RSI中性）"
            else:
                debug_info["rsi_analysis"]["result"] = "RSI数据不足"

            debug_info["kdj_analysis"] = {}
            kdj_k = latest.get("KDJ_K")
            kdj_d = latest.get("KDJ_D")
            if kdj_k is not None and kdj_d is not None:
                debug_info["kdj_analysis"]["kdj_values"] = {
                    "K": float(kdj_k),
                    "D": float(kdj_d),
                }
                if kdj_k < 20:
                    up_score += 5
                    debug_info["kdj_analysis"]["result"] = "上涨+5（KDJ超卖）"
                elif kdj_k > 80:
                    down_score += 5
                    debug_info["kdj_analysis"]["result"] = "下跌+5（KDJ超买）"
                else:
                    sideways_score += 5
                    debug_info["kdj_analysis"]["result"] = "横盘+5（KDJ中性）"
            else:
                debug_info["kdj_analysis"]["result"] = "KDJ数据不足"

            total = up_score + down_score + sideways_score
            if total > 0:
                up_prob = up_score / total
                down_prob = down_score / total
                sideways_prob = sideways_score / total
            else:
                up_prob = down_prob = sideways_prob = 0.333

            debug_info["final_scores"] = {
                "up_score": up_score,
                "down_score": down_score,
                "sideways_score": sideways_score,
                "total": total,
            }
            debug_info["final_probability"] = {
                "up": round(up_prob * 100, 1),
                "down": round(down_prob * 100, 1),
                "sideways": round(sideways_prob * 100, 1),
            }

            return {
                "up": round(up_prob * 100, 1),
                "down": round(down_prob * 100, 1),
                "sideways": round(sideways_prob * 100, 1),
            }, debug_info

        except Exception as e:
            logger.error(f"预测趋势概率失败: {e}")
            debug_info["error"] = str(e)
            return {"up": 33, "down": 33, "sideways": 34}, debug_info

    def _predict_single_day_debug(
        self, historical_data, latest, day, support_resistance, trend_probability
    ):
        """预测单日价格（调试版）"""
        debug_info = {}
        try:
            current_price = float(latest.get("close"))
            debug_info["day"] = day
            debug_info["current_price"] = current_price

            if len(historical_data) >= 20:
                volatility = float(
                    historical_data["close"].pct_change().tail(20).std()
                ) * np.sqrt(252)
                daily_volatility = volatility / np.sqrt(252)
                debug_info["volatility"] = {
                    "annualized": f"{volatility * 100:.2f}%",
                    "daily": f"{daily_volatility * 100:.2f}%",
                }
            else:
                daily_volatility = 0.02
                debug_info["volatility"] = {"daily": "2%（默认）"}

            up_prob = trend_probability.get("up", 33) / 100
            down_prob = trend_probability.get("down", 33) / 100
            sideways_prob = trend_probability.get("sideways", 34) / 100

            debug_info["input_probability"] = {
                "up": f"{up_prob * 100:.1f}%",
                "down": f"{down_prob * 100:.1f}%",
                "sideways": f"{sideways_prob * 100:.1f}%",
            }

            expected_change = (up_prob - down_prob) * daily_volatility * day
            debug_info["expected_change"] = {
                "value": f"{expected_change * 100:.4f}%",
                "calculation": f"({up_prob * 100:.1f}% - {down_prob * 100:.1f}%) × {daily_volatility * 100:.2f}% × {day}天",
            }

            target_price = current_price * (1 + expected_change)
            debug_info["target_price"] = target_price

            range_multiplier = 1.5
            high_price = target_price * (
                1 + range_multiplier * daily_volatility * np.sqrt(day)
            )
            low_price = target_price * (
                1 - range_multiplier * daily_volatility * np.sqrt(day)
            )

            debug_info["price_range"] = {
                "high": high_price,
                "low": low_price,
                "multiplier": range_multiplier,
            }

            resistance_levels = support_resistance.get("resistance", [])
            support_levels = support_resistance.get("support", [])

            if resistance_levels and high_price > resistance_levels[0]:
                old_high = high_price
                high_price = min(high_price, resistance_levels[0] * 1.01)
                debug_info["resistance_adjustment"] = (
                    f"受限: {old_high:.2f} → {high_price:.2f} (阻力位 {resistance_levels[0]})"
                )

            if support_levels and low_price < support_levels[-1]:
                old_low = low_price
                low_price = max(low_price, support_levels[-1] * 0.99)
                debug_info["support_adjustment"] = (
                    f"受限: {old_low:.2f} → {low_price:.2f} (支撑位 {support_levels[-1]})"
                )

            if up_prob > 50:
                trend = "上涨"
                confidence_score = int(up_prob)
            elif down_prob > 50:
                trend = "下跌"
                confidence_score = int(down_prob)
            else:
                trend = "横盘"
                confidence_score = int(sideways_prob)

            debug_info["trend_decision"] = {
                "selected": trend,
                "confidence_score": confidence_score,
                "reason": f"{trend}概率={confidence_score}%",
            }

            if confidence_score >= 60:
                confidence = "high"
            elif confidence_score >= 45:
                confidence = "medium"
            else:
                confidence = "low"

            debug_info["confidence_level"] = f"{confidence} (score={confidence_score})"

            return {
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "target": round(target_price, 2),
                "trend": trend,
                "confidence": confidence,
                "confidence_score": confidence_score,
                "trend_probability": trend_probability,
                "volatility": round(daily_volatility * 100, 2),
            }, debug_info

        except Exception as e:
            logger.error(f"预测单日价格失败: {e}")
            debug_info["error"] = str(e)
            return {
                "high": None,
                "low": None,
                "target": None,
                "trend": "横盘",
                "confidence": "low",
            }, debug_info


class PricePredictorDebug(PricePredictor):
    """价格预测调试版 - 返回详细的调试信息"""

    def predict_price(self, historical_data, latest, signal_data=None):
        """预测未来价格（带调试信息）"""
        try:
            debug_info = {}

            current_price = latest.get("close")
            if pd.isna(current_price) or current_price <= 0:
                return self._empty_prediction_debug()

            predictions = {}

            support_resistance, sr_debug = self._calculate_support_resistance_debug(
                historical_data, current_price
            )
            debug_info["support_resistance_calculation"] = sr_debug

            trend_probability, tp_debug = self._predict_trend_probability_debug(
                historical_data, latest, signal_data
            )
            debug_info["trend_probability_calculation"] = tp_debug

            for day in self.prediction_days:
                prediction, pred_debug = self._predict_single_day_debug(
                    historical_data, latest, day, support_resistance, trend_probability
                )
                predictions[f"prediction_{day}d"] = prediction
                debug_info[f"prediction_{day}d_calculation"] = pred_debug

            return {
                "predictions": predictions,
                "support_resistance": support_resistance,
                "trend_probability": trend_probability,
                "current_price": current_price,
                "debug_info": debug_info,
            }

        except Exception as e:
            logger.error(f"价格预测失败: {e}", exc_info=True)
            return self._empty_prediction_debug()

    def _empty_prediction_debug(self):
        return {
            "predictions": {},
            "support_resistance": {"support": [], "resistance": []},
            "trend_probability": {"up": 33, "down": 33, "sideways": 34},
            "current_price": None,
            "debug_info": {"error": "预测失败或数据不足"},
        }

    def _calculate_support_resistance_debug(self, historical_data, current_price):
        """计算支撑阻力位（调试版）"""
        debug_info = {}
        try:
            debug_info["data_length"] = len(historical_data)

            if not isinstance(historical_data, pd.DataFrame):
                debug_info["error"] = "数据不是DataFrame"
                return {"support": [], "resistance": []}, debug_info

            if len(historical_data) < 20:
                debug_info["error"] = f"数据不足20天，只有{len(historical_data)}天"
                return {"support": [], "resistance": []}, debug_info

            high_series = historical_data.get("high", historical_data["close"])
            low_series = historical_data.get("low", historical_data["close"])

            high = float(high_series.iloc[-20:].max())
            low = float(low_series.iloc[-20:].min())
            close = float(historical_data["close"].iloc[-1])

            debug_info["recent_20d_high"] = high
            debug_info["recent_20d_low"] = low
            debug_info["current_close"] = close

            latest = historical_data.iloc[-1]

            atr = 0
            if len(historical_data) >= 14:
                prev_close = historical_data["close"].shift(1)
                tr1 = high_series - low_series
                tr2 = (high_series - prev_close).abs()
                tr3 = (low_series - prev_close).abs()
                atr = float(
                    pd.concat([tr1, tr2, tr3], axis=1)
                    .max(axis=1)
                    .rolling(14)
                    .mean()
                    .iloc[-1]
                )
                debug_info["atr_14d"] = atr
            else:
                atr = (high - low) * 0.1
                debug_info["atr_estimated"] = atr

            support_levels = []
            support_details = []

            support_levels.append(low)
            support_details.append({"source": "20日最低", "value": low})

            if "BBL_20_2.0" in latest.index:
                bb_lower = (
                    float(latest["BBL_20_2.0"])
                    if pd.notna(latest["BBL_20_2.0"])
                    else None
                )
                if bb_lower:
                    support_levels.append(bb_lower)
                    support_details.append({"source": "布林下轨", "value": bb_lower})

            for ma_period in [20, 60]:
                ma_col = f"SMA_{ma_period}"
                if ma_col in latest.index:
                    ma_value = (
                        float(latest[ma_col]) if pd.notna(latest[ma_col]) else None
                    )
                    if ma_value and ma_value < current_price:
                        support_levels.append(ma_value)
                        support_details.append(
                            {"source": f"{ma_period}日均线", "value": ma_value}
                        )

            support_levels.append(current_price - atr * 1.5)
            support_details.append(
                {"source": "ATR-1.5倍", "value": current_price - atr * 1.5}
            )
            support_levels.append(current_price - atr * 3)
            support_details.append(
                {"source": "ATR-3倍", "value": current_price - atr * 3}
            )

            support_levels = sorted(
                list(set([round(v, 2) for v in support_levels if v > 0]))
            )
            support_levels = [v for v in support_levels if v < current_price]

            resistance_levels = []
            resistance_details = []

            resistance_levels.append(high)
            resistance_details.append({"source": "20日最高", "value": high})

            if "BBU_20_2.0" in latest.index:
                bb_upper = (
                    float(latest["BBU_20_2.0"])
                    if pd.notna(latest["BBU_20_2.0"])
                    else None
                )
                if bb_upper:
                    resistance_levels.append(bb_upper)
                    resistance_details.append({"source": "布林上轨", "value": bb_upper})

            for ma_period in [5, 10, 20]:
                ma_col = f"SMA_{ma_period}"
                if ma_col in latest.index:
                    ma_value = (
                        float(latest[ma_col]) if pd.notna(latest[ma_col]) else None
                    )
                    if ma_value and ma_value > current_price:
                        resistance_levels.append(ma_value)
                        resistance_details.append(
                            {"source": f"{ma_period}日均线", "value": ma_value}
                        )

            resistance_levels.append(current_price + atr * 1.5)
            resistance_details.append(
                {"source": "ATR+1.5倍", "value": current_price + atr * 1.5}
            )
            resistance_levels.append(current_price + atr * 3)
            resistance_details.append(
                {"source": "ATR+3倍", "value": current_price + atr * 3}
            )

            resistance_levels = sorted(
                list(set([round(v, 2) for v in resistance_levels if v > 0]))
            )
            resistance_levels = [v for v in resistance_levels if v > current_price]

            support = support_levels[-3:] if len(support_levels) > 3 else support_levels
            resistance = (
                resistance_levels[:3]
                if len(resistance_levels) > 3
                else resistance_levels
            )

            debug_info["support_levels_all"] = support_details
            debug_info["resistance_levels_all"] = resistance_details
            debug_info["final_support"] = support
            debug_info["final_resistance"] = resistance

            return {
                "support": support,
                "resistance": resistance,
                "atr": atr,
            }, debug_info

        except Exception as e:
            logger.error(f"计算支撑阻力位失败: {e}")
            debug_info["error"] = str(e)
            return {"support": [], "resistance": []}, debug_info

    def _predict_trend_probability_debug(self, historical_data, latest, signal_data):
        """预测趋势概率（调试版）"""
        debug_info = {}

        try:
            up_score = 0
            down_score = 0
            sideways_score = 10

            debug_info["signal_score"] = {}
            if signal_data:
                signal_score = signal_data.get("signal_score", 50)
                debug_info["signal_score"]["input_score"] = signal_score
                if signal_score > 50:
                    up_score += (signal_score - 50) * 0.5
                    debug_info["signal_score"]["result"] = (
                        f"上涨+{(signal_score - 50) * 0.5:.1f}"
                    )
                elif signal_score < 50:
                    down_score += (50 - signal_score) * 0.5
                    debug_info["signal_score"]["result"] = (
                        f"下跌+{(50 - signal_score) * 0.5:.1f}"
                    )
                else:
                    sideways_score += 0.5
                    debug_info["signal_score"]["result"] = "横盘+0.5"
            else:
                debug_info["signal_score"]["result"] = "无信号数据"

            if isinstance(latest, pd.Series):
                close = latest.get("close") if "close" in latest.index else None
                sma_5 = latest.get("SMA_5") if "SMA_5" in latest.index else None
                sma_10 = latest.get("SMA_10") if "SMA_10" in latest.index else None
                sma_20 = latest.get("SMA_20") if "SMA_20" in latest.index else None
            else:
                close = latest.get("close") if isinstance(latest, dict) else None
                sma_5 = latest.get("SMA_5") if isinstance(latest, dict) else None
                sma_10 = latest.get("SMA_10") if isinstance(latest, dict) else None
                sma_20 = latest.get("SMA_20") if isinstance(latest, dict) else None

            debug_info["ma_trend"] = {
                "close": close,
                "sma_5": sma_5,
                "sma_10": sma_10,
                "sma_20": sma_20,
            }

            if sma_5 is not None and sma_20 is not None and close is not None:
                if close > sma_5 > sma_20:
                    up_score += 20
                    debug_info["ma_trend"]["result"] = "上涨+20（多头排列）"
                elif close < sma_5 < sma_20:
                    down_score += 20
                    debug_info["ma_trend"]["result"] = "下跌+20（空头排列）"
                else:
                    sideways_score += 20
                    debug_info["ma_trend"]["result"] = "横盘+20（均线纠缠）"
            else:
                debug_info["ma_trend"]["result"] = "均线数据不足"

            debug_info["momentum"] = {}
            if len(historical_data) >= 3:
                recent_changes = historical_data["close"].pct_change().tail(3)
                avg_change = float(recent_changes.mean())
                debug_info["momentum"]["avg_change_3d"] = f"{avg_change * 100:.2f}%"
                if avg_change > 0.005:
                    up_score += 15
                    debug_info["momentum"]["result"] = "上涨+15（上涨动能）"
                elif avg_change < -0.005:
                    down_score += 15
                    debug_info["momentum"]["result"] = "下跌+15（下跌动能）"
                else:
                    sideways_score += 15
                    debug_info["momentum"]["result"] = "横盘+15（动能中性）"

            debug_info["rsi_analysis"] = {}
            rsi = latest.get("RSI_14")
            if rsi is not None:
                debug_info["rsi_analysis"]["rsi_value"] = float(rsi)
                if rsi < 40:
                    up_score += 10
                    debug_info["rsi_analysis"]["result"] = "上涨+10（RSI超卖）"
                elif rsi > 60:
                    down_score += 10
                    debug_info["rsi_analysis"]["result"] = "下跌+10（RSI超买）"
                else:
                    sideways_score += 10
                    debug_info["rsi_analysis"]["result"] = "横盘+10（RSI中性）"
            else:
                debug_info["rsi_analysis"]["result"] = "RSI数据不足"

            debug_info["kdj_analysis"] = {}
            kdj_k = latest.get("KDJ_K")
            kdj_d = latest.get("KDJ_D")
            if kdj_k is not None and kdj_d is not None:
                debug_info["kdj_analysis"]["kdj_values"] = {
                    "K": float(kdj_k),
                    "D": float(kdj_d),
                }
                if kdj_k < 20:
                    up_score += 5
                    debug_info["kdj_analysis"]["result"] = "上涨+5（KDJ超卖）"
                elif kdj_k > 80:
                    down_score += 5
                    debug_info["kdj_analysis"]["result"] = "下跌+5（KDJ超买）"
                else:
                    sideways_score += 5
                    debug_info["kdj_analysis"]["result"] = "横盘+5（KDJ中性）"
            else:
                debug_info["kdj_analysis"]["result"] = "KDJ数据不足"

            total = up_score + down_score + sideways_score
            if total > 0:
                up_prob = up_score / total
                down_prob = down_score / total
                sideways_prob = sideways_score / total
            else:
                up_prob = down_prob = sideways_prob = 0.333

            debug_info["final_scores"] = {
                "up_score": up_score,
                "down_score": down_score,
                "sideways_score": sideways_score,
                "total": total,
            }
            debug_info["final_probability"] = {
                "up": round(up_prob * 100, 1),
                "down": round(down_prob * 100, 1),
                "sideways": round(sideways_prob * 100, 1),
            }

            return {
                "up": round(up_prob * 100, 1),
                "down": round(down_prob * 100, 1),
                "sideways": round(sideways_prob * 100, 1),
            }, debug_info

        except Exception as e:
            logger.error(f"预测趋势概率失败: {e}")
            debug_info["error"] = str(e)
            return {"up": 33, "down": 33, "sideways": 34}, debug_info

    def _predict_single_day_debug(
        self, historical_data, latest, day, support_resistance, trend_probability
    ):
        """预测单日价格（调试版）"""
        debug_info = {}
        try:
            current_price = float(latest.get("close"))
            debug_info["day"] = day
            debug_info["current_price"] = current_price

            if len(historical_data) >= 20:
                volatility = float(
                    historical_data["close"].pct_change().tail(20).std()
                ) * np.sqrt(252)
                daily_volatility = volatility / np.sqrt(252)
                debug_info["volatility"] = {
                    "annualized": f"{volatility * 100:.2f}%",
                    "daily": f"{daily_volatility * 100:.2f}%",
                }
            else:
                daily_volatility = 0.02
                debug_info["volatility"] = {"daily": "2%（默认）"}

            up_prob = trend_probability.get("up", 33) / 100
            down_prob = trend_probability.get("down", 33) / 100
            sideways_prob = trend_probability.get("sideways", 34) / 100

            debug_info["input_probability"] = {
                "up": f"{up_prob * 100:.1f}%",
                "down": f"{down_prob * 100:.1f}%",
                "sideways": f"{sideways_prob * 100:.1f}%",
            }

            expected_change = (up_prob - down_prob) * daily_volatility * day
            debug_info["expected_change"] = {
                "value": f"{expected_change * 100:.4f}%",
                "calculation": f"({up_prob * 100:.1f}% - {down_prob * 100:.1f}%) × {daily_volatility * 100:.2f}% × {day}天",
            }

            target_price = current_price * (1 + expected_change)
            debug_info["target_price"] = target_price

            range_multiplier = 1.5
            high_price = target_price * (
                1 + range_multiplier * daily_volatility * np.sqrt(day)
            )
            low_price = target_price * (
                1 - range_multiplier * daily_volatility * np.sqrt(day)
            )

            debug_info["price_range"] = {
                "high": high_price,
                "low": low_price,
                "multiplier": range_multiplier,
            }

            resistance_levels = support_resistance.get("resistance", [])
            support_levels = support_resistance.get("support", [])

            if resistance_levels and high_price > resistance_levels[0]:
                old_high = high_price
                high_price = min(high_price, resistance_levels[0] * 1.01)
                debug_info["resistance_adjustment"] = (
                    f"受限: {old_high:.2f} → {high_price:.2f} (阻力位 {resistance_levels[0]})"
                )

            if support_levels and low_price < support_levels[-1]:
                old_low = low_price
                low_price = max(low_price, support_levels[-1] * 0.99)
                debug_info["support_adjustment"] = (
                    f"受限: {old_low:.2f} → {low_price:.2f} (支撑位 {support_levels[-1]})"
                )

            if up_prob > 50:
                trend = "上涨"
                confidence_score = int(up_prob)
            elif down_prob > 50:
                trend = "下跌"
                confidence_score = int(down_prob)
            else:
                trend = "横盘"
                confidence_score = int(sideways_prob)

            debug_info["trend_decision"] = {
                "selected": trend,
                "confidence_score": confidence_score,
                "reason": f"{trend}概率={confidence_score}%",
            }

            if confidence_score >= 60:
                confidence = "high"
            elif confidence_score >= 45:
                confidence = "medium"
            else:
                confidence = "low"

            debug_info["confidence_level"] = f"{confidence} (score={confidence_score})"

            return {
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "target": round(target_price, 2),
                "trend": trend,
                "confidence": confidence,
                "confidence_score": confidence_score,
                "trend_probability": trend_probability,
                "volatility": round(daily_volatility * 100, 2),
            }, debug_info

        except Exception as e:
            logger.error(f"预测单日价格失败: {e}")
            debug_info["error"] = str(e)
            return {
                "high": None,
                "low": None,
                "target": None,
                "trend": "横盘",
                "confidence": "low",
            }, debug_info
