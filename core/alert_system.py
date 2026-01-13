"""
预警系统 - 检测关键技术信号并生成预警
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


class AlertSystem:
    """
    预警系统
    检测关键的技术信号并生成预警（高风险/中风险/低风险）
    """

    def __init__(self):
        # 预警等级定义
        self.alert_levels = {"high": "高风险", "medium": "中风险", "low": "低风险"}

        # 预警类型定义
        self.alert_types = {
            "trend_reversal": "趋势反转",
            "overbought_oversold": "超买超卖",
            "divergence": "背离信号",
            "breakout": "突破预警",
            "ma_alignment": "多空排列",
            "volume_anomaly": "量价异常",
            "signal_conflict": "信号冲突",
        }

    def generate_alerts(self, historical_data, latest, prev_latest, signal_data=None):
        """
        生成预警信息

        参数:
            historical_data: 历史数据
            latest: 最新数据
            prev_latest: 前一天数据
            signal_data: 信号数据（可选）

        返回:
            dict: {
                'alerts': [
                    {
                        'level': 'high/medium/low',
                        'type': '趋势反转/超买超卖/...',
                        'message': '预警信息',
                        'indicator': 'RSI/KDJ/MACD/...',
                        'value': '指标值'
                    },
                    ...
                ],
                'alert_count': {'high': 2, 'medium': 3, 'low': 1},
                'overall_risk': 'high/medium/low'
            }
        """
        try:
            alerts = []

            # 1. 趋势反转预警
            alerts.extend(
                self._check_trend_reversal(historical_data, latest, prev_latest)
            )

            # 2. 超买超卖预警
            alerts.extend(self._check_overbought_oversold(latest))

            # 3. 背离信号预警
            alerts.extend(self._check_divergence(historical_data, latest))

            # 4. 突破预警
            alerts.extend(self._check_breakout(latest, prev_latest))

            # 5. 多空排列变化预警
            alerts.extend(self._check_ma_alignment(historical_data, latest))

            # 6. 信号冲突预警
            if signal_data:
                alerts.extend(self._check_signal_conflict(signal_data))

            # 统计预警数量
            alert_count = {
                "high": len([a for a in alerts if a["level"] == "high"]),
                "medium": len([a for a in alerts if a["level"] == "medium"]),
                "low": len([a for a in alerts if a["level"] == "low"]),
            }

            # 判定整体风险等级
            overall_risk = self._determine_overall_risk(alert_count)

            return {
                "alerts": alerts,
                "alert_count": alert_count,
                "overall_risk": overall_risk,
            }

        except Exception as e:
            logger.error(f"生成预警失败: {e}", exc_info=True)
            return {
                "alerts": [],
                "alert_count": {"high": 0, "medium": 0, "low": 0},
                "overall_risk": "low",
            }

    def _check_trend_reversal(self, historical_data, latest, prev_latest):
        """检查趋势反转预警"""
        alerts = []

        try:
            # 检查MACD背离
            if len(historical_data) >= 10:
                recent_close = historical_data["close"].iloc[-10:].tolist()
                recent_macd = (
                    historical_data.get(
                        "MACD_12_26_9", pd.Series([0] * len(historical_data))
                    )
                    .iloc[-10:]
                    .tolist()
                )

                # 顶背离：价格新高但MACD未创新高
                if len(recent_close) >= 3 and len(recent_macd) >= 3:
                    if recent_close[-1] > max(recent_close[:-1]) and recent_macd[
                        -1
                    ] < max(recent_macd[:-1]):
                        alerts.append(
                            {
                                "level": "high",
                                "type": self.alert_types["trend_reversal"],
                                "message": "⚠️ 顶背离：价格创新高但MACD未创新高，警惕趋势反转",
                                "indicator": "MACD",
                                "value": f"{recent_macd[-1]:.4f}",
                            }
                        )

                    # 底背离：价格新低但MACD未创新低
                    if recent_close[-1] < min(recent_close[:-1]) and recent_macd[
                        -1
                    ] > min(recent_macd[:-1]):
                        alerts.append(
                            {
                                "level": "medium",
                                "type": self.alert_types["trend_reversal"],
                                "message": "⚠️ 底背离：价格创新低但MACD未创新低，关注反弹机会",
                                "indicator": "MACD",
                                "value": f"{recent_macd[-1]:.4f}",
                            }
                        )

            # 检查均线即将死叉/金叉
            sma_5 = latest.get("SMA_5")
            sma_10 = latest.get("SMA_10")
            prev_sma_5 = prev_latest.get("SMA_5")
            prev_sma_10 = prev_latest.get("SMA_10")

            if pd.notna(sma_5) and pd.notna(sma_10):
                if sma_5 > prev_sma_10 and sma_5 < sma_10:
                    alerts.append(
                        {
                            "level": "medium",
                            "type": self.alert_types["trend_reversal"],
                            "message": "⚠️ 5日均线即将死叉10日均线，警惕趋势转弱",
                            "indicator": "MA",
                            "value": f"MA5={sma_5:.2f}, MA10={sma_10:.2f}",
                        }
                    )
                elif sma_5 < prev_sma_10 and sma_5 > sma_10:
                    alerts.append(
                        {
                            "level": "medium",
                            "type": self.alert_types["trend_reversal"],
                            "message": "⚠️ 5日均线即将金叉10日均线，关注趋势转强",
                            "indicator": "MA",
                            "value": f"MA5={sma_5:.2f}, MA10={sma_10:.2f}",
                        }
                    )

        except Exception as e:
            logger.error(f"检查趋势反转预警失败: {e}")

        return alerts

    def _check_overbought_oversold(self, latest):
        """检查超买超卖预警"""
        alerts = []

        try:
            # RSI超买超卖
            rsi = latest.get("RSI_14")
            if pd.notna(rsi):
                if rsi >= 80:
                    alerts.append(
                        {
                            "level": "high",
                            "type": self.alert_types["overbought_oversold"],
                            "message": f"⚠️ RSI严重超买（{rsi:.1f}），警惕大幅回调风险",
                            "indicator": "RSI",
                            "value": f"{rsi:.1f}",
                        }
                    )
                elif rsi >= 70:
                    alerts.append(
                        {
                            "level": "medium",
                            "type": self.alert_types["overbought_oversold"],
                            "message": f"⚠️ RSI进入超买区域（{rsi:.1f}），短期可能回调",
                            "indicator": "RSI",
                            "value": f"{rsi:.1f}",
                        }
                    )
                elif rsi <= 20:
                    alerts.append(
                        {
                            "level": "medium",
                            "type": self.alert_types["overbought_oversold"],
                            "message": f"⚠️ RSI严重超卖（{rsi:.1f}），关注反弹机会",
                            "indicator": "RSI",
                            "value": f"{rsi:.1f}",
                        }
                    )
                elif rsi <= 30:
                    alerts.append(
                        {
                            "level": "low",
                            "type": self.alert_types["overbought_oversold"],
                            "message": f"⚠️ RSI进入超卖区域（{rsi:.1f}），短期可能反弹",
                            "indicator": "RSI",
                            "value": f"{rsi:.1f}",
                        }
                    )

            # KDJ超买超卖
            kdj_j = latest.get("KDJ_J")
            if pd.notna(kdj_j):
                if kdj_j >= 100:
                    alerts.append(
                        {
                            "level": "high",
                            "type": self.alert_types["overbought_oversold"],
                            "message": f"⚠️ KDJ(J={kdj_j:.1f})极端超买，警惕剧烈回调",
                            "indicator": "KDJ",
                            "value": f"J={kdj_j:.1f}",
                        }
                    )
                elif kdj_j <= 0:
                    alerts.append(
                        {
                            "level": "medium",
                            "type": self.alert_types["overbought_oversold"],
                            "message": f"⚠️ KDJ(J={kdj_j:.1f})极端超卖，关注反弹机会",
                            "indicator": "KDJ",
                            "value": f"J={kdj_j:.1f}",
                        }
                    )

            # CCI超买超卖
            cci = latest.get("CCI_14")
            if pd.notna(cci):
                if cci >= 200:
                    alerts.append(
                        {
                            "level": "high",
                            "type": self.alert_types["overbought_oversold"],
                            "message": f"⚠️ CCI极端超买（{cci:.1f}），警惕剧烈回调",
                            "indicator": "CCI",
                            "value": f"{cci:.1f}",
                        }
                    )
                elif cci >= 100:
                    alerts.append(
                        {
                            "level": "medium",
                            "type": self.alert_types["overbought_oversold"],
                            "message": f"⚠️ CCI进入超买区域（{cci:.1f}），趋势过热",
                            "indicator": "CCI",
                            "value": f"{cci:.1f}",
                        }
                    )
                elif cci <= -200:
                    alerts.append(
                        {
                            "level": "medium",
                            "type": self.alert_types["overbought_oversold"],
                            "message": f"⚠️ CCI极端超卖（{cci:.1f}），关注反弹机会",
                            "indicator": "CCI",
                            "value": f"{cci:.1f}",
                        }
                    )

            # 威廉指标超买超卖
            wr = latest.get("WR_14")
            if pd.notna(wr):
                if wr <= -80:
                    alerts.append(
                        {
                            "level": "high",
                            "type": self.alert_types["overbought_oversold"],
                            "message": f"⚠️ 威廉指标严重超买（{wr:.1f}），警惕回调",
                            "indicator": "WR",
                            "value": f"{wr:.1f}",
                        }
                    )
                elif wr >= -20:
                    alerts.append(
                        {
                            "level": "medium",
                            "type": self.alert_types["overbought_oversold"],
                            "message": f"⚠️ 威廉指标严重超卖（{wr:.1f}），关注反弹",
                            "indicator": "WR",
                            "value": f"{wr:.1f}",
                        }
                    )

        except Exception as e:
            logger.error(f"检查超买超卖预警失败: {e}")

        return alerts

    def _check_divergence(self, historical_data, latest):
        """检查背离信号预警"""
        alerts = []

        try:
            if len(historical_data) < 10:
                return alerts

            # 检查RSI背离
            if "RSI_14" in historical_data.columns:
                recent_close = historical_data["close"].iloc[-10:].tolist()
                recent_rsi = historical_data["RSI_14"].iloc[-10:].tolist()

                # 顶背离
                if len(recent_close) >= 3 and len(recent_rsi) >= 3:
                    if recent_close[-1] > max(recent_close[:-1]) and recent_rsi[
                        -1
                    ] < max(recent_rsi[:-1]):
                        alerts.append(
                            {
                                "level": "high",
                                "type": self.alert_types["divergence"],
                                "message": "⚠️ RSI顶背离：价格创新高但RSI未创新高，警惕趋势反转",
                                "indicator": "RSI",
                                "value": f"RSI={recent_rsi[-1]:.1f}",
                            }
                        )

                    # 底背离
                    if recent_close[-1] < min(recent_close[:-1]) and recent_rsi[
                        -1
                    ] > min(recent_rsi[:-1]):
                        alerts.append(
                            {
                                "level": "medium",
                                "type": self.alert_types["divergence"],
                                "message": "⚠️ RSI底背离：价格创新低但RSI未创新低，关注反弹机会",
                                "indicator": "RSI",
                                "value": f"RSI={recent_rsi[-1]:.1f}",
                            }
                        )

            # 检查OBV背离
            if "OBV" in historical_data.columns:
                obv_values = historical_data["OBV"].iloc[-10:].dropna().tolist()
                close_values = (
                    historical_data["close"].iloc[-len(obv_values) :].tolist()
                )

                if len(close_values) >= 3 and len(obv_values) >= 3:
                    # 顶背离：价格新高但OBV未创新高
                    if close_values[-1] > max(close_values[:-1]) and obv_values[
                        -1
                    ] < max(obv_values[:-1]):
                        alerts.append(
                            {
                                "level": "high",
                                "type": self.alert_types["divergence"],
                                "message": "⚠️ OBV顶背离：价格创新高但资金未同步流入，警惕下跌",
                                "indicator": "OBV",
                                "value": f"OBV={obv_values[-1]:.0f}",
                            }
                        )

                    # 底背离：价格新低但OBV未创新低
                    if close_values[-1] < min(close_values[:-1]) and obv_values[
                        -1
                    ] > min(obv_values[:-1]):
                        alerts.append(
                            {
                                "level": "medium",
                                "type": self.alert_types["divergence"],
                                "message": "⚠️ OBV底背离：价格创新低但资金未同步流出，关注反弹",
                                "indicator": "OBV",
                                "value": f"OBV={obv_values[-1]:.0f}",
                            }
                        )

        except Exception as e:
            logger.error(f"检查背离预警失败: {e}")

        return alerts

    def _check_breakout(self, latest, prev_latest):
        """检查突破预警"""
        alerts = []

        try:
            # 检查布林带突破
            close = latest.get("close")
            bb_upper = latest.get("BBU_20_2.0")
            bb_lower = latest.get("BBL_20_2.0")

            if pd.notna(close) and pd.notna(bb_upper) and pd.notna(bb_lower):
                if close > bb_upper:
                    alerts.append(
                        {
                            "level": "medium",
                            "type": self.alert_types["breakout"],
                            "message": "⚠️ 突破布林带上轨，强势突破但需警惕回调",
                            "indicator": "BOLLINGER",
                            "value": f"{close:.2f} > {bb_upper:.2f}",
                        }
                    )
                elif close < bb_lower:
                    alerts.append(
                        {
                            "level": "medium",
                            "type": self.alert_types["breakout"],
                            "message": "⚠️ 跌破布林带下轨，弱势突破但需关注反弹",
                            "indicator": "BOLLINGER",
                            "value": f"{close:.2f} < {bb_lower:.2f}",
                        }
                    )

            # 检查MACD突破零轴
            macd = latest.get("MACD_12_26_9")
            prev_macd = prev_latest.get("MACD_12_26_9")

            if pd.notna(macd) and pd.notna(prev_macd):
                if macd > 0 and prev_macd <= 0:
                    alerts.append(
                        {
                            "level": "low",
                            "type": self.alert_types["breakout"],
                            "message": "⚠️ MACD突破零轴，进入多头市场",
                            "indicator": "MACD",
                            "value": f"{macd:.4f}",
                        }
                    )
                elif macd < 0 and prev_macd >= 0:
                    alerts.append(
                        {
                            "level": "low",
                            "type": self.alert_types["breakout"],
                            "message": "⚠️ MACD跌破零轴，进入空头市场",
                            "indicator": "MACD",
                            "value": f"{macd:.4f}",
                        }
                    )

        except Exception as e:
            logger.error(f"检查突破预警失败: {e}")

        return alerts

    def _check_ma_alignment(self, historical_data, latest):
        """检查多空排列变化预警"""
        alerts = []

        try:
            # 检查均线排列（短期）
            close = latest.get("close")
            sma_5 = latest.get("SMA_5")
            sma_10 = latest.get("SMA_10")
            sma_20 = latest.get("SMA_20")

            if pd.notna(close) and pd.notna(sma_5) and pd.notna(sma_20):
                # 完美多头排列
                if close > sma_5 > sma_10 > sma_20:
                    alerts.append(
                        {
                            "level": "low",
                            "type": self.alert_types["ma_alignment"],
                            "message": "✅ 短期均线多头排列，趋势强劲",
                            "indicator": "MA",
                            "value": "多头排列",
                        }
                    )
                # 完美空头排列
                elif close < sma_5 < sma_10 < sma_20:
                    alerts.append(
                        {
                            "level": "low",
                            "type": self.alert_types["ma_alignment"],
                            "message": "⚠️ 短期均线空头排列，趋势弱势",
                            "indicator": "MA",
                            "value": "空头排列",
                        }
                    )
                else:
                    alerts.append(
                        {
                            "level": "medium",
                            "type": self.alert_types["ma_alignment"],
                            "message": "⚠️ 均线排列混乱，趋势不明确，观望为主",
                            "indicator": "MA",
                            "value": "排列混乱",
                        }
                    )

        except Exception as e:
            logger.error(f"检查多空排列预警失败: {e}")

        return alerts

    def _check_signal_conflict(self, signal_data):
        """检查信号冲突预警"""
        alerts = []

        try:
            forward_indicators = signal_data.get("forward_indicators", {})

            # 统计买入和卖出信号数量
            buy_signals = [
                k for k, v in forward_indicators.items() if v.get("status") == "买入"
            ]
            sell_signals = [
                k for k, v in forward_indicators.items() if v.get("status") == "卖出"
            ]

            # 如果买入和卖出信号都超过2个，说明信号冲突
            if len(buy_signals) >= 2 and len(sell_signals) >= 2:
                alerts.append(
                    {
                        "level": "medium",
                        "type": self.alert_types["signal_conflict"],
                        "message": f"⚠️ 信号冲突：买入指标({len(buy_signals)})和卖出指标({len(sell_signals)})数量接近，信号不明确，建议观望",
                        "indicator": "Multiple",
                        "value": f"买入:{len(buy_signals)}, 卖出:{len(sell_signals)}",
                    }
                )

            # 检查置信度
            confidence = signal_data.get("confidence", 0)
            if confidence < 30:
                alerts.append(
                    {
                        "level": "low",
                        "type": self.alert_types["signal_conflict"],
                        "message": f"⚠️ 信号置信度低（{confidence:.0f}%），多空方向不明确",
                        "indicator": "Confidence",
                        "value": f"{confidence:.0f}%",
                    }
                )

        except Exception as e:
            logger.error(f"检查信号冲突预警失败: {e}")

        return alerts

    def _determine_overall_risk(self, alert_count):
        """判定整体风险等级"""
        try:
            high_count = alert_count.get("high", 0)
            medium_count = alert_count.get("medium", 0)

            # 如果有2个或以上高风险预警，整体风险为高
            if high_count >= 2:
                return "high"

            # 如果有1个高风险或3个以上中风险预警，整体风险为中高
            elif high_count >= 1 or medium_count >= 3:
                return "high"

            # 如果有1-2个中风险预警，整体风险为中
            elif medium_count >= 1:
                return "medium"

            # 否则整体风险为低
            else:
                return "low"

        except Exception as e:
            logger.error(f"判定整体风险等级失败: {e}")
            return "low"


def generate_alert_summary(alert_data):
    """
    生成预警摘要文本

    参数:
        alert_data: AlertSystem.generate_alerts() 返回的数据

    返回:
        str: 预警摘要
    """
    try:
        alerts = alert_data.get("alerts", [])
        alert_count = alert_data.get("alert_count", {})
        overall_risk = alert_data.get("overall_risk", "low")

        if not alerts:
            return "当前无预警信号，技术面相对平稳。"

        # 风险等级描述
        risk_desc = {"high": "高风险", "medium": "中风险", "low": "低风险"}

        # 生成摘要
        summary_parts = []

        # 整体风险
        summary_parts.append(
            f"整体风险等级：{risk_desc.get(overall_risk, overall_risk)}"
        )

        # 预警数量
        high_count = alert_count.get("high", 0)
        medium_count = alert_count.get("medium", 0)
        low_count = alert_count.get("low", 0)

        if high_count > 0 or medium_count > 0 or low_count > 0:
            count_parts = []
            if high_count > 0:
                count_parts.append(f"{high_count}个高风险")
            if medium_count > 0:
                count_parts.append(f"{medium_count}个中风险")
            if low_count > 0:
                count_parts.append(f"{low_count}个低风险")
            summary_parts.append(f"预警数量：{'、'.join(count_parts)}")

        # 关键预警（只显示高风险和前3个中风险）
        key_alerts = [a for a in alerts if a["level"] == "high"]
        medium_alerts = [a for a in alerts if a["level"] == "medium"][:2]
        key_alerts.extend(medium_alerts)

        if key_alerts:
            summary_parts.append("关键预警：")
            for alert in key_alerts:
                summary_parts.append(f"  • {alert['message']}")

        return "；".join(summary_parts) + "。"

    except Exception as e:
        logger.error(f"生成预警摘要失败: {e}")
        return "预警摘要生成失败"
