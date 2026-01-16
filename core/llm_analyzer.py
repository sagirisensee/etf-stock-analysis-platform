# llm_analyzer.py (优化 prompt_data 和 system_prompt)

import os
import json
import logging
import asyncio
import pandas as pd
from openai import OpenAI

logger = logging.getLogger(__name__)


# --- 配置 ---
def _get_api_provider():
    """检测API提供商类型"""
    api_base = os.getenv("LLM_API_BASE", "").lower()
    if "perplexity" in api_base:
        return "perplexity"
    elif "openai" in api_base or "siliconflow" in api_base:
        return "openai"
    else:
        return "openai"  # 默认为OpenAI格式


def _get_openai_client():
    """动态获取OpenAI客户端，优先使用环境变量中的配置"""
    try:
        api_base = os.getenv("LLM_API_BASE")
        api_key = os.getenv("LLM_API_KEY")

        if not api_base or not api_key:
            logger.warning("LLM API配置不完整，请在Web界面配置或设置环境变量")
            return None

        return OpenAI(
            base_url=api_base,
            api_key=api_key,
        )
    except Exception as e:
        logger.error(f"初始化OpenAI客户端失败: {e}")
        return None


# 全局客户端变量
client = None


# --- 核心函数 ---
async def get_llm_score_and_analysis(
    etf_data,
    daily_trend_data,
    forward_indicators_data=None,
    minute_30_data=None,
    minute_60_data=None,
    minute_support_resistance=None,
    minute_entry_signals=None,
    signal_data=None,
    alert_data=None,
    prediction_data=None,
):
    """调用大模型对单支ETF进行分析和打分（支持多周期数据）"""
    # 动态获取客户端
    current_client = _get_openai_client()
    if current_client is None:
        return {
            "signal": "持有",
            "confidence": 50,
            "probability": "涨跌概率未知",
            "support": "未知",
            "resistance": "未知",
            "target": "未知",
            "stop_loss": "未知",
            "comment": "LLM服务未配置或初始化失败。请在配置页面设置AI模型参数。",
        }

    # 检测API提供商
    api_provider = _get_api_provider()
    logger.info(f"检测到API提供商: {api_provider}")

    # --- 1. 修改 prompt_data 的结构 ---
    # 将所有必要的信息都扁平化，直接传递给LLM
    combined_data = {
        "投资标的名称": etf_data.get("name"),
        "代码": etf_data.get("code"),
        "日内涨跌幅": f"{etf_data.get('change', 0):.2f}%",
        "日线级别整体趋势": daily_trend_data.get("status"),
        "盘中技术信号": etf_data.get("analysis_points", []),
        "详细技术指标分析列表": daily_trend_data.get(
            "technical_indicators_summary", []
        ),
    }

    # 添加前瞻性指标数据（日线级别）
    if forward_indicators_data:
        combined_data["日线技术指标（前瞻性）"] = {
            "RSI12（日线）": forward_indicators_data.get("RSI_12"),
            "KDJ（日线）": f"K={forward_indicators_data.get('KDJ_K'):.1f}, D={forward_indicators_data.get('KDJ_D'):.1f}, J={forward_indicators_data.get('KDJ_J'):.1f}"
            if pd.notna(forward_indicators_data.get("KDJ_K"))
            else None,
            "CCI（日线）": forward_indicators_data.get("CCI_14"),
            "威廉指标（日线）": forward_indicators_data.get("WR_14"),
            "OBV（日线）": "资金流入"
            if forward_indicators_data.get("OBV_change", 0) > 0
            else (
                "资金流出"
                if forward_indicators_data.get("OBV_change", 0) < 0
                else "资金持平"
            )
            if pd.notna(forward_indicators_data.get("OBV"))
            else None,
        }

    # 添加分钟线数据（新增）- 明确标注时间周期
    minute_data = {}
    if minute_30_data is not None and not minute_30_data.empty:
        latest_30 = minute_30_data.iloc[-1]
        minute_data["30分钟线指标"] = {
            "RSI12（30分钟）": latest_30.get("RSI_12"),
            "KDJ（30分钟）": f"K={latest_30.get('KDJ_K'):.1f}, D={latest_30.get('KDJ_D'):.1f}, J={latest_30.get('KDJ_J'):.1f}"
            if pd.notna(latest_30.get("KDJ_K"))
            else None,
            "MACD（30分钟）": latest_30.get("MACD_5_10_5"),
            "布林带（30分钟）": f"上轨:{latest_30.get('BBU_10_2.0'):.2f}, 中轨:{latest_30.get('BBM_10_2.0'):.2f}, 下轨:{latest_30.get('BBL_10_2.0'):.2f}"
            if pd.notna(latest_30.get("BBU_10_2.0"))
            else None,
        }

    if minute_60_data is not None and not minute_60_data.empty:
        latest_60 = minute_60_data.iloc[-1]
        minute_data["60分钟线指标"] = {
            "RSI12（60分钟）": latest_60.get("RSI_12"),
            "KDJ（60分钟）": f"K={latest_60.get('KDJ_K'):.1f}, D={latest_60.get('KDJ_D'):.1f}, J={latest_60.get('KDJ_J'):.1f}"
            if pd.notna(latest_60.get("KDJ_K"))
            else None,
            "MACD（60分钟）": latest_60.get("MACD_5_10_5"),
            "布林带（60分钟）": f"上轨:{latest_60.get('BBU_10_2.0'):.2f}, 中轨:{latest_60.get('BBM_10_2.0'):.2f}, 下轨:{latest_60.get('BBL_10_2.0'):.2f}"
            if pd.notna(latest_60.get("BBU_10_2.0"))
            else None,
        }

    if minute_data:
        combined_data["分钟线技术指标（短线）"] = minute_data

    # 添加支撑阻力位（新增）
    if minute_support_resistance:
        support_30 = minute_support_resistance.get("support_30", [])
        resistance_30 = minute_support_resistance.get("resistance_30", [])
        support_60 = minute_support_resistance.get("support_60", [])
        resistance_60 = minute_support_resistance.get("resistance_60", [])

        support_str_30 = (
            ", ".join([f"{s:.2f}" for s in support_30[-2:]]) if support_30 else "无"
        )
        resistance_str_30 = (
            ", ".join([f"{r:.2f}" for r in resistance_30[:2]])
            if resistance_30
            else "无"
        )
        support_str_60 = (
            ", ".join([f"{s:.2f}" for s in support_60[-2:]]) if support_60 else "无"
        )
        resistance_str_60 = (
            ", ".join([f"{r:.2f}" for r in resistance_60[:2]])
            if resistance_60
            else "无"
        )

        combined_data["分钟线支撑阻力位"] = {
            "30分钟支撑": support_str_30,
            "30分钟阻力": resistance_str_30,
            "60分钟支撑": support_str_60,
            "60分钟阻力": resistance_str_60,
        }

    # 添加入场信号（新增）
    if minute_entry_signals:
        entry_price_buy = minute_entry_signals.get("entry_price_buy")
        entry_price_sell = minute_entry_signals.get("entry_price_sell")
        entry_confidence = minute_entry_signals.get("entry_confidence")
        entry_reason = minute_entry_signals.get("entry_reason")

        combined_data["推荐入场价位"] = {
            "买入价位": f"{entry_price_buy:.2f}"
            if entry_price_buy
            else "无明确买入价位",
            "卖出价位": f"{entry_price_sell:.2f}"
            if entry_price_sell
            else "无明确卖出价位",
            "信心度": entry_confidence,
            "入场理由": entry_reason,
        }

    # 添加买卖信号数据
    if signal_data:
        signal_type = signal_data.get("signal_type", "Hold")
        signal_score = signal_data.get("signal_score", 50)
        signal_confidence = signal_data.get("confidence", 0)
        signal_strength = signal_data.get("signal_strength", "Weak")

        signal_type_cn = {
            "Strong Buy": "强烈买入",
            "Buy": "买入",
            "Hold": "持有",
            "Sell": "卖出",
            "Strong Sell": "强烈卖出",
        }

        combined_data["买卖信号"] = {
            "信号类型": signal_type_cn.get(signal_type, signal_type),
            "信号强度": signal_strength,
            "综合评分": f"{signal_score:.1f}/100",
            "信号置信度": f"{signal_confidence:.0f}%",
        }

        if signal_data.get("signal_reasons"):
            combined_data["买卖信号"]["信号理由"] = signal_data.get(
                "signal_reasons", []
            )

    # 添加预警数据
    if alert_data:
        overall_risk = alert_data.get("overall_risk", "low")
        alert_count = alert_data.get("alert_count", {})
        alerts = alert_data.get("alerts", [])

        overall_risk_cn = {"high": "高风险", "medium": "中风险", "low": "低风险"}

        combined_data["风险预警"] = {
            "整体风险等级": overall_risk_cn.get(overall_risk, overall_risk),
            "预警数量": f"高风险:{alert_count.get('high', 0)}, 中风险:{alert_count.get('medium', 0)}, 低风险:{alert_count.get('low', 0)}",
        }

        if alerts:
            combined_data["风险预警"]["关键预警"] = [
                alert["message"] for alert in alerts[:3]
            ]

    # 添加价格预测数据
    if prediction_data:
        predictions = prediction_data.get("predictions", {})
        pred_1d = predictions.get("prediction_1d", {})
        pred_3d = predictions.get("prediction_3d", {})
        trend_prob = prediction_data.get("trend_probability", {})
        current_price = prediction_data.get("current_price")
        support_resistance = prediction_data.get("support_resistance", {})

        # 获取 forward_indicators - 从 daily_trend_data 中
        forward_indicators_data = daily_trend_data.get("forward_indicators", {})

        combined_data["技术指标数据（日线）"] = {
            "当前价格": current_price,
            "RSI12（日线）": float(forward_indicators_data.get("RSI_12", 0))
            if pd.notna(forward_indicators_data.get("RSI_12"))
            else None,
            "KDJ（日线）": f"K={forward_indicators_data.get('KDJ_K', 0):.1f}, D={forward_indicators_data.get('KDJ_D', 0):.1f}, J={forward_indicators_data.get('KDJ_J', 0):.1f}"
            if pd.notna(forward_indicators_data.get("KDJ_K"))
            else None,
            "CCI（日线）": forward_indicators_data.get("CCI_14", 0)
            if pd.notna(forward_indicators_data.get("CCI_14"))
            else None,
            "威廉指标（日线）": forward_indicators_data.get("WR_14", 0)
            if pd.notna(forward_indicators_data.get("WR_14"))
            else None,
            "OBV（日线）": "资金流入"
            if forward_indicators_data.get("OBV_change", 0) > 0
            else (
                "资金流出"
                if forward_indicators_data.get("OBV_change", 0) < 0
                else "资金持平"
            )
            if pd.notna(forward_indicators_data.get("OBV"))
            else None,
        }

        support_list = support_resistance.get("support", [])
        resistance_list = support_resistance.get("resistance", [])
        support_str = (
            ", ".join([f"{s:.2f}" for s in support_list]) if support_list else "无"
        )
        resistance_str = (
            ", ".join([f"{r:.2f}" for r in resistance_list])
            if resistance_list
            else "无"
        )

        combined_data["价格区间"] = {"支撑位": support_str, "阻力位": resistance_str}

        support_list = support_resistance.get("support", [])
        resistance_list = support_resistance.get("resistance", [])
        support_str = (
            ", ".join([f"{s:.2f}" for s in support_list]) if support_list else "无"
        )
        resistance_str = (
            ", ".join([f"{r:.2f}" for r in resistance_list])
            if resistance_list
            else "无"
        )

        combined_data["价格区间"] = {"支撑位": support_str, "阻力位": resistance_str}

    # --- 2. 优化 system_prompt ---
    # 完全AI驱动 - 所有概率由AI自主计算
    system_prompt = (
        "你是一个专业的量化交易分析师，完全基于技术指标数据进行概率预测和交易决策。\n"
        "**核心原则**：所有趋势概率（上涨/下跌/横盘）由你自主研判，不依赖任何预计算的数值。\n"
        "**关键要求**：必须严格区分日线指标和分钟线指标的时间周期，避免混淆不同周期的数值。\n\n"
        "分析内容包括：\n"
        "1. **概览**：投资标的名称、代码、当前价格。\n"
        "2. **技术指标分析**（权重100%）：\n"
        "   - **日线指标（前瞻性，更可靠）**：RSI12（日线）、KDJ(K/D/J)（日线）、CCI(14)（日线）、威廉指标（日线）、OBV（日线）\n"
        "   - **分钟线指标（短线，更灵敏）**：30分钟/60分钟线的RSI、KDJ、MACD、布林带\n"
        "   - **均线系统**：SMA_5、SMA_10、SMA_20的位置关系\n"
        "3. **重要提醒**：\n"
        "   - **日线KDJ**和**分钟线KDJ**是不同时间周期的指标，数值可能差异很大\n"
        "   - **日线指标**反映中长期趋势\n"
        "   - **分钟线指标**反映短期波动\n"
        "   - 在分析时要明确区分并正确引用对应周期的指标数值\n"
        "4. **支撑阻力位分析**：\n"
        "   - 当前价格相对支撑位/阻力位的位置\n"
        "   - 判断是否接近关键价位\n"
        "5. **自主概率计算**（核心任务）：\n"
        "   - 基于所有技术指标的综合判断，重点参考日线指标\n"
        "   - 分别计算：上涨概率、下跌概率、横盘概率\n"
        "   - **必须**：三个概率之和等于100%\n"
        "   - **依据**：明确说明得出这些概率的具体指标依据，注明是日线还是分钟线指标\n"
        "6. **价格预测**（基于概率）：\n"
        "   - 1日预测：根据1日趋势判断，给出目标价和置信度\n"
        "   - 3日预测：根据3日预期，给出目标价和置信度\n"
        "7. **买卖信号**：\n"
        "   - 强烈买入：上涨概率>60% + 关键超卖信号（日线指标为主）\n"
        "   - 买入：上涨概率50-60% + 接近支撑位\n"
        "   - 持有：没有明确方向或横盘概率最高\n"
        "   - 卖出：下跌概率50-60% + 接近阻力位\n"
        "   - 强烈卖出：下跌概率>60% + 关键超买信号（日线指标为主）\n"
        "8. **交易建议**：\n"
        "   - 支撑位：详细列出最重要的2-3个支撑位\n"
        "   - 阻力位：详细列出最重要的2-3个阻力位\n"
        "   - 目标价：基于上涨概率计算的目标价\n"
        "   - 止损价：基于风险控制设置\n"
        "\n"
        "请严格以JSON格式返回：\n"
        "{\n"
        '  "signal": "买入",\n'
        '  "confidence": 75,\n'
        '  "probability": "上涨概率65%",\n'
        '  "detailed_probability": {"up": 65, "down": 25, "sideways": 10},\n'
        '  "pred_1d": {"trend": "上涨", "target": 1.62, "confidence": 60},\n'
        '  "pred_3d": {"trend": "上涨", "target": 1.65, "confidence": 55},\n'
        '  "support": "1.55-1.57",\n'
        '  "resistance": "1.62-1.65",\n'
        '  "target": "1.65",\n'
        '  "stop_loss": "1.52",\n'
        '  "comment": "基于日线RSI(72.8)进入超买区、日线KDJ(K=78.5, D=77.2, J=81.1)正常、分钟线KDJ(J=1.1)低位，综合判断上涨概率40%。指标依据：日线RSI超买提示风险，日线KDJ正常但分钟线KDJ低位显示有超跌反弹需求，形成短期矛盾信号。"\n'
        "}\n"
        "\n"
        "字段说明：\n"
        "- signal: 买卖信号（强烈买入/买入/持有/卖出/强烈卖出）\n"
        "- confidence: 信号置信度（0-100）\n"
        "- probability: 今日涨跌概率文本（如'上涨概率65%'）\n"
        "- detailed_probability: 详细概率对象，必须包含up/down/sideways三个数字，之和=100\n"
        "- pred_1d: 1日预测 {trend: 上涨/下跌/横盘, target: 目标价, confidence: 0-100}\n"
        "- pred_3d: 3日预测 {trend: 上涨/下跌/横盘, target: 目标价, confidence: 0-100}\n"
        "- support: 支撑位（价格区间或单一价格）\n"
        "- resistance: 阻力位（价格区间或单一价格）\n"
        "- target: 目标价（止盈价）\n"
        "- stop_loss: 止损价\n"
        "- comment: 点评（必须包含：概率依据、具体指标数值、操作建议）\n"
        "\n"
        "**特别注意**：\n"
        "1. 所有概率由你自主计算，不要使用系统提供的任何概率值\n"
        "2. detailed_probability中的三个数字必须精确到整数或小数点后1位，且总和=100\n"
        "3. comment中必须说明得出概率的具体指标依据，并明确标注是日线还是分钟线指标\n"
        "4. 预测价格要基于你计算的概率合理推导\n"
        "5. **严禁混淆日线指标和分钟线指标的数值**\n"
        "6. 当出现矛盾信号时（如日线KDJ正常但分钟线KDJ低位），要在comment中明确说明这种矛盾\n"
    )

    # 重试机制配置
    max_retries = 3
    retry_delay = 2  # 秒

    for attempt in range(max_retries):
        try:
            # 根据API提供商构建不同的请求参数
            request_params = {
                "model": os.getenv("LLM_MODEL_NAME", "sonar-pro"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(
                            combined_data, ensure_ascii=False, indent=2
                        ),
                    },
                ],
            }

            # 根据API提供商添加不同的参数
            if api_provider == "perplexity":
                # Perplexity AI 不使用response_format
                request_params.update(
                    {"max_tokens": 1000, "temperature": 0.7, "top_p": 0.9}
                )
                logger.info("使用Perplexity AI格式请求（无response_format）")
            else:
                # OpenAI 使用json_object格式
                request_params.update({"response_format": {"type": "json_object"}})
                logger.info("使用OpenAI格式请求（json_object）")

            response = await asyncio.to_thread(
                current_client.chat.completions.create, **request_params
            )

            raw_content = response.choices[0].message.content
            if not raw_content:
                logger.warning(f"LLM为空内容返回: {etf_data.get('name')}")
                return {
                    "signal": "持有",
                    "confidence": 50,
                    "probability": "涨跌概率未知",
                    "support": "未知",
                    "resistance": "未知",
                    "target": "未知",
                    "stop_loss": "未知",
                    "comment": "模型未提供有效分析。",
                }

            # 根据API提供商进行不同的解析
            if api_provider == "perplexity":
                # Perplexity AI 特殊解析：从文本中提取JSON
                result = _parse_perplexity_response(raw_content)
            else:
                # OpenAI 兼容格式解析
                result = _parse_openai_response(raw_content)

            return result

        except Exception as e:
            error_str = str(e)
            logger.warning(
                f"LLM请求失败 (尝试 {attempt + 1}/{max_retries}): {error_str}"
            )

            # 检查是否是服务繁忙错误
            if (
                "503" in error_str
                or "too busy" in error_str.lower()
                or "service unavailable" in error_str.lower()
            ):
                if attempt < max_retries - 1:  # 不是最后一次尝试
                    logger.info(f"检测到服务繁忙，等待 {retry_delay} 秒后重试...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # 指数退避
                    continue
                else:
                    # 最后一次尝试也失败了
                    return {
                        "signal": "持有",
                        "confidence": 50,
                        "probability": "涨跌概率未知",
                        "detailed_probability": {},
                        "pred_1d": {},
                        "pred_3d": {},
                        "support": "未知",
                        "resistance": "未知",
                        "target": "未知",
                        "stop_loss": "未知",
                        "comment": "AI分析服务繁忙，请稍后再试。当前返回默认评分。",
                    }
            else:
                # 其他类型的错误，不重试
                logger.error(f"LLM调用失败，错误类型: {error_str}", exc_info=True)
                return {
                    "signal": "持有",
                    "confidence": 50,
                    "probability": "涨跌概率未知",
                    "detailed_probability": {},
                    "pred_1d": {},
                    "pred_3d": {},
                    "support": "未知",
                    "resistance": "未知",
                    "target": "未知",
                    "stop_loss": "未知",
                    "comment": f"AI分析服务异常: {error_str}",
                }

    # 如果所有重试都失败了
    return {
        "signal": "持有",
        "confidence": 50,
        "probability": "涨跌概率未知",
        "detailed_probability": {},
        "pred_1d": {},
        "pred_3d": {},
        "support": "未知",
        "resistance": "未知",
        "target": "未知",
        "stop_loss": "未知",
        "comment": "AI分析服务暂时不可用，请稍后再试。",
    }


def _parse_perplexity_response(raw_content):
    """解析Perplexity AI的响应"""
    import re

    logger.info(f"原始响应内容: {raw_content[:500]}...")

    try:
        # 尝试直接解析JSON
        parsed_json = json.loads(raw_content)
        if isinstance(parsed_json, dict):
            signal = parsed_json.get("signal", "持有")
            confidence = parsed_json.get("confidence", 50)
            probability = parsed_json.get("probability", "涨跌概率未知")
            support = parsed_json.get("support", "未知")
            resistance = parsed_json.get("resistance", "未知")
            target = parsed_json.get("target", "未知")
            stop_loss = parsed_json.get("stop_loss", "未知")
            comment = parsed_json.get("comment", "Perplexity AI分析完成")
            logger.info(
                f"Perplexity解析成功: signal={signal}, confidence={confidence}, probability={probability}, support={support}, resistance={resistance}, target={target}, stop_loss={stop_loss}"
            )
            return {
                "signal": str(signal),
                "confidence": int(confidence)
                if isinstance(confidence, (int, float))
                else 50,
                "probability": str(probability),
                "detailed_probability": parsed_json.get("detailed_probability", {}),
                "pred_1d": parsed_json.get("pred_1d", {}),
                "pred_3d": parsed_json.get("pred_3d", {}),
                "support": str(support),
                "resistance": str(resistance),
                "target": str(target),
                "stop_loss": str(stop_loss),
                "comment": str(comment),
            }
    except json.JSONDecodeError:
        pass

    # 如果直接解析失败，尝试从文本中提取JSON
    try:
        # 查找JSON模式（包含signal字段）
        json_pattern = r'\{[^{}]*"signal"[^{}]*\}'
        json_match = re.search(json_pattern, raw_content, re.DOTALL)

        if json_match:
            json_str = json_match.group(0)
            parsed_json = json.loads(json_str)
            signal = parsed_json.get("signal", "持有")
            confidence = parsed_json.get("confidence", 50)
            probability = parsed_json.get("probability", "涨跌概率未知")
            support = parsed_json.get("support", "未知")
            resistance = parsed_json.get("resistance", "未知")
            target = parsed_json.get("target", "未知")
            stop_loss = parsed_json.get("stop_loss", "未知")
            comment = parsed_json.get("comment", "Perplexity AI分析完成")
            logger.info(
                f"Perplexity从文本提取成功: signal={signal}, confidence={confidence}, probability={probability}, support={support}, resistance={resistance}, target={target}, stop_loss={stop_loss}"
            )
            return {
                "signal": str(signal),
                "confidence": int(confidence)
                if isinstance(confidence, (int, float))
                else 50,
                "probability": str(probability),
                "detailed_probability": parsed_json.get("detailed_probability", {}),
                "pred_1d": parsed_json.get("pred_1d", {}),
                "pred_3d": parsed_json.get("pred_3d", {}),
                "support": str(support),
                "resistance": str(resistance),
                "target": str(target),
                "stop_loss": str(stop_loss),
                "comment": str(comment),
            }
    except (json.JSONDecodeError, AttributeError):
        pass

    # 如果都失败了，尝试逐字段提取
    try:
        # 查找信号字段
        signal_pattern = r'"signal":\s*"([^"]*)"'
        signal_match = re.search(signal_pattern, raw_content)
        signal = signal_match.group(1) if signal_match else "持有"

        # 查找confidence字段
        confidence_pattern = r'"confidence":\s*(\d+)'
        confidence_match = re.search(confidence_pattern, raw_content)
        confidence = int(confidence_match.group(1)) if confidence_match else 50

        # 查找probability字段
        probability_pattern = r'"probability":\s*"([^"]*)"'
        probability_match = re.search(probability_pattern, raw_content)
        probability = (
            probability_match.group(1) if probability_match else "涨跌概率未知"
        )

        # 查找support字段
        support_pattern = r'"support":\s*"([^"]*)"'
        support_match = re.search(support_pattern, raw_content)
        support = support_match.group(1) if support_match else "未知"

        # 查找resistance字段
        resistance_pattern = r'"resistance":\s*"([^"]*)"'
        resistance_match = re.search(resistance_pattern, raw_content)
        resistance = resistance_match.group(1) if resistance_match else "未知"

        # 查找target字段
        target_pattern = r'"target":\s*"([^"]*)"'
        target_match = re.search(target_pattern, raw_content)
        target = target_match.group(1) if target_match else "未知"

        # 查找stop_loss字段
        stop_loss_pattern = r'"stop_loss":\s*"([^"]*)"'
        stop_loss_match = re.search(stop_loss_pattern, raw_content)
        stop_loss = stop_loss_match.group(1) if stop_loss_match else "未知"

        # 查找评论内容
        comment_pattern = r'"comment":\s*"([^"]*)"'
        comment_match = re.search(comment_pattern, raw_content)
        comment = comment_match.group(1) if comment_match else "Perplexity AI分析完成"

        logger.info(
            f"Perplexity逐字段提取成功: signal={signal}, confidence={confidence}, probability={probability}, support={support}, resistance={resistance}, target={target}, stop_loss={stop_loss}"
        )
        return {
            "signal": signal,
            "confidence": confidence,
            "probability": probability,
            "support": support,
            "resistance": resistance,
            "target": target,
            "stop_loss": stop_loss,
            "comment": comment,
        }
    except (AttributeError, ValueError):
        pass

    # 最后的兜底方案
    logger.warning(f"Perplexity AI响应解析失败，使用默认值: {raw_content[:200]}...")
    return {
        "signal": "持有",
        "confidence": 50,
        "probability": "涨跌概率未知",
        "support": "未知",
        "resistance": "未知",
        "target": "未知",
        "stop_loss": "未知",
        "comment": "Perplexity AI分析完成，但响应格式需要优化",
    }
    pass

    # 如果直接解析失败，尝试从文本中提取JSON
    try:
        # 查找JSON模式（包含signal字段）
        json_pattern = r'\{[^{}]*"signal"[^{}]*\}'
        json_match = re.search(json_pattern, raw_content, re.DOTALL)

        if json_match:
            json_str = json_match.group(0)
            parsed_json = json.loads(json_str)
            signal = parsed_json.get("signal", "持有")
            confidence = parsed_json.get("confidence", 50)
            probability = parsed_json.get("probability", "涨跌概率未知")
            support = parsed_json.get("support", "未知")
            resistance = parsed_json.get("resistance", "未知")
            target = parsed_json.get("target", "未知")
            stop_loss = parsed_json.get("stop_loss", "未知")
            comment = parsed_json.get("comment", "Perplexity AI分析完成")
            logger.info(
                f"Perplexity从文本提取成功: signal={signal}, confidence={confidence}, probability={probability}, support={support}, resistance={resistance}, target={target}, stop_loss={stop_loss}"
            )
            return {
                "signal": str(signal),
                "confidence": int(confidence)
                if isinstance(confidence, (int, float))
                else 50,
                "probability": str(probability),
                "detailed_probability": parsed_json.get("detailed_probability", {}),
                "pred_1d": parsed_json.get("pred_1d", {}),
                "pred_3d": parsed_json.get("pred_3d", {}),
                "support": str(support),
                "resistance": str(resistance),
                "target": str(target),
                "stop_loss": str(stop_loss),
                "comment": str(comment),
            }
    except (json.JSONDecodeError, AttributeError):
        pass

    # 如果都失败了，尝试提取数字评分
    try:
        # 查找评分数字
        score_pattern = r'"score":\s*(\d+(?:\.\d+)?)'
        score_match = re.search(score_pattern, raw_content)
        score = float(score_match.group(1)) if score_match else 50

        # 查找信号字段
        signal_pattern = r'"signal":\s*"([^"]*)"'
        signal_match = re.search(signal_pattern, raw_content)
        signal = signal_match.group(1) if signal_match else "持有"

        # 查找评论内容
        comment_pattern = r'"comment":\s*"([^"]*)"'
        comment_match = re.search(comment_pattern, raw_content)
        comment = comment_match.group(1) if comment_match else "Perplexity AI分析完成"

        # 查找confidence字段
        confidence_pattern = r'"confidence":\s*(\d+)'
        confidence_match = re.search(confidence_pattern, raw_content)
        confidence = int(confidence_match.group(1)) if confidence_match else 50

        # 查找probability字段
        probability_pattern = r'"probability":\s*"([^"]*)"'
        probability_match = re.search(probability_pattern, raw_content)
        probability = (
            probability_match.group(1) if probability_match else "涨跌概率未知"
        )

        # 查找support字段
        support_pattern = r'"support":\s*"([^"]*)"'
        support_match = re.search(support_pattern, raw_content)
        support = support_match.group(1) if support_match else "未知"

        # 查找resistance字段
        resistance_pattern = r'"resistance":\s*"([^"]*)"'
        resistance_match = re.search(resistance_pattern, raw_content)
        resistance = resistance_match.group(1) if resistance_match else "未知"

        # 查找target字段
        target_pattern = r'"target":\s*"([^"]*)"'
        target_match = re.search(target_pattern, raw_content)
        target = target_match.group(1) if target_match else "未知"

        # 查找stop_loss字段
        stop_loss_pattern = r'"stop_loss":\s*"([^"]*)"'
        stop_loss_match = re.search(stop_loss_pattern, raw_content)
        stop_loss = stop_loss_match.group(1) if stop_loss_match else "未知"

        logger.info(
            f"Perplexity逐字段提取成功: signal={signal}, confidence={confidence}, probability={probability}, support={support}, resistance={resistance}, target={target}, stop_loss={stop_loss}"
        )
        return {
            "signal": signal,
            "confidence": confidence,
            "probability": probability,
            "support": support,
            "resistance": resistance,
            "target": target,
            "stop_loss": stop_loss,
            "comment": comment,
        }
    except (AttributeError, ValueError):
        pass

    # 最后的兜底方案
    logger.warning(f"Perplexity AI响应解析失败，使用默认值: {raw_content[:200]}...")
    return {
        "signal": "持有",
        "confidence": 50,
        "probability": "涨跌概率未知",
        "support": "未知",
        "resistance": "未知",
        "target": "未知",
        "stop_loss": "未知",
        "comment": "Perplexity AI分析完成，但响应格式需要优化",
    }
    pass

    # 如果直接解析失败，尝试从文本中提取JSON
    try:
        # 查找JSON模式（包含signal字段）
        json_pattern = r'\{[^{}]*"signal"[^{}]*\}'
        json_match = re.search(json_pattern, raw_content, re.DOTALL)

        if json_match:
            json_str = json_match.group(0)
            parsed_json = json.loads(json_str)
            signal = parsed_json.get("signal", "持有")
            confidence = parsed_json.get("confidence", 50)
            probability = parsed_json.get("probability", "涨跌概率未知")
            support = parsed_json.get("support", "未知")
            resistance = parsed_json.get("resistance", "未知")
            target = parsed_json.get("target", "未知")
            stop_loss = parsed_json.get("stop_loss", "未知")
            comment = parsed_json.get("comment", "Perplexity AI分析完成")
            return {
                "signal": str(signal),
                "confidence": int(confidence)
                if isinstance(confidence, (int, float))
                else 50,
                "probability": str(probability),
                "detailed_probability": parsed_json.get("detailed_probability", {}),
                "pred_1d": parsed_json.get("pred_1d", {}),
                "pred_3d": parsed_json.get("pred_3d", {}),
                "support": str(support),
                "resistance": str(resistance),
                "target": str(target),
                "stop_loss": str(stop_loss),
                "comment": str(comment),
            }
    except (json.JSONDecodeError, AttributeError):
        pass

    # 最后的兜底方案
    logger.warning(f"Perplexity AI响应解析失败，使用默认值: {raw_content[:200]}...")
    return {
        "signal": "持有",
        "confidence": 50,
        "probability": "涨跌概率未知",
        "support": "未知",
        "resistance": "未知",
        "target": "未知",
        "stop_loss": "未知",
        "comment": "Perplexity AI分析完成，但响应格式需要优化",
    }


def _adjust_score_by_comment(score, comment):
    """
    根据点评内容智能调整评分
    如果点评中提到风险、谨慎、警惕等词汇，应该降低评分
    """
    if not comment:
        return score

    comment_lower = comment.lower()

    # 风险词汇，需要降低评分
    risk_keywords = [
        "风险",
        "谨慎",
        "警惕",
        "回调",
        "调整",
        "下跌",
        "压力",
        "阻力",
        "超买",
        "超卖",
        "震荡",
        "不确定",
        "观望",
        "注意",
        "关注",
        "空头",
        "减弱",
        "缩短",
        "死叉",
        "跌破",
        "下方",
        "偏弱",
    ]

    # 积极词汇，可以保持或略微提高评分
    positive_keywords = [
        "强势",
        "突破",
        "金叉",
        "多头",
        "上方",
        "增长",
        "增强",
        "看好",
        "乐观",
        "积极",
        "买入",
        "持有",
        "推荐",
    ]

    # 计算风险词汇数量
    risk_count = sum(1 for keyword in risk_keywords if keyword in comment_lower)
    positive_count = sum(1 for keyword in positive_keywords if keyword in comment_lower)

    # 根据风险词汇调整评分
    if risk_count > 0:
        # 每个风险词汇降低1-3分，最多降低20分
        risk_adjustment = min(risk_count * 2, 20)  # 最多降低20分
        score = max(score - risk_adjustment, 0)
        logger.info(f"检测到{risk_count}个风险词汇，降低评分{risk_adjustment}分")

    # 如果只有积极词汇且没有风险词汇，可以略微提高
    elif positive_count > 0 and risk_count == 0:
        # 最多提高2分
        positive_adjustment = min(positive_count, 2)
        score = min(score + positive_adjustment, 99)
        logger.info(
            f"检测到{positive_count}个积极词汇，提高评分{positive_adjustment}分"
        )

    return score


def _calculate_weighted_score(base_score, technical_indicators):
    """
    基于技术指标重要性进行权重评分调整
    根据实际技术分析中指标的重要性来分配权重
    """
    if not technical_indicators:
        return base_score

    # 技术指标权重配置（基于实际重要性）
    indicator_weights = {
        # 均线指标权重（最重要，占40%）
        "均线": 0.4,
        "SMA": 0.4,
        "MA": 0.4,
        "金叉": 0.35,
        "死叉": 0.35,
        "多头排列": 0.4,
        "空头排列": 0.4,
        # MACD指标权重（次重要，占30%）
        "MACD": 0.3,
        "MACD金叉": 0.3,
        "MACD死叉": 0.3,
        "红柱": 0.25,
        "绿柱": 0.25,
        "零轴": 0.2,
        # 布林带指标权重（第三重要，占20%）
        "布林": 0.2,
        "布林上轨": 0.2,
        "布林下轨": 0.2,
        "布林中轨": 0.15,
        "突破": 0.25,
        "跌破": 0.25,
        # 其他指标权重（占10%）
        "成交量": 0.1,
        "量能": 0.1,
        "震荡": 0.05,
        "趋势": 0.1,
    }

    # 计算权重调整
    total_weight = 0
    positive_signals = 0
    negative_signals = 0
    neutral_signals = 0

    for indicator in technical_indicators:
        indicator_lower = indicator.lower()

        # 计算该指标的权重
        indicator_weight = 0
        for key, weight in indicator_weights.items():
            if key.lower() in indicator_lower:
                indicator_weight = max(indicator_weight, weight)

        total_weight += indicator_weight

        # 判断信号类型
        if any(
            keyword in indicator_lower
            for keyword in [
                "金叉",
                "多头",
                "突破",
                "上方",
                "增长",
                "增强",
                "向上",
                "积极",
            ]
        ):
            positive_signals += 1
        elif any(
            keyword in indicator_lower
            for keyword in [
                "死叉",
                "空头",
                "跌破",
                "下方",
                "缩短",
                "减弱",
                "向下",
                "谨慎",
                "超买",
                "超卖",
            ]
        ):
            negative_signals += 1
        else:
            neutral_signals += 1

    # 基于信号类型和权重计算调整
    if total_weight == 0:
        return base_score

    # 信号强度计算
    signal_ratio = (positive_signals - negative_signals) / max(
        1, len(technical_indicators)
    )

    # 权重调整（基于总权重和信号强度）
    # 限制调整幅度，确保不会超过99分
    max_adjustment = min(99 - base_score, 15)  # 最多调整15分，且不能超过99分
    weight_adjustment = total_weight * signal_ratio * 5  # 减少调整系数从10到5
    weight_adjustment = max(
        -max_adjustment, min(max_adjustment, weight_adjustment)
    )  # 限制调整范围

    # 应用调整
    adjusted_score = base_score + weight_adjustment

    logger.info(
        f"权重评分调整: 基础分={base_score:.1f}, 权重={total_weight:.2f}, 信号比例={signal_ratio:.2f}, 调整={weight_adjustment:.1f}, 最终分={adjusted_score:.1f}"
    )

    return adjusted_score


def _parse_openai_response(raw_content):
    """解析OpenAI兼容格式的响应"""
    try:
        parsed_json = json.loads(raw_content)

        # 确保解析结果是字典
        result_dict = None
        if isinstance(parsed_json, list) and parsed_json:
            result_dict = parsed_json[0]
        elif isinstance(parsed_json, dict):
            result_dict = parsed_json

        if result_dict and isinstance(result_dict, dict):
            signal = result_dict.get("signal", "持有")
            confidence = result_dict.get("confidence", 50)
            probability = result_dict.get("probability", "涨跌概率未知")
            support = result_dict.get("support", "未知")
            resistance = result_dict.get("resistance", "未知")
            target = result_dict.get("target", "未知")
            stop_loss = result_dict.get("stop_loss", "未知")
            comment = result_dict.get("comment", "OpenAI AI分析完成")
            return {
                "signal": str(signal),
                "confidence": int(confidence)
                if isinstance(confidence, (int, float))
                else 50,
                "probability": str(probability),
                "detailed_probability": result_dict.get("detailed_probability", {}),
                "pred_1d": result_dict.get("pred_1d", {}),
                "pred_3d": result_dict.get("pred_3d", {}),
                "support": str(support),
                "resistance": str(resistance),
                "target": str(target),
                "stop_loss": str(stop_loss),
                "comment": str(comment),
            }
        else:
            logger.error(f"OpenAI返回格式错误，不是预期的JSON字典: {raw_content}")
            return {
                "signal": "持有",
                "confidence": 50,
                "probability": "涨跌概率未知",
                "detailed_probability": {},
                "pred_1d": {},
                "pred_3d": {},
                "support": "未知",
                "resistance": "未知",
                "target": "未知",
                "stop_loss": "未知",
                "comment": "OpenAI返回格式错误或内容不符合预期。",
            }
    except json.JSONDecodeError as e:
        logger.error(f"OpenAI响应JSON解析失败: {e}, 内容: {raw_content}")
        return {
            "signal": "持有",
            "confidence": 50,
            "probability": "涨跌概率未知",
            "detailed_probability": {},
            "pred_1d": {},
            "pred_3d": {},
            "support": "未知",
            "resistance": "未知",
            "target": "未知",
            "stop_loss": "未知",
            "comment": "OpenAI响应JSON解析失败，无法解析为有效JSON。",
        }


def extract_signal_from_comment(comment):
    """从LLM点评中提取买卖信号（辅助函数）"""
    if not comment or not isinstance(comment, str):
        return "持有"

    # 按优先级检测信号
    if "强烈买入" in comment:
        return "强烈买入"
    elif "强烈卖出" in comment:
        return "强烈卖出"
    elif "买入" in comment:
        return "买入"
    elif "卖出" in comment:
        return "卖出"
    else:
        return "持有"


async def get_llm_score_with_signal(
    etf_data,
    daily_trend_data,
    forward_indicators_data=None,
    signal_data=None,
    alert_data=None,
    prediction_data=None,
):
    """调用大模型对单支ETF进行分析和打分（支持前瞻性指标和买卖信号）

    返回: (score, signal, comment)
    - score: 评分
    - signal: 买卖信号（强烈买入/买入/持有/卖出/强烈卖出）
    - comment: AI点评
    """
    # 调用原函数获取评分和点评
    score, comment = await get_llm_score_and_analysis(
        etf_data,
        daily_trend_data,
        forward_indicators_data,
        signal_data,
        alert_data,
        prediction_data,
    )

    # 如果有signal_data，使用其中的买卖信号
    if signal_data:
        signal_type = signal_data.get("signal_type", "Hold")
        signal_type_cn = {
            "Strong Buy": "强烈买入",
            "Buy": "买入",
            "Hold": "持有",
            "Sell": "卖出",
            "Strong Sell": "强烈卖出",
        }
        signal = signal_type_cn.get(signal_type, "持有")
    else:
        # 否则从点评中提取买卖信号
        signal = extract_signal_from_comment(comment)

    return score, signal, comment
