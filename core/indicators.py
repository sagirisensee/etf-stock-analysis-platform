import pandas as pd


def _get_trend_description(length):
    """获取均线趋势描述"""
    if length == 5:
        return "短期趋势"
    elif length == 10:
        return "短期趋势"
    elif length == 20:
        return "中期趋势"
    elif length == 60:
        return "中长期趋势"
    else:
        return "趋势"


def analyze_bollinger(result, latest, prev_latest, trend_signals):
    try:
        upper = latest.get("BBU_20_2.0")
        middle = latest.get("BBM_20_2.0")
        lower = latest.get("BBL_20_2.0")
        close = latest.get("close")  # Corrected: using 'close'

        # Ensure all necessary Bollinger Band values and close price are not NaN
        if pd.notna(upper) and pd.notna(middle) and pd.notna(lower) and pd.notna(close):
            if close > upper:
                trend_signals.append("收盘价突破布林上轨，短线超买，警惕回调。")
            elif close < lower:
                trend_signals.append("收盘价跌破布林下轨，短线超卖，关注反弹。")
            elif close > middle:
                trend_signals.append("收盘价位于布林中轨之上，趋势偏强。")
            elif close < middle:
                trend_signals.append("收盘价位于布林中轨之下，趋势偏弱。")

            # 震荡判别：检查最近几个交易日穿越布林中轨的次数
            # 修正：避免直接比较 Series 对象，而是检查每日穿越情况
            # 需要至少两个数据点来判断交叉
            if (
                len(result) >= 2
                and "close" in result.columns
                and "BBM_20_2.0" in result.columns
            ):
                cross_count = 0
                # 检查最近 N 天的穿越，例如最近 5 个交易日
                # 需要至少 6 个数据点才能检查到 5 次"前一天"和"当前天"
                # 更稳健的做法是获取最近的完整数据段
                num_days_to_check = min(
                    len(result), 5
                )  # Check up to the last 5 days available

                # Iterate from the second-to-last day back to check for crosses
                for i in range(1, num_days_to_check):
                    current_idx = -1 - (
                        num_days_to_check - 1 - i
                    )  # Current day index (from tail)
                    prev_idx = current_idx - 1  # Previous day index (from tail)

                    current_close = result["close"].iloc[current_idx]
                    current_middle = result["BBM_20_2.0"].iloc[current_idx]
                    prev_close = result["close"].iloc[prev_idx]
                    prev_middle = result["BBM_20_2.0"].iloc[prev_idx]

                    if (
                        pd.notna(current_close)
                        and pd.notna(current_middle)
                        and pd.notna(prev_close)
                        and pd.notna(prev_middle)
                    ):
                        # A cross occurs if the relationship (close > middle) changes from previous day to current day
                        # i.e., (prev_close <= prev_middle AND current_close > current_middle) OR
                        #       (prev_close >= prev_middle AND current_close < current_middle)
                        if (
                            prev_close <= prev_middle and current_close > current_middle
                        ) or (
                            prev_close >= prev_middle and current_close < current_middle
                        ):
                            cross_count += 1

                # If there are frequent crosses (e.g., 2 or more in 5 days), it indicates oscillation
                if (
                    cross_count >= 2
                ):  # Lowering threshold slightly as 5 days is a short window
                    trend_signals.append("近期收盘价频繁上下穿布林中轨，市场震荡明显。")
            else:
                trend_signals.append("布林通道震荡判别数据不足或列缺失。")
        else:
            trend_signals.append("布林通道数据不足或关键数据缺失，无法分析。")
    except Exception as e:
        trend_signals.append(f"布林通道分析异常：{e}，跳过分析。")


def judge_trend_status(latest, prev_latest):
    """
    综合均线、布林通道等，返回趋势状态字符串。
    """
    status = "🟡 震荡趋势"  # Default to neutral/sideways

    close = latest.get("close")  # Using 'close'
    if pd.isna(close):
        return "🟡 数据异常"

    sma_20 = latest.get("SMA_20")

    # Primary trend based on close vs SMA_20
    if pd.notna(sma_20):
        if close > sma_20:
            status = "🟢 上升趋势"
        else:
            status = "🔴 下降趋势"
    else:
        status = "🟡 均线数据不足"

    # Bollinger Bands for confirming oscillation
    middle_bb = latest.get("BBM_20_2.0")
    if pd.notna(middle_bb) and pd.notna(
        close
    ):  # Ensure close is also available for this check
        # If close price is very near the middle band, it suggests oscillation
        if abs(close - middle_bb) / middle_bb < 0.005:
            status = "🟡 震荡趋势"

    return status


