"""
买卖信号系统 - 基于前瞻性技术指标的智能信号生成
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


class SignalSystem:
    """
    买卖信号生成系统
    信号类型：Strong Buy / Buy / Hold / Sell / Strong Sell
    信号强度：基于多指标综合评分（0-100）
    信号置信度：基于指标一致性（0-100%）
    """

    def __init__(self):
        # 信号权重配置（总权重100）
        self.signal_weights = {
            "RSI": 25,  # RSI是最重要的领先指标
            "KDJ": 20,  # KDJ是短期灵敏指标
            "MACD": 20,  # MACD是趋势确认指标
            "MA": 15,  # MA是基础趋势指标
            "BOLLINGER": 10,  # 布林带是辅助指标
            "CCI": 5,  # CCI是辅助指标
            "OBV": 3,  # OBV是资金流向指标
            "WILLIAMS": 2,  # 威廉指标是辅助指标
        }

    def generate_signals(self, latest, prev_latest, historical_data=None):
        """
        生成买卖信号

        参数:
            latest: 最新一天的数据
            prev_latest: 前一天的数据
            historical_data: 历史数据（用于趋势判断）

        返回:
            dict: {
                'signal_type': 'Strong Buy/Buy/Hold/Sell/Strong Sell',
                'signal_score': 0-100,
                'confidence': 0-100%,
                'signal_reasons': ['理由1', '理由2', ...],
                'signal_strength': 'Weak/Strong',
                'forward_indicators': {
                    'RSI': {'value': 65, 'status': '买入', 'weight': 25},
                    'KDJ': {'value': 70, 'status': '买入', 'weight': 20},
                    ...
                }
            }
        """
        try:
            # 初始化信号数据结构
            signal_data = {
                "signal_type": "Hold",
                "signal_score": 50,
                "confidence": 50,
                "signal_reasons": [],
                "signal_strength": "Weak",
                "forward_indicators": {},
            }

            # 评估每个前瞻性指标
            total_weight = 0
            buy_weight = 0
            sell_weight = 0

            # RSI分析（权重25%）
            rsi_result = self._evaluate_rsi(latest, prev_latest)
            if rsi_result:
                signal_data["forward_indicators"]["RSI"] = rsi_result
                total_weight += self.signal_weights["RSI"]
                if rsi_result["status"] == "买入":
                    buy_weight += self.signal_weights["RSI"]
                    signal_data["signal_reasons"].append(
                        f"RSI({rsi_result['value']:.1f})显示买入信号"
                    )
                elif rsi_result["status"] == "卖出":
                    sell_weight += self.signal_weights["RSI"]
                    signal_data["signal_reasons"].append(
                        f"RSI({rsi_result['value']:.1f})显示卖出信号"
                    )

            # KDJ分析（权重20%）
            kdj_result = self._evaluate_kdj(latest, prev_latest)
            if kdj_result:
                signal_data["forward_indicators"]["KDJ"] = kdj_result
                total_weight += self.signal_weights["KDJ"]
                if kdj_result["status"] == "买入":
                    buy_weight += self.signal_weights["KDJ"]
                    signal_data["signal_reasons"].append(
                        f"KDJ(K={kdj_result['k_value']:.1f}, J={kdj_result['j_value']:.1f})显示买入信号"
                    )
                elif kdj_result["status"] == "卖出":
                    sell_weight += self.signal_weights["KDJ"]
                    signal_data["signal_reasons"].append(
                        f"KDJ(K={kdj_result['k_value']:.1f}, J={kdj_result['j_value']:.1f})显示卖出信号"
                    )

            # MACD分析（权重20%）
            macd_result = self._evaluate_macd(latest, prev_latest)
            if macd_result:
                signal_data["forward_indicators"]["MACD"] = macd_result
                total_weight += self.signal_weights["MACD"]
                if macd_result["status"] == "买入":
                    buy_weight += self.signal_weights["MACD"]
                    signal_data["signal_reasons"].append("MACD显示买入信号")
                elif macd_result["status"] == "卖出":
                    sell_weight += self.signal_weights["MACD"]
                    signal_data["signal_reasons"].append("MACD显示卖出信号")

            # MA分析（权重15%）
            ma_result = self._evaluate_ma(latest, prev_latest)
            if ma_result:
                signal_data["forward_indicators"]["MA"] = ma_result
                total_weight += self.signal_weights["MA"]
                if ma_result["status"] == "买入":
                    buy_weight += self.signal_weights["MA"]
                    signal_data["signal_reasons"].append("均线多头排列")
                elif ma_result["status"] == "卖出":
                    sell_weight += self.signal_weights["MA"]
                    signal_data["signal_reasons"].append("均线空头排列")

            # 布林带分析（权重10%）
            bb_result = self._evaluate_bollinger(latest)
            if bb_result:
                signal_data["forward_indicators"]["BOLLINGER"] = bb_result
                total_weight += self.signal_weights["BOLLINGER"]
                if bb_result["status"] == "买入":
                    buy_weight += self.signal_weights["BOLLINGER"]
                    signal_data["signal_reasons"].append(f"价格触及布林下轨，超卖")
                elif bb_result["status"] == "卖出":
                    sell_weight += self.signal_weights["BOLLINGER"]
                    signal_data["signal_reasons"].append(f"价格触及布林上轨，超买")

            # CCI分析（权重5%）
            cci_result = self._evaluate_cci(latest, prev_latest)
            if cci_result:
                signal_data["forward_indicators"]["CCI"] = cci_result
                total_weight += self.signal_weights["CCI"]
                if cci_result["status"] == "买入":
                    buy_weight += self.signal_weights["CCI"]
                    signal_data["signal_reasons"].append(
                        f"CCI({cci_result['value']:.1f})超卖，买入信号"
                    )
                elif cci_result["status"] == "卖出":
                    sell_weight += self.signal_weights["CCI"]
                    signal_data["signal_reasons"].append(
                        f"CCI({cci_result['value']:.1f})超买，卖出信号"
                    )

            # OBV分析（权重3%）
            obv_result = self._evaluate_obv(latest, prev_latest)
            if obv_result:
                signal_data["forward_indicators"]["OBV"] = obv_result
                total_weight += self.signal_weights["OBV"]
                if obv_result["status"] == "买入":
                    buy_weight += self.signal_weights["OBV"]
                    signal_data["signal_reasons"].append("OBV资金流入")
                elif obv_result["status"] == "卖出":
                    sell_weight += self.signal_weights["OBV"]
                    signal_data["signal_reasons"].append("OBV资金流出")

            # 威廉指标分析（权重2%）
            wr_result = self._evaluate_williams(latest, prev_latest)
            if wr_result:
                signal_data["forward_indicators"]["WILLIAMS"] = wr_result
                total_weight += self.signal_weights["WILLIAMS"]
                if wr_result["status"] == "买入":
                    buy_weight += self.signal_weights["WILLIAMS"]
                    signal_data["signal_reasons"].append(
                        f"威廉指标({wr_result['value']:.1f})超卖"
                    )
                elif wr_result["status"] == "卖出":
                    sell_weight += self.signal_weights["WILLIAMS"]
                    signal_data["signal_reasons"].append(
                        f"威廉指标({wr_result['value']:.1f})超买"
                    )

            # 计算信号评分（买入为正，卖出为负）
            if total_weight > 0:
                net_score = (
                    (buy_weight - sell_weight) / total_weight
                ) * 50 + 50  # 归一化到0-100
                signal_data["signal_score"] = net_score
            else:
                signal_data["signal_score"] = 50  # 默认中性

            # 计算置信度（基于信号一致性）
            signal_count = len(
                [
                    s
                    for s in signal_data["forward_indicators"].values()
                    if s.get("status") in ["买入", "卖出"]
                ]
            )
            buy_count = len(
                [
                    s
                    for s in signal_data["forward_indicators"].values()
                    if s.get("status") == "买入"
                ]
            )
            sell_count = len(
                [
                    s
                    for s in signal_data["forward_indicators"].values()
                    if s.get("status") == "卖出"
                ]
            )

            total_indicators = len(signal_data["forward_indicators"])
            if signal_count > 0:
                # 买入或卖出信号占比越高，置信度越高
                dominant_count = max(buy_count, sell_count)
                signal_data["confidence"] = (dominant_count / signal_count) * 100
            else:
                # 所有指标中性时，置信度设为50，表示市场共识为中性
                signal_data["confidence"] = 50

            # 判定信号类型
            if signal_data["signal_score"] >= 85:
                signal_data["signal_type"] = "Strong Buy"
                signal_data["signal_strength"] = "Strong"
            elif signal_data["signal_score"] >= 65:
                signal_data["signal_type"] = "Buy"
                signal_data["signal_strength"] = "Weak"
            elif signal_data["signal_score"] >= 45:
                signal_data["signal_type"] = "Hold"
                signal_data["signal_strength"] = "Weak"
            elif signal_data["signal_score"] >= 25:
                signal_data["signal_type"] = "Sell"
                signal_data["signal_strength"] = "Weak"
            else:
                signal_data["signal_type"] = "Strong Sell"
                signal_data["signal_strength"] = "Strong"

            # 如果信号类型是Hold，清空理由
            if signal_data["signal_type"] == "Hold":
                signal_data["signal_reasons"] = ["多空信号均衡，建议持有观望"]

            # 基于置信度调整信号强度
            if signal_data["confidence"] >= 70:
                signal_data["signal_strength"] = "Strong"
            elif signal_data["confidence"] >= 40:
                signal_data["signal_strength"] = "Weak"

            return signal_data

        except Exception as e:
            logger.error(f"生成信号失败: {e}", exc_info=True)
            return {
                "signal_type": "Hold",
                "signal_score": 50,
                "confidence": 0,
                "signal_reasons": ["信号生成失败，默认持有"],
                "signal_strength": "Weak",
                "forward_indicators": {},
            }

    def _evaluate_rsi(self, latest, prev_latest):
        """评估RSI指标"""
        try:
            rsi = latest.get("RSI_12")
            if pd.isna(rsi):
                return None

            if rsi < 30:
                return {
                    "value": rsi,
                    "status": "买入",
                    "weight": self.signal_weights["RSI"],
                }
            elif rsi < 40:
                return {
                    "value": rsi,
                    "status": "买入",
                    "weight": self.signal_weights["RSI"],
                }
            elif rsi > 70:
                return {
                    "value": rsi,
                    "status": "卖出",
                    "weight": self.signal_weights["RSI"],
                }
            elif rsi > 60:
                return {
                    "value": rsi,
                    "status": "卖出",
                    "weight": self.signal_weights["RSI"],
                }
            else:
                return {
                    "value": rsi,
                    "status": "中性",
                    "weight": self.signal_weights["RSI"],
                }
        except:
            return None

    def _evaluate_kdj(self, latest, prev_latest):
        """评估KDJ指标"""
        try:
            k_val = latest.get("KDJ_K")
            j_val = latest.get("KDJ_J")
            prev_k = prev_latest.get("KDJ_K")
            prev_d = prev_latest.get("KDJ_D")

            if pd.isna(k_val) or pd.isna(j_val):
                return None

            # 金叉判断
            if pd.notna(prev_k) and pd.notna(prev_d):
                if k_val > prev_d and prev_k <= prev_d:
                    return {
                        "k_value": k_val,
                        "j_value": j_val,
                        "status": "买入",
                        "weight": self.signal_weights["KDJ"],
                    }
                elif k_val < prev_d and prev_k >= prev_d:
                    return {
                        "k_value": k_val,
                        "j_value": j_val,
                        "status": "卖出",
                        "weight": self.signal_weights["KDJ"],
                    }

            # J值判断
            if j_val < 0:
                return {
                    "k_value": k_val,
                    "j_value": j_val,
                    "status": "买入",
                    "weight": self.signal_weights["KDJ"],
                }
            elif j_val > 100:
                return {
                    "k_value": k_val,
                    "j_value": j_val,
                    "status": "卖出",
                    "weight": self.signal_weights["KDJ"],
                }
            elif k_val < 20:
                return {
                    "k_value": k_val,
                    "j_value": j_val,
                    "status": "买入",
                    "weight": self.signal_weights["KDJ"],
                }
            elif k_val > 80:
                return {
                    "k_value": k_val,
                    "j_value": j_val,
                    "status": "卖出",
                    "weight": self.signal_weights["KDJ"],
                }
            else:
                return {
                    "k_value": k_val,
                    "j_value": j_val,
                    "status": "中性",
                    "weight": self.signal_weights["KDJ"],
                }
        except:
            return None

    def _evaluate_macd(self, latest, prev_latest):
        """评估MACD指标"""
        try:
            macd = latest.get("MACD_12_26_9")
            signal = latest.get("MACDs_12_26_9")
            prev_macd = prev_latest.get("MACD_12_26_9")
            prev_signal = prev_latest.get("MACDs_12_26_9")

            if pd.isna(macd) or pd.isna(signal):
                return None

            # 金叉死叉判断
            if pd.notna(prev_macd) and pd.notna(prev_signal):
                if macd > signal and prev_macd <= prev_signal:
                    return {
                        "value": macd,
                        "status": "买入",
                        "weight": self.signal_weights["MACD"],
                    }
                elif macd < signal and prev_macd >= prev_signal:
                    return {
                        "value": macd,
                        "status": "卖出",
                        "weight": self.signal_weights["MACD"],
                    }

            # 零轴判断
            if macd > 0 and signal > 0:
                return {
                    "value": macd,
                    "status": "买入",
                    "weight": self.signal_weights["MACD"],
                }
            elif macd < 0 and signal < 0:
                return {
                    "value": macd,
                    "status": "卖出",
                    "weight": self.signal_weights["MACD"],
                }
            else:
                return {
                    "value": macd,
                    "status": "中性",
                    "weight": self.signal_weights["MACD"],
                }
        except:
            return None

    def _evaluate_ma(self, latest, prev_latest):
        """评估均线指标"""
        try:
            close = latest.get("close")
            sma_5 = latest.get("SMA_5")
            sma_10 = latest.get("SMA_10")
            sma_20 = latest.get("SMA_20")

            if pd.isna(close) or pd.isna(sma_20):
                return None

            # 短期多头排列
            if pd.notna(sma_5) and pd.notna(sma_10):
                if close > sma_5 > sma_10 > sma_20:
                    return {
                        "value": close,
                        "status": "买入",
                        "weight": self.signal_weights["MA"],
                    }
                elif close < sma_5 < sma_10 < sma_20:
                    return {
                        "value": close,
                        "status": "卖出",
                        "weight": self.signal_weights["MA"],
                    }

            # 简单判断
            if close > sma_20:
                return {
                    "value": close,
                    "status": "买入",
                    "weight": self.signal_weights["MA"],
                }
            elif close < sma_20:
                return {
                    "value": close,
                    "status": "卖出",
                    "weight": self.signal_weights["MA"],
                }
            else:
                return {
                    "value": close,
                    "status": "中性",
                    "weight": self.signal_weights["MA"],
                }
        except:
            return None

    def _evaluate_bollinger(self, latest):
        """评估布林带指标"""
        try:
            close = latest.get("close")
            upper = latest.get("BBU_20_2.0")
            lower = latest.get("BBL_20_2.0")
            middle = latest.get("BBM_20_2.0")

            if pd.isna(close) or pd.isna(lower):
                return None

            if close < lower:
                return {
                    "value": close,
                    "status": "买入",
                    "weight": self.signal_weights["BOLLINGER"],
                }
            elif close > upper:
                return {
                    "value": close,
                    "status": "卖出",
                    "weight": self.signal_weights["BOLLINGER"],
                }
            elif close > middle:
                return {
                    "value": close,
                    "status": "买入",
                    "weight": self.signal_weights["BOLLINGER"],
                }
            else:
                return {
                    "value": close,
                    "status": "卖出",
                    "weight": self.signal_weights["BOLLINGER"],
                }
        except:
            return None

    def _evaluate_cci(self, latest, prev_latest):
        """评估CCI指标"""
        try:
            cci = latest.get("CCI_14")
            prev_cci = prev_latest.get("CCI_14")

            if pd.isna(cci):
                return None

            if cci < -100:
                return {
                    "value": cci,
                    "status": "买入",
                    "weight": self.signal_weights["CCI"],
                }
            elif cci > 100:
                return {
                    "value": cci,
                    "status": "卖出",
                    "weight": self.signal_weights["CCI"],
                }
            else:
                return {
                    "value": cci,
                    "status": "中性",
                    "weight": self.signal_weights["CCI"],
                }
        except:
            return None

    def _evaluate_obv(self, latest, prev_latest):
        """评估OBV指标"""
        try:
            obv = latest.get("OBV")
            prev_obv = prev_latest.get("OBV")

            if pd.isna(obv):
                return None

            if pd.notna(prev_obv):
                if obv > prev_obv:
                    return {
                        "value": obv,
                        "status": "买入",
                        "weight": self.signal_weights["OBV"],
                    }
                elif obv < prev_obv:
                    return {
                        "value": obv,
                        "status": "卖出",
                        "weight": self.signal_weights["OBV"],
                    }

            return {
                "value": obv,
                "status": "中性",
                "weight": self.signal_weights["OBV"],
            }
        except:
            return None

    def _evaluate_williams(self, latest, prev_latest):
        """评估威廉指标"""
        try:
            wr = latest.get("WR_14")
            prev_wr = prev_latest.get("WR_14")

            if pd.isna(wr):
                return None

            # 威廉指标与RSI相反，-80以下为超买，-20以上为超卖
            if wr > -20:
                return {
                    "value": wr,
                    "status": "买入",
                    "weight": self.signal_weights["WILLIAMS"],
                }
            elif wr < -80:
                return {
                    "value": wr,
                    "status": "卖出",
                    "weight": self.signal_weights["WILLIAMS"],
                }
            else:
                return {
                    "value": wr,
                    "status": "中性",
                    "weight": self.signal_weights["WILLIAMS"],
                }
        except:
            return None


def generate_signal_summary(signal_data):
    """
    生成信号摘要文本

    参数:
        signal_data: generate_signals() 返回的数据

    返回:
        str: 信号摘要
    """
    try:
        signal_type = signal_data.get("signal_type", "Hold")
        score = signal_data.get("signal_score", 50)
        confidence = signal_data.get("confidence", 0)
        reasons = signal_data.get("signal_reasons", [])

        # 信号强度描述
        strength = signal_data.get("signal_strength", "Weak")

        # 信号类型中文映射
        signal_type_cn = {
            "Strong Buy": "强烈买入",
            "Buy": "买入",
            "Hold": "持有",
            "Sell": "卖出",
            "Strong Sell": "强烈卖出",
        }

        # 生成摘要
        summary = f"{signal_type_cn.get(signal_type, signal_type)}信号"

        if strength == "Strong":
            summary += "（强度：强）"
        else:
            summary += "（强度：弱）"

        summary += f"，综合评分：{score:.1f}/100，置信度：{confidence:.0f}%。"

        if reasons:
            summary += " 主要原因：" + "、".join(reasons[:3]) + "。"

        return summary

    except Exception as e:
        logger.error(f"生成信号摘要失败: {e}")
        return "信号摘要生成失败"