def analyze_ma(result, latest, prev_latest, trend_signals):
    """
    均线（MA）信号分析
    """
    try:
        close = latest.get("close")  # Using 'close'
        if pd.isna(close):
            trend_signals.append("收盘价数据缺失，无法进行均线分析。")
            return

        # 股价与均线关系
        for length in [5, 10, 20, 60]:
            col = f"SMA_{length}"
            val = latest.get(col)
            if pd.notna(val):
                if close > val:
                    trend_signals.append(f"股价高于{length}日均线。")
                else:
                    trend_signals.append(f"股价低于{length}日均线。")
            else:
                trend_signals.append(f"{length}日均线数据缺失。")

        # 均线交叉（金叉/死叉）
        ma_pairs = [(5, 10), (10, 20), (20, 60)]
        for s_len, l_len in ma_pairs:
            s_col = f"SMA_{s_len}"
            l_col = f"SMA_{l_len}"

            # 检查当前和前一日均线值是否都可用
            current_s_val = latest.get(s_col)
            current_l_val = latest.get(l_col)
            prev_s_val = prev_latest.get(s_col)
            prev_l_val = prev_latest.get(l_col)

            # 如果当前值都存在，至少可以判断当前排列
            if pd.notna(current_s_val) and pd.notna(current_l_val):
                # 如果前一日值也存在，可以判断交叉
                if pd.notna(prev_s_val) and pd.notna(prev_l_val):
                    # Check for Golden Cross
                    if current_s_val > current_l_val and prev_s_val <= prev_l_val:
                        trend_signals.append(
                            f"{s_len}日均线金叉{l_len}日均线（看涨信号）。"
                        )
                    # Check for Death Cross
                    elif current_s_val < current_l_val and prev_s_val >= prev_l_val:
                        trend_signals.append(
                            f"{s_len}日均线死叉{l_len}日均线（看跌信号）。"
                        )
                    else:
                        # Current arrangement description if no cross
                        if current_s_val > current_l_val:
                            trend_signals.append(
                                f"{s_len}日均线在{l_len}日均线上方，多头排列延续。"
                            )
                        else:
                            trend_signals.append(
                                f"{s_len}日均线在{l_len}日均线下方，空头排列延续。"
                            )
                else:
                    # 只有当前值，只能判断当前排列
                    if current_s_val > current_l_val:
                        trend_signals.append(
                            f"{s_len}日均线在{l_len}日均线上方，多头排列。"
                        )
                    else:
                        trend_signals.append(
                            f"{s_len}日均线在{l_len}日均线下方，空头排列。"
                        )
            else:
                # 如果连当前值都没有，才报告数据缺失
                trend_signals.append(
                    f"{s_len}日与{l_len}日均线数据缺失，无法判断交叉。"
                )

        # 所有均线趋势判断
        for length in [5, 10, 20, 60]:
            col = f"SMA_{length}"
            sma_latest = latest.get(col)
            sma_prev = prev_latest.get(col)

            if pd.notna(sma_latest) and pd.notna(sma_prev):
                # 有前一日数据，直接比较
                if sma_latest > sma_prev:
                    trend_signals.append(
                        f"{length}日均线趋势向上（{_get_trend_description(length)}）。"
                    )
                elif sma_latest < sma_prev:
                    trend_signals.append(
                        f"{length}日均线趋势向下（{_get_trend_description(length)}）。"
                    )
                else:
                    trend_signals.append(
                        f"{length}日均线趋势持平（{_get_trend_description(length)}）。"
                    )
            elif pd.notna(sma_latest):
                # 只有当前值，尝试与更早的数据比较来判断趋势
                if len(result) >= 2:
                    # 对于60日均线，需要检查更长的历史数据
                    max_check_days = 20 if length == 60 else 10
                    check_range = min(len(result), max_check_days)

                    # 尝试获取前几天的均线值
                    for i in range(2, check_range):
                        prev_idx = -i
                        sma_earlier = result[col].iloc[prev_idx]
                        if pd.notna(sma_earlier):
                            if sma_latest > sma_earlier:
                                trend_signals.append(
                                    f"{length}日均线趋势向上（{_get_trend_description(length)}）。"
                                )
                            elif sma_latest < sma_earlier:
                                trend_signals.append(
                                    f"{length}日均线趋势向下（{_get_trend_description(length)}）。"
                                )
                            else:
                                trend_signals.append(
                                    f"{length}日均线趋势持平（{_get_trend_description(length)}）。"
                                )
                            break
                    else:
                        # 如果找不到可比较的历史数据，提供更详细的信息
                        if length == 60:
                            # 对于60日均线，检查有多少个非NaN值
                            non_nan_count = result[col].notna().sum()
                            if non_nan_count == 1:
                                trend_signals.append(
                                    "60日均线当前值可用，但数据长度刚好60天，需要更多历史数据才能判断趋势变化。"
                                )
                            else:
                                trend_signals.append(
                                    f"60日均线当前值可用，但历史数据不足无法判断趋势变化（共{non_nan_count}个有效值）。"
                                )
                        else:
                            trend_signals.append(
                                f"{length}日均线当前值可用，但历史数据不足无法判断趋势变化。"
                            )
                else:
                    trend_signals.append(
                        f"{length}日均线当前值可用，但历史数据不足无法判断趋势变化。"
                    )
            else:
                trend_signals.append(f"{length}日均线数据缺失，无法判断趋势。")
    except Exception as e:
        trend_signals.append(f"均线分析异常：{e}，跳过分析。")


def analyze_macd(result, latest, prev_latest, trend_signals):
    """
    MACD信号分析
    """
    try:
        macd_line_col = "MACD_12_26_9"
        signal_line_col = "MACDs_12_26_9"
        histogram_col = "MACDh_12_26_9"

        l_macd = latest.get(macd_line_col)
        l_signal = latest.get(signal_line_col)
        l_hist = latest.get(histogram_col)
        p_macd = prev_latest.get(macd_line_col)
        p_signal = prev_latest.get(signal_line_col)
        p_hist = prev_latest.get(histogram_col)

        # Check if all necessary MACD values are not NaN before proceeding
        if all(
            pd.notna(x) for x in [l_macd, l_signal, l_hist, p_macd, p_signal, p_hist]
        ):
            # 金叉/死叉
            if l_macd > l_signal and p_macd <= p_signal:
                trend_signals.append("MACD金叉（看涨信号）。")
            elif l_macd < l_signal and p_macd >= p_signal:
                trend_signals.append("MACD死叉（看跌信号）。")
            else:
                if l_macd > l_signal:
                    trend_signals.append("MACD线在信号线上方，多头延续。")
                else:
                    trend_signals.append("MACD线在信号线下方，空头延续。")

            # 零轴
            if l_macd > 0:
                trend_signals.append("MACD线在零轴上方，市场偏强。")
            elif l_macd < 0:
                trend_signals.append("MACD线在零轴下方，市场偏弱。")
            else:
                trend_signals.append("MACD线在零轴附近，市场中性。")

            # 柱线变化
            if l_hist > 0:  # Red bars (positive histogram)
                if l_hist > p_hist:
                    trend_signals.append("MACD红柱增长，多头力量增强。")
                elif l_hist < p_hist:
                    trend_signals.append("MACD红柱缩短，多头力量减弱。")
                else:
                    trend_signals.append("MACD红柱持平，多头力量维持。")
            elif l_hist < 0:  # Green bars (negative histogram)
                if l_hist < p_hist:  # Histogram becomes more negative
                    trend_signals.append("MACD绿柱增长，空头力量增强。")
                elif (
                    l_hist > p_hist
                ):  # Histogram becomes less negative (moves towards zero)
                    trend_signals.append("MACD绿柱缩短，空头力量减弱。")
                else:
                    trend_signals.append("MACD绿柱持平，空头力量维持。")
            else:  # Histogram is zero
                trend_signals.append("MACD柱线在零轴，多空平衡。")
        else:
            trend_signals.append("MACD指标数据缺失或不完整，无法分析。")
    except Exception as e:
        trend_signals.append(f"MACD分析异常：{e}，跳过分析。")


def calculate_forward_indicators(df):
    """
    计算所有前瞻性技术指标
    """
    try:
        # 计算RSI（14日相对强弱指标）
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["RSI_14"] = 100 - (100 / (1 + rs))

        # 计算KDJ指标
        low_min = df["close"].rolling(window=9).min()
        high_max = df["close"].rolling(window=9).max()
        rsv = (df["close"] - low_min) / (high_max - low_min) * 100
        df["KDJ_K"] = rsv.ewm(com=2, adjust=False).mean()
        df["KDJ_D"] = df["KDJ_K"].ewm(com=2, adjust=False).mean()
        df["KDJ_J"] = 3 * df["KDJ_K"] - 2 * df["KDJ_D"]

        # 计算CCI（14日顺势指标）
        tp = (
            df["close"] + df.get("high", df["close"]) + df.get("low", df["close"])
        ) / 3
        ma_tp = tp.rolling(window=14).mean()
        mad = tp.rolling(window=14).apply(lambda x: abs(x - x.mean()).mean())
        df["CCI_14"] = (tp - ma_tp) / (0.015 * mad)

        # 计算OBV（能量潮）- 需要成交量数据
        if "volume" in df.columns or "成交量" in df.columns:
            vol_col = "volume" if "volume" in df.columns else "成交量"
            df["OBV"] = (
                df["close"].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
                * df[vol_col]
            ).cumsum()
        else:
            df["OBV"] = None

        # 计算威廉指标 - 使用东方财富格式（0-100）
        # WR1: 10日周期
        high_max_10 = df.get("high", df["close"]).rolling(window=10).max()
        low_min_10 = df.get("low", df["close"]).rolling(window=10).min()
        df["WR1"] = (
            (high_max_10 - df.get("close", df["close"])) / (high_max_10 - low_min_10)
        ) * 100

        # WR2: 6日周期
        high_max_6 = df.get("high", df["close"]).rolling(window=6).max()
        low_min_6 = df.get("low", df["close"]).rolling(window=6).min()
        df["WR2"] = (
            (high_max_6 - df.get("close", df["close"])) / (high_max_6 - low_min_6)
        ) * 100

        return df
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"计算前瞻性指标失败: {e}")
        return df


def analyze_rsi(result, latest, prev_latest, trend_signals):
    """
    RSI（相对强弱指标）分析 - 领先指标，提前识别超买超卖
    """
    try:
        rsi_14 = latest.get("RSI_14")
        prev_rsi = prev_latest.get("RSI_14")

        if pd.notna(rsi_14):
            # RSI超买超卖判断
            if rsi_14 > 80:
                trend_signals.append(
                    f"RSI({rsi_14:.1f})严重超买，警惕大幅回调风险（前瞻性预警）。"
                )
            elif rsi_14 > 70:
                trend_signals.append(
                    f"RSI({rsi_14:.1f})进入超买区域，短期可能回调（前瞻性预警）。"
                )
            elif rsi_14 < 20:
                trend_signals.append(
                    f"RSI({rsi_14:.1f})严重超卖，关注反弹机会（前瞻性预警）。"
                )
            elif rsi_14 < 30:
                trend_signals.append(
                    f"RSI({rsi_14:.1f})进入超卖区域，短期可能反弹（前瞻性预警）。"
                )
            elif rsi_14 > 50:
                trend_signals.append(f"RSI({rsi_14:.1f})在50上方，多头力量占优。")
            else:
                trend_signals.append(f"RSI({rsi_14:.1f})在50下方，空头力量占优。")

            # RSI背离判断（价格新高但RSI未创新高）
            if pd.notna(prev_rsi) and len(result) >= 5:
                recent_close = result["close"].iloc[-5:].tolist()
                recent_rsi = result["RSI_14"].iloc[-5:].tolist()

                # 顶背离判断：价格新高但RSI未创新高
                if recent_close[-1] > max(recent_close[:-1]) and recent_rsi[-1] < max(
                    recent_rsi[:-1]
                ):
                    trend_signals.append(
                        "⚠️ 顶背离信号：价格创新高但RSI未创新高，警惕趋势反转（前瞻性预警）。"
                    )

                # 底背离判断：价格新低但RSI未创新低
                if recent_close[-1] < min(recent_close[:-1]) and recent_rsi[-1] > min(
                    recent_rsi[:-1]
                ):
                    trend_signals.append(
                        "⚠️ 底背离信号：价格创新低但RSI未创新低，关注反弹机会（前瞻性预警）。"
                    )
        else:
            trend_signals.append("RSI指标数据缺失，无法分析。")
    except Exception as e:
        trend_signals.append(f"RSI分析异常：{e}，跳过分析。")


def analyze_kdj(result, latest, prev_latest, trend_signals):
    """
    KDJ指标分析 - 比MACD更灵敏的短期趋势指标
    """
    try:
        k_val = latest.get("KDJ_K")
        d_val = latest.get("KDJ_D")
        j_val = latest.get("KDJ_J")
        prev_k = prev_latest.get("KDJ_K")
        prev_d = prev_latest.get("KDJ_D")

        if pd.notna(k_val) and pd.notna(d_val) and pd.notna(j_val):
            # KDJ位置判断
            if j_val > 100:
                trend_signals.append(
                    f"KDJ(J={j_val:.1f})超买，警惕短期回调（前瞻性预警）。"
                )
            elif j_val < 0:
                trend_signals.append(
                    f"KDJ(J={j_val:.1f})超卖，关注短期反弹（前瞻性预警）。"
                )
            elif k_val > 80:
                trend_signals.append(f"KDJ(K={k_val:.1f})进入超买区域，短期可能回调。")
            elif k_val < 20:
                trend_signals.append(f"KDJ(K={k_val:.1f})进入超卖区域，短期可能反弹。")

            # KDJ金叉/死叉
            if pd.notna(prev_k) and pd.notna(prev_d):
                if k_val > d_val and prev_k <= prev_d:
                    trend_signals.append(
                        f"KDJ金叉（K={k_val:.1f}, D={d_val:.1f}），买入信号（前瞻性预警）。"
                    )
                    if j_val > 0 and (prev_latest.get("KDJ_J") or 0) <= 0:
                        trend_signals.append(
                            "KDJ的J线从负值转正，多头力量增强（前瞻性预警）。"
                        )
                elif k_val < d_val and prev_k >= prev_d:
                    trend_signals.append(
                        f"KDJ死叉（K={k_val:.1f}, D={d_val:.1f}），卖出信号（前瞻性预警）。"
                    )
                    if j_val < 0 and (prev_latest.get("KDJ_J") or 0) >= 0:
                        trend_signals.append(
                            "KDJ的J线从正值转负，空头力量增强（前瞻性预警）。"
                        )
            else:
                if k_val > d_val:
                    trend_signals.append(
                        f"KDJ多头排列（K={k_val:.1f}, D={d_val:.1f}）。"
                    )
                else:
                    trend_signals.append(
                        f"KDJ空头排列（K={k_val:.1f}, D={d_val:.1f}）。"
                    )

            # J线趋势
            if j_val > 50:
                trend_signals.append(f"KDJ(J={j_val:.1f})强势，多头活跃。")
            elif j_val < -50:
                trend_signals.append(f"KDJ(J={j_val:.1f})弱势，空头活跃。")
        else:
            trend_signals.append("KDJ指标数据缺失，无法分析。")
    except Exception as e:
        trend_signals.append(f"KDJ分析异常：{e}，跳过分析。")


def analyze_cci(result, latest, prev_latest, trend_signals):
    """
    CCI（顺势指标）分析 - 识别趋势转折和异常波动
    """
    try:
        cci_14 = latest.get("CCI_14")
        prev_cci = prev_latest.get("CCI_14")

        if pd.notna(cci_14):
            # CCI极端值判断
            if cci_14 > 200:
                trend_signals.append(
                    f"CCI({cci_14:.1f})极端超买，警惕剧烈回调（前瞻性预警）。"
                )
            elif cci_14 > 100:
                trend_signals.append(
                    f"CCI({cci_14:.1f})进入超买区域，趋势过热（前瞻性预警）。"
                )
            elif cci_14 < -200:
                trend_signals.append(
                    f"CCI({cci_14:.1f})极端超卖，关注反弹机会（前瞻性预警）。"
                )
            elif cci_14 < -100:
                trend_signals.append(
                    f"CCI({cci_14:.1f})进入超卖区域，趋势过冷（前瞻性预警）。"
                )
            elif cci_14 > 0:
                trend_signals.append(f"CCI({cci_14:.1f})在零轴上方，多头市场。")
            else:
                trend_signals.append(f"CCI({cci_14:.1f})在零轴下方，空头市场。")

            # CCI穿越+100/-100判断
            if pd.notna(prev_cci):
                if cci_14 > 100 and prev_cci <= 100:
                    trend_signals.append("CCI突破+100，进入强势区域（前瞻性预警）。")
                elif cci_14 < -100 and prev_cci >= -100:
                    trend_signals.append("CCI跌破-100，进入弱势区域（前瞻性预警）。")
                elif cci_14 < 100 and prev_cci >= 100:
                    trend_signals.append("CCI回落至+100下方，强势减弱（前瞻性预警）。")
                elif cci_14 > -100 and prev_cci <= -100:
                    trend_signals.append("CCI回升至-100上方，弱势减弱（前瞻性预警）。")
        else:
            trend_signals.append("CCI指标数据缺失，无法分析。")
    except Exception as e:
        trend_signals.append(f"CCI分析异常：{e}，跳过分析。")


def analyze_obv(result, latest, prev_latest, trend_signals):
    """
    OBV（能量潮）分析 - 资金流向指标（替代直接资金数据）
    """
    try:
        obv = latest.get("OBV")
        prev_obv = prev_latest.get("OBV")

        if pd.notna(obv):
            # OBV趋势判断
            if pd.notna(prev_obv):
                if obv > prev_obv:
                    trend_signals.append(f"OBV上升，资金流入（价格可能滞后反映）。")
                elif obv < prev_obv:
                    trend_signals.append(f"OBV下降，资金流出（价格可能滞后反映）。")
                else:
                    trend_signals.append("OBV持平，资金流向平衡。")

            # OBV与价格背离判断
            if pd.notna(prev_obv) and len(result) >= 5:
                recent_close = result["close"].iloc[-5:].tolist()
                recent_obv = result["OBV"].iloc[-5:].tolist()

                # 顶背离：价格新高但OBV未创新高
                if recent_close[-1] > max(recent_close[:-1]) and recent_obv[-1] < max(
                    recent_obv[:-1]
                ):
                    trend_signals.append(
                        "⚠️ OBV顶背离：价格创新高但资金未同步流入，警惕下跌（前瞻性预警）。"
                    )

                # 底背离：价格新低但OBV未创新低
                if recent_close[-1] < min(recent_close[:-1]) and recent_obv[-1] > min(
                    recent_obv[:-1]
                ):
                    trend_signals.append(
                        "⚠️ OBV底背离：价格创新低但资金未同步流出，关注反弹（前瞻性预警）。"
                    )
        else:
            trend_signals.append("OBV指标数据缺失（需要成交量数据），无法分析。")
    except Exception as e:
        trend_signals.append(f"OBV分析异常：{e}，跳过分析。")



def analyze_williams(result, latest, prev_latest, trend_signals):
    """
    威廉指标（WR）分析 - 超买超卖领先指标
    东方财富格式：WR1(10日)、WR2(6日)，取值范围0-100
    """
    try:
        wr1 = latest.get("WR1")  # 10日威廉指标
        wr1_prev = prev_latest.get("WR1")
        wr2 = latest.get("WR2")  # 6日威廉指标
        wr2_prev = prev_latest.get("WR2")

        if pd.notna(wr1) and pd.notna(wr2):
            # 超买超卖判断（高于80超卖，低于20超买）
            if wr1 > 80 or wr2 > 80:
                trend_signals.append(
                    f"WR指标({wr1:.1f}/{wr2:.1f})进入超卖区间，关注反弹机会。"
                )
            elif wr1 < 20 or wr2 < 20:
                trend_signals.append(
                    f"WR指标({wr1:.1f}/{wr2:.1f})进入超买区间，警惕回调风险。"
                )

            # 趋势强弱分析（以50为中轴线）
            if wr1 > 50 and wr2 > 50:
                trend_signals.append(
                    "WR指标双线均高于50，处于强势回升区间。"
                )
            elif wr1 < 50 and wr2 < 50:
                trend_signals.append(
                    "WR指标双线均低于50，处于弱势调整区间。"
                )

            # WR2穿越50判断（短线信号）
            if pd.notna(wr2_prev):
                if wr2 > 50 and wr2_prev <= 50:
                    trend_signals.append(
                        "WR2突破50，进入弱势区域，短线走弱。"
                    )
                elif wr2 < 50 and wr2_prev >= 50:
                    trend_signals.append(
                        "WR2跌破50，进入强势区域，短线走强。"
                    )

            # 买卖信号
            if pd.notna(wr1_prev) and pd.notna(wr2_prev):
                # WR1反复在80上方震荡后跌破80（底部反转）
                if wr1 < 80 and wr1_prev > 80:
                    trend_signals.append(
                        "WR1从超卖区间跌破80，可能形成底部反弹信号。"
                    )
                # WR2反复在20下方震荡后突破20（顶部反转）
                if wr2 > 20 and wr2_prev < 20:
                    trend_signals.append(
                        "WR2从超买区间突破20，可能形成顶部回落信号。"
                    )
        else:
            trend_signals.append("WR指标数据缺失，无法分析。")

    except Exception as e:
        trend_signals.append(f"威廉指标分析异常：{e}，跳过分析。")


def calculate_minute_indicators(minute_df, period="60"):
    """
    计算分钟线技术指标

    参数:
        minute_df: 分钟线DataFrame
        period: 分钟周期（"60"/"30"/"15"/"5"/"1"）

    返回:
        DataFrame: 包含技术指标的分钟线数据
    """
    if minute_df is None or minute_df.empty:
        return minute_df

    if "close" not in minute_df.columns:
        return minute_df

    try:
        # 短期均线（基于分钟线）
        minute_df["SMA_5"] = minute_df["close"].rolling(window=5).mean()
        minute_df["SMA_10"] = minute_df["close"].rolling(window=10).mean()
        minute_df["SMA_20"] = minute_df["close"].rolling(window=20).mean()

        # 短期MACD（快速参数）
        exp1 = minute_df["close"].ewm(span=5).mean()
        exp2 = minute_df["close"].ewm(span=10).mean()
        minute_df["MACD_5_10_5"] = exp1 - exp2
        minute_df["MACDs_5_10_5"] = minute_df["MACD_5_10_5"].ewm(span=5).mean()
        minute_df["MACDh_5_10_5"] = minute_df["MACD_5_10_5"] - minute_df["MACDs_5_10_5"]

        # 短期布林带（10周期）
        minute_df["BBM_10_2.0"] = minute_df["close"].rolling(window=10).mean()
        std_10 = minute_df["close"].rolling(window=10).std()
        minute_df["BBU_10_2.0"] = minute_df["BBM_10_2.0"] + (std_10 * 2)
        minute_df["BBL_10_2.0"] = minute_df["BBM_10_2.0"] - (std_10 * 2)

        # RSI（14周期）
        delta = minute_df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        minute_df["RSI_14"] = 100 - (100 / (1 + rs))

        # KDJ指标 (9, 3, 3)
        if "high" in minute_df.columns and "low" in minute_df.columns:
            low_9 = minute_df["low"].rolling(window=9).min()
            high_9 = minute_df["high"].rolling(window=9).max()
            rsv = (minute_df["close"] - low_9) / (high_9 - low_9) * 100

            minute_df["KDJ_K"] = rsv.ewm(com=2).mean()
            minute_df["KDJ_D"] = minute_df["KDJ_K"].ewm(com=2).mean()
            minute_df["KDJ_J"] = 3 * minute_df["KDJ_K"] - 2 * minute_df["KDJ_D"]

        # CCI（14周期）
        if "high" in minute_df.columns and "low" in minute_df.columns:
            tp = (minute_df["high"] + minute_df["low"] + minute_df["close"]) / 3
            ma_tp = tp.rolling(window=14).mean()
            mad = tp.rolling(window=14).apply(
                lambda x: (pd.Series(x) - pd.Series(x).mean()).abs().mean()
            )
            minute_df["CCI_14"] = (tp - ma_tp) / (0.015 * mad)

        # ATR（真实波动范围，14周期）
        if "high" in minute_df.columns and "low" in minute_df.columns:
            prev_close = minute_df["close"].shift(1)
            tr1 = minute_df["high"] - minute_df["low"]
            tr2 = (minute_df["high"] - prev_close).abs()
            tr3 = (minute_df["low"] - prev_close).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            minute_df["ATR_14"] = tr.rolling(window=14).mean()

        # 标注周期类型
        minute_df["period_type"] = period

        return minute_df

    except Exception as e:
        print(f"计算分钟线指标异常: {e}")
        return minute_df


def calculate_minute_support_resistance(minute_30_df, minute_60_df, current_price):
    """
    基于分钟线计算支撑阻力位

    参数:
        minute_30_df: 30分钟线DataFrame
        minute_60_df: 60分钟线DataFrame
        current_price: 当前价格

    返回:
        dict: {
            'support_30': [...],  # 30分钟支撑位
            'resistance_30': [...],  # 30分钟阻力位
            'support_60': [...],  # 60分钟支撑位
            'resistance_60': [...],  # 60分钟阻力位
            'atr_30': ...,  # 30分钟ATR
            'atr_60': ...,  # 60分钟ATR
        }
    """
    result = {
        "support_30": [],
        "resistance_30": [],
        "support_60": [],
        "resistance_60": [],
        "atr_30": None,
        "atr_60": None,
    }

    # 计算30分钟线支撑阻力
    if minute_30_df is not None and not minute_30_df.empty and len(minute_30_df) >= 20:
        try:
            # 获取最近20个数据点
            recent_30 = minute_30_df.iloc[-20:]

            # 高点和低点
            high_30 = recent_30["high"].max()
            low_30 = recent_30["low"].min()

            # 布林带支撑阻力
            bb_upper_30 = recent_30.iloc[-1].get("BBU_10_2.0")
            bb_lower_30 = recent_30.iloc[-1].get("BBL_10_2.0")

            # ATR
            atr_30 = None
            if "ATR_14" in recent_30.columns:
                atr_30 = recent_30["ATR_14"].iloc[-1]
                result["atr_30"] = atr_30

            # 支撑位
            support_levels_30 = []
            support_levels_30.append(low_30)  # 近期低点
            if pd.notna(bb_lower_30) and bb_lower_30 < current_price:
                support_levels_30.append(bb_lower_30)
            if pd.notna(atr_30):
                support_levels_30.append(current_price - atr_30 * 1.5)
                support_levels_30.append(current_price - atr_30 * 3)

            # 去重并排序
            support_levels_30 = sorted(
                list(set([round(v, 2) for v in support_levels_30 if v > 0]))
            )
            result["support_30"] = [v for v in support_levels_30 if v < current_price]

            # 阻力位
            resistance_levels_30 = []
            resistance_levels_30.append(high_30)  # 近期高点
            if pd.notna(bb_upper_30) and bb_upper_30 > current_price:
                resistance_levels_30.append(bb_upper_30)
            if pd.notna(atr_30):
                resistance_levels_30.append(current_price + atr_30 * 1.5)
                resistance_levels_30.append(current_price + atr_30 * 3)

            # 去重并排序
            resistance_levels_30 = sorted(
                list(set([round(v, 2) for v in resistance_levels_30 if v > 0]))
            )
            result["resistance_30"] = [
                v for v in resistance_levels_30 if v > current_price
            ]

        except Exception as e:
            print(f"计算30分钟支撑阻力异常: {e}")

    # 计算60分钟线支撑阻力
    if minute_60_df is not None and not minute_60_df.empty and len(minute_60_df) >= 20:
        try:
            # 获取最近20个数据点
            recent_60 = minute_60_df.iloc[-20:]

            # 高点和低点
            high_60 = recent_60["high"].max()
            low_60 = recent_60["low"].min()

            # 布林带支撑阻力
            bb_upper_60 = recent_60.iloc[-1].get("BBU_10_2.0")
            bb_lower_60 = recent_60.iloc[-1].get("BBL_10_2.0")

            # ATR
            atr_60 = None
            if "ATR_14" in recent_60.columns:
                atr_60 = recent_60["ATR_14"].iloc[-1]
                result["atr_60"] = atr_60

            # 支撑位
            support_levels_60 = []
            support_levels_60.append(low_60)  # 近期低点
            if pd.notna(bb_lower_60) and bb_lower_60 < current_price:
                support_levels_60.append(bb_lower_60)
            if pd.notna(atr_60):
                support_levels_60.append(current_price - atr_60 * 1.5)
                support_levels_60.append(current_price - atr_60 * 3)

            # 去重并排序
            support_levels_60 = sorted(
                list(set([round(v, 2) for v in support_levels_60 if v > 0]))
            )
            result["support_60"] = [v for v in support_levels_60 if v < current_price]

            # 阻力位
            resistance_levels_60 = []
            resistance_levels_60.append(high_60)  # 近期高点
            if pd.notna(bb_upper_60) and bb_upper_60 > current_price:
                resistance_levels_60.append(bb_upper_60)
            if pd.notna(atr_60):
                resistance_levels_60.append(current_price + atr_60 * 1.5)
                resistance_levels_60.append(current_price + atr_60 * 3)

            # 去重并排序
            resistance_levels_60 = sorted(
                list(set([round(v, 2) for v in resistance_levels_60 if v > 0]))
            )
            result["resistance_60"] = [
                v for v in resistance_levels_60 if v > current_price
            ]

        except Exception as e:
            print(f"计算60分钟支撑阻力异常: {e}")

    return result


def calculate_entry_signals(
    minute_30_df, minute_60_df, support_resistance, current_price
):
    """
    计算推荐入场价位

    参数:
        minute_30_df: 30分钟线DataFrame
        minute_60_df: 60分钟线DataFrame
        support_resistance: 支撑阻力位数据
        current_price: 当前价格

    返回:
        dict: {
            'entry_price_buy': ...,  # 买入推荐价位
            'entry_price_sell': ...,  # 卖出推荐价位
            'entry_confidence': ...,  # 入场信心度
            'entry_reason': ...,  # 入场理由
        }
    """
    result = {
        "entry_price_buy": None,
        "entry_price_sell": None,
        "entry_confidence": "low",
        "entry_reason": "",
    }

    try:
        # 分析30分钟线指标
        rsi_30 = None
        kdj_k_30 = None
        macd_30 = None

        if (
            minute_30_df is not None
            and not minute_30_df.empty
            and len(minute_30_df) >= 2
        ):
            latest_30 = minute_30_df.iloc[-1]
            rsi_30 = latest_30.get("RSI_14")
            kdj_k_30 = latest_30.get("KDJ_K")
            macd_30 = latest_30.get("MACD_5_10_5")

        # 分析60分钟线指标
        rsi_60 = None
        kdj_k_60 = None
        macd_60 = None

        if (
            minute_60_df is not None
            and not minute_60_df.empty
            and len(minute_60_df) >= 2
        ):
            latest_60 = minute_60_df.iloc[-1]
            rsi_60 = latest_60.get("RSI_14")
            kdj_k_60 = latest_60.get("KDJ_K")
            macd_60 = latest_60.get("MACD_5_10_5")

        # 判断买入信号
        buy_signals = []
        entry_price_buy = None
        buy_confidence = 0

        # 30分钟线买入信号
        if rsi_30 is not None:
            if rsi_30 < 30:
                buy_signals.append(f"30分钟RSI超卖({rsi_30:.1f})")
                buy_confidence += 3
            elif rsi_30 < 40:
                buy_signals.append(f"30分钟RSI偏低({rsi_30:.1f})")
                buy_confidence += 1

        if kdj_k_30 is not None:
            if kdj_k_30 < 20:
                buy_signals.append(f"30分钟KDJ超卖({kdj_k_30:.1f})")
                buy_confidence += 2
            elif kdj_k_30 < 30:
                buy_signals.append(f"30分钟KDJ偏低({kdj_k_30:.1f})")
                buy_confidence += 1

        # 60分钟线买入信号
        if rsi_60 is not None:
            if rsi_60 < 30:
                buy_signals.append(f"60分钟RSI超卖({rsi_60:.1f})")
                buy_confidence += 2
            elif rsi_60 < 40:
                buy_signals.append(f"60分钟RSI偏低({rsi_60:.1f})")
                buy_confidence += 1

        if kdj_k_60 is not None:
            if kdj_k_60 < 20:
                buy_signals.append(f"60分钟KDJ超卖({kdj_k_60:.1f})")
                buy_confidence += 1

        # 基于支撑位计算买入价
        support_levels = []
        if support_resistance.get("support_30"):
            support_levels.extend(support_resistance["support_30"])
        if support_resistance.get("support_60"):
            support_levels.extend(support_resistance["support_60"])

        if support_levels:
            # 选择最接近当前价格的支撑位
            valid_supports = [s for s in support_levels if s < current_price]
            if valid_supports:
                entry_price_buy = max(valid_supports)
                buy_signals.append(f"接近30/60分钟支撑位({entry_price_buy:.2f})")
                buy_confidence += 2

        # 判断卖出信号
        sell_signals = []
        entry_price_sell = None
        sell_confidence = 0

        # 30分钟线卖出信号
        if rsi_30 is not None:
            if rsi_30 > 70:
                sell_signals.append(f"30分钟RSI超买({rsi_30:.1f})")
                sell_confidence += 3
            elif rsi_30 > 60:
                sell_signals.append(f"30分钟RSI偏高({rsi_30:.1f})")
                sell_confidence += 1

        if kdj_k_30 is not None:
            if kdj_k_30 > 80:
                sell_signals.append(f"30分钟KDJ超买({kdj_k_30:.1f})")
                sell_confidence += 2
            elif kdj_k_30 > 70:
                sell_signals.append(f"30分钟KDJ偏高({kdj_k_30:.1f})")
                sell_confidence += 1

        # 60分钟线卖出信号
        if rsi_60 is not None:
            if rsi_60 > 70:
                sell_signals.append(f"60分钟RSI超买({rsi_60:.1f})")
                sell_confidence += 2
            elif rsi_60 > 60:
                sell_signals.append(f"60分钟RSI偏高({rsi_60:.1f})")
                sell_confidence += 1

        if kdj_k_60 is not None:
            if kdj_k_60 > 80:
                sell_signals.append(f"60分钟KDJ超买({kdj_k_60:.1f})")
                sell_confidence += 1

        # 基于阻力位计算卖出价
        resistance_levels = []
        if support_resistance.get("resistance_30"):
            resistance_levels.extend(support_resistance["resistance_30"])
        if support_resistance.get("resistance_60"):
            resistance_levels.extend(support_resistance["resistance_60"])

        if resistance_levels:
            # 选择最接近当前价格的阻力位
            valid_resistances = [r for r in resistance_levels if r > current_price]
            if valid_resistances:
                entry_price_sell = min(valid_resistances)
                sell_signals.append(f"接近30/60分钟阻力位({entry_price_sell:.2f})")
                sell_confidence += 2

        # 确定总体信心度
        max_confidence = max(buy_confidence, sell_confidence)
        if max_confidence >= 5:
            result["entry_confidence"] = "high"
        elif max_confidence >= 3:
            result["entry_confidence"] = "medium"
        else:
            result["entry_confidence"] = "low"

        # 设置推荐价位和理由
        if buy_confidence >= sell_confidence and buy_signals:
            result["entry_price_buy"] = entry_price_buy
            result["entry_reason"] = f"买入信号：{'; '.join(buy_signals)}"
        elif sell_signals:
            result["entry_price_sell"] = entry_price_sell
            result["entry_reason"] = f"卖出信号：{'; '.join(sell_signals)}"
        else:
            result["entry_reason"] = "暂无明显入场信号，建议观望"

    except Exception as e:
        print(f"计算入场信号异常: {e}")
        result["entry_reason"] = f"计算异常: {str(e)}"

    return result
