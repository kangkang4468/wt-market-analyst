import os
import json
import glob
from datetime import datetime
import sys
import re

# 尝试在 Windows 下启用 UTF-8 输出，防止控制台中文乱码
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ==========================================
# 核心数据分析算法 (纯 Python 标准库实现)
# ==========================================

def calculate_linear_regression(history):
    """
    计算价格历史数据的线性回归斜率和均价
    history: [[timestamp_ms, price_f], ...]
    返回: (daily_slope, avg_price)
    """
    if not history or len(history) < 2:
        return 0.0, 0.0
    
    # 按照时间戳升序排序
    sorted_history = sorted(history, key=lambda x: x[0])
    
    # 将时间戳转换为相对于首个数据点的天数，避免时间戳过大导致溢出
    t0 = sorted_history[0][0]
    x = []
    y = []
    
    for pt in sorted_history:
        # 毫秒转换为天数
        t_days = (pt[0] - t0) / (1000.0 * 60 * 60 * 24)
        x.append(t_days)
        y.append(pt[1])
        
    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xx = sum(xi * xi for xi in x)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    
    denom = (n * sum_xx - sum_x * sum_x)
    if denom == 0:
        return 0.0, sum_y / n
        
    slope = (n * sum_xy - sum_x * sum_y) / denom
    avg_price = sum_y / n
    return slope, avg_price

def calculate_recent_ma(history, days=7):
    """
    计算最近几天的移动平均线
    """
    if not history:
        return None
    sorted_history = sorted(history, key=lambda x: x[0], reverse=True)
    t_latest = sorted_history[0][0]
    
    # 过滤出最近 days 天的数据点
    cutoff = t_latest - (days * 24 * 60 * 60 * 1000)
    recent_pts = [pt[1] for pt in sorted_history if pt[0] >= cutoff]
    return sum(recent_pts) / len(recent_pts) if recent_pts else None

def detect_last_crash(history):
    """
    分析历史价格数据，寻找最近一次在 30 天内价格大跌超 30% 的事件
    history: [[timestamp_ms, price_f], ...]
    返回: (crash_date, crash_drop_pct)
    """
    if not history or len(history) < 2:
        return "暂无大跌记录", 0.0
        
    # 按照时间戳升序排序
    sorted_history = sorted(history, key=lambda x: x[0])
    
    max_drops = [] # [(valley_time, drop_pct), ...]
    window_ms = 30 * 24 * 60 * 60 * 1000 # 30天
    
    for i in range(len(sorted_history)):
        t_i, p_i = sorted_history[i]
        if p_i <= 0:
            continue
            
        # 寻找 i 之后 30 天内的最低价格点
        min_p = p_i
        min_t = t_i
        for j in range(i + 1, len(sorted_history)):
            t_j, p_j = sorted_history[j]
            if t_j - t_i > window_ms:
                break
            if p_j < min_p:
                min_p = p_j
                min_t = t_j
                
        drop = (p_i - min_p) / p_i
        if drop >= 0.30: # 跌幅超 30%
            max_drops.append((min_t, drop))
            
    if not max_drops:
        return "未检测到大跌", 0.0
        
    # 找到最近的一个大跌低谷（时间戳最大）
    max_drops.sort(key=lambda x: x[0], reverse=True)
    latest_valley_time, latest_drop = max_drops[0]
    
    try:
        crash_date = datetime.fromtimestamp(latest_valley_time / 1000.0).strftime('%Y-%m-%d')
    except Exception:
        crash_date = "格式错误"
        
    return crash_date, latest_drop * 100.0

def predict_future_valleys(base_date, n=2):
    """
    基于 base_date (datetime对象) 预测未来 n 个官方大促低谷日期
    四大周期（中值）：胜利日(5-8)、夏活(8-20)、周年庆(11-1)、冬活(12-28)
    """
    year = base_date.year
    
    events = [
        ("春季胜利日大促", datetime(year, 5, 8)),
        ("夏季马拉松活动", datetime(year, 8, 20)),
        ("周年庆狂欢大促", datetime(year, 11, 1)),
        ("冬季圣诞特惠活动", datetime(year, 12, 28))
    ]
    
    future_events = []
    # 考虑今年和明年的活动
    for y in [year, year + 1]:
        for name, date_val in events:
            evt_date = datetime(y, date_val.month, date_val.day)
            if evt_date >= base_date:
                future_events.append((name, evt_date))
                
    # 按名称去重，保留日期最早的
    unique_events = {}
    for name, dt in future_events:
        if name not in unique_events or dt < unique_events[name]:
            unique_events[name] = dt
            
    sorted_events = sorted(unique_events.items(), key=lambda x: x[1])
    return sorted_events[:n]

def predict_next_valley():
    """
    结合官方活动大促日历，预测下一次周期性载具低谷日期及天数
    """
    now = datetime.now()
    future_valleys = predict_future_valleys(now, 1)
    next_event = future_valleys[0]
    days_left = (next_event[1] - now).days
    
    return {
        "event_name": next_event[0],
        "expected_date": next_event[1].strftime('%Y-%m-%d'),
        "days_left": days_left
    }

def evaluate_item(item, current_date_str=None):
    """
    运行多因子量化评估模型，生成更精准的上涨潜力评分和操作建议
    """
    if not current_date_str:
        current_date_str = datetime.now().strftime('%Y-%m-%d')
    current_date = datetime.strptime(current_date_str, '%Y-%m-%d')

    sell_price = item.get('sellPrice')
    buy_price = item.get('buyPrice')
    sell_orders = item.get('sellOrders') or 0
    buy_orders = item.get('buyOrders') or 0
    raw_history = item.get('history') or []
    
    # 兼容自适应逻辑：如果历史价格 pt[1] 大于 10000 (因为单个售卖上限是 2000 GJN)，则除以 10000
    history = []
    for pt in raw_history:
        if len(pt) >= 2:
            t = pt[0]
            p = float(pt[1])
            if p > 10000.0:
                p = p / 10000.0
            history.append([t, p])
            
    # 将清洗后的历史数据写回 item 中，确保生成的 HTML JSON 数组里也是正确的浮点数值
    item['history'] = history
    
    # 计算价差比率
    spread = None
    if sell_price and buy_price and sell_price > 0:
        spread = (sell_price - buy_price) / sell_price

    # 历史趋势基本分析
    slope, avg_price = calculate_linear_regression(history)
    ma7 = calculate_recent_ma(history, days=7) or (sell_price or 0.0)
    
    recent_trend_pct = 0.0
    if ma7 and avg_price > 0:
        recent_trend_pct = (ma7 - avg_price) / avg_price

    # 分析时间跨度与首次挂载
    history_days = 0
    first_listed_date = "暂无数据"
    first_listed_days = -1.0
    if history:
        sorted_history_asc = sorted(history, key=lambda x: x[0])
        first_timestamp_ms = sorted_history_asc[0][0]
        
        try:
            first_listed_date = datetime.fromtimestamp(first_timestamp_ms / 1000.0).strftime('%Y-%m-%d')
        except Exception:
            first_listed_date = "格式错误"
            
        try:
            first_listed_days = round((datetime.now().timestamp() * 1000.0 - first_timestamp_ms) / (1000.0 * 60 * 60 * 24), 1)
            if first_listed_days < 0:
                first_listed_days = 0.0
        except Exception:
            first_listed_days = -1.0
 
        if len(sorted_history_asc) >= 2:
            history_days = (sorted_history_asc[-1][0] - sorted_history_asc[0][0]) / (1000.0 * 60 * 60 * 24)

    # 兜底判定：如果没有有效的成交历史，给出稳健的默认评测指标
    if not history or sell_price is None or sell_price <= 0:
        return {
            "spread": spread,
            "dailySlope": 0.0,
            "avgPrice": sell_price or 0.0,
            "recentTrendPct": 0.0,
            "growthScore": 40.0,
            "action": "HOLD_NEUTRAL",
            "firstListedDate": first_listed_date,
            "firstListedDays": first_listed_days,
            "lastCrashDate": "未检测到大跌",
            "lastCrashDrop": 0.0,
            "nextValleyEvent": "官方胜利日活动",
            "nextValleyDate": "2026-05-08",
            "nextValleyDays": 0,
            "suggestedBuyDate": current_date_str,
            "suggestedSellDate": current_date_str
        }

    sorted_history = sorted(history, key=lambda x: x[0])
    p_initial = sorted_history[0][1]
    p_current = sell_price

    # ==========================================
    # 2. 核心 6 因子估值量化引擎计算 (0 - 100分)
    # ==========================================

    # A. 稀缺度因子 (Scarcity Factor) —— 权重 20%
    if sell_orders <= 5:
        f_scarcity = 100.0
    elif sell_orders <= 30:
        f_scarcity = 100.0 - (sell_orders - 5) * 2.0
    elif sell_orders <= 100:
        f_scarcity = 50.0 - (sell_orders - 30) * 0.5
    elif sell_orders <= 250:
        f_scarcity = 15.0 - (sell_orders - 100) * 0.1
    else:
        f_scarcity = 0.0

    # B. 供求比因子 (Demand/Supply Factor) —— 权重 15%
    # 【v3移植自适应校准】如果缺少求购挂单数据（无 Token 定时抓取状态），启动供求比特征插补，防止白白丢掉 15% 的分值
    if (buy_orders == 0 or buy_price is None or buy_price <= 0):
        # 稀缺度佳且流动性高的商品，求购热度在市场规律中自动锚定在较高水位
        f_ds = 40.0 + 0.3 * f_scarcity + 0.3 * (min(100.0, (len(history) / 5.0) * 100.0) if history else 0.0)
        f_ds = max(20.0, min(95.0, f_ds))
    else:
        ds_ratio = buy_orders / sell_orders if sell_orders > 0 else buy_orders
        f_ds = min(100.0, (ds_ratio / 4.0) * 100.0)

    # C. 长期历史回报率因子 (Long-term Return Factor) —— 权重 15%
    growth_multiplier = p_current / p_initial if p_initial > 0 else 1.0
    f_return = min(100.0, (growth_multiplier / 3.0) * 100.0)

    # D. 绝对大底安全边际因子 (Safety Margin Factor) —— 权重 20%
    min_price = min(pt[1] for pt in sorted_history)
    price_to_bottom = (p_current - min_price) / min_price if min_price > 0 else 0.0
    if price_to_bottom <= 0.15:
        f_safety = 100.0 
    elif price_to_bottom <= 1.50:
        f_safety = 100.0 - ((price_to_bottom - 0.15) / 1.35) * 80.0
    else:
        f_safety = 20.0

    # E. 短期价格动量因子 (Short-term Price Momentum Factor) —— 权重 15%
    ma30 = calculate_recent_ma(history, days=30) or p_current
    ma_bias = (ma7 - ma30) / ma30 if ma30 > 0 else 0.0
    f_momentum = 50.0 + (ma_bias * 333.3)
    f_momentum = max(0.0, min(100.0, f_momentum))

    # F. 交易流动性因子 (Liquidity Factor) —— 权重 15%
    # 计算最近 30 天内有效交易成交的天数密集度，防止发掘出有价无市的僵尸物品
    latest_t = sorted_history[-1][0]
    cutoff_30d = latest_t - 30 * 24 * 60 * 60 * 1000
    recent_pts_count = sum(1 for pt in sorted_history if pt[0] >= cutoff_30d)
    # 近 30 天有 5 期以上不同的交易价格录入即为流动性充足
    f_liquidity = min(100.0, (recent_pts_count / 5.0) * 100.0)

    # 汇总计算基础潜力得分
    growth_score = (
        0.20 * f_scarcity +
        0.15 * f_ds +
        0.15 * f_return +
        0.20 * f_safety +
        0.15 * f_momentum +
        0.15 * f_liquidity
    )

    # G. 惩罚修正项：高价差阻力扣分 (High Spread Penalty)
    # 如果买卖挂单价差高达 35% 以上，说明虚高泡沫严重，直接重扣 20 分
    if spread and spread > 0.35:
        growth_score = max(0.0, growth_score - 20.0)

    # 限制潜力得分最终区间
    growth_score = max(0.0, min(100.0, growth_score))

    # ==========================================
    # 3. 制定行动建议决策逻辑
    # ==========================================
    action = "HOLD_NEUTRAL"
    is_extremely_scarce = (sell_orders > 0 and sell_orders <= 10) or (sell_orders == 0 and buy_orders > 0)
    is_heavy_supply = sell_orders >= 120
    
    if growth_score >= 75 and not is_heavy_supply:
        action = "STRONG_HOLD"
    elif growth_score <= 35 and p_current > avg_price * 1.10:
        action = "GRADUAL_SELL"
    elif p_current < min_price * 1.15 and not is_heavy_supply:
        action = "HOLD_DIP" # 跌入历史绝对大底附近，低位抄底
    elif spread and spread <= 0.05:
        if slope < -0.001:
            action = "QUICK_SELL"
        else:
            action = "HOLD_NEUTRAL"
    elif growth_score >= 70 and slope >= 0.0005:
        if is_heavy_supply:
            action = "HOLD_NEUTRAL"
        else:
            action = "STRONG_HOLD"
    elif growth_score < 40 and p_current > (avg_price * 1.15):
        action = "GRADUAL_SELL"
    elif p_current < (avg_price * 0.85):
        if is_heavy_supply:
            action = "HOLD_NEUTRAL"
        else:
            action = "HOLD_DIP"
    elif slope < -0.002:
        action = "GRADUAL_SELL"
        
    # 检测最近大跌
    crash_date, crash_drop = detect_last_crash(history)
    
    # 预测未来的活动低谷
    future_valleys = predict_future_valleys(current_date, 2)
    next_valley = future_valleys[0]
    next_next_valley = future_valleys[1] if len(future_valleys) > 1 else future_valleys[0]
    
    next_valley_date_str = next_valley[1].strftime('%Y-%m-%d')
    
    # 建议买入日期：
    # 如果 action 是 STRONG_HOLD 或 HOLD_DIP，说明价格被严重低估，为抄底佳期，即建议“当前”买入
    # 否则，建议在大促低谷（nextValleyDate）买入
    if action in ["STRONG_HOLD", "HOLD_DIP"] or (sell_price is not None and sell_price < avg_price * 0.85):
        suggested_buy_date = current_date_str
    else:
        suggested_buy_date = next_valley_date_str

    # 建议卖出日期：
    # 如果 action 是 GRADUAL_SELL 或 QUICK_SELL，代表当前是高点泡沫期或抛压沉重，建议“当前”卖出
    # 如果 action 是 STRONG_HOLD，潜力极佳，建议捂盘增值，可在下下个大促的前夕（低谷往前推15天）卖出以最大化增值
    # 否则（HOLD_NEUTRAL, HOLD_DIP 等稳健持有状态），建议在下一次大促的前夕（低谷往前推15天）卖出，规避大促抛盘踩踏
    from datetime import timedelta
    if action in ["GRADUAL_SELL", "QUICK_SELL"] or (sell_price is not None and sell_price > avg_price * 1.15):
        suggested_sell_date = current_date_str
    elif action == "STRONG_HOLD":
        eve_date = next_next_valley[1] - timedelta(days=15)
        if eve_date < current_date:
            suggested_sell_date = current_date_str
        else:
            suggested_sell_date = eve_date.strftime('%Y-%m-%d')
    else:
        eve_date = next_valley[1] - timedelta(days=15)
        if eve_date < current_date:
            suggested_sell_date = current_date_str
        else:
            suggested_sell_date = eve_date.strftime('%Y-%m-%d')
        
    return {
        "spread": spread,
        "dailySlope": slope,
        "avgPrice": avg_price,
        "recentTrendPct": recent_trend_pct,
        "growthScore": growth_score,
        "action": action,
        "firstListedDate": first_listed_date,
        "firstListedDays": first_listed_days,
        "lastCrashDate": crash_date,
        "lastCrashDrop": round(crash_drop, 1),
        "nextValleyEvent": next_valley[0],
        "nextValleyDate": next_valley_date_str,
        "nextValleyDays": (next_valley[1] - current_date).days,
        "suggestedBuyDate": suggested_buy_date,
        "suggestedSellDate": suggested_sell_date
    }

def analyze_single_file(file_path, meta_data):
    """
    分析单个大盘JSON快照文件，输出分析物品列表与大盘汇总数据
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"[警告] 读取文件失败 {file_path}: {str(e)}")
        return [], {}
        
    if not isinstance(raw_data, list):
        return [], {}
        
    analyzed_list = []
    
    opportunity_count = 0
    scarce_count = 0
    crash_count = 0
    total_val = 0.0
    
    # 提取快照日期作为基准日期进行自适应评估
    h_date_str = datetime.now().strftime('%Y-%m-%d')
    match = re.search(r'gaijin_market_(\d{4}-\d{2}-\d{2})', file_path)
    if match:
        h_date_str = match.group(1)
        
    for item in raw_data:
        metrics = evaluate_item(item, h_date_str)
        
        # 融合大盘数据
        analyzed_item = {
            **item,
            **metrics,
            "addedDate": meta_data["added_dates"].get(item['name'], "")
        }
        analyzed_list.append(analyzed_item)
        
        sell_price = item.get('sellPrice') or 0.0
        total_val += sell_price
        
        if metrics['action'] in ['STRONG_HOLD', 'HOLD_DIP']:
            opportunity_count += 1
            
        sell_orders = item.get('sellOrders') or 0
        buy_orders = item.get('buyOrders') or 0
        if (sell_orders > 0 and sell_orders <= 10) or (sell_orders == 0 and buy_orders > 0):
            scarce_count += 1
            
        if metrics['lastCrashDrop'] >= 30.0:
            crash_count += 1
        
    summary = {
        "totalVehicles": len(analyzed_list),
        "opportunityCount": opportunity_count,
        "scarceCount": scarce_count,
        "crashCount": crash_count,
        # 大盘总售价之和，代表全大盘最低估值市值走势
        "totalSellValue": round(total_val, 2)
    }
    
    return analyzed_list, summary

# ==========================================
# 主流程控制
# ==========================================

def main():
    print("=" * 50)
    print("      Gaijin 全市场大盘载具分析脚本启动 (v2.2)")
    print("=" * 50)
    
    # 1. 查找所有的数据导出文件
    json_files = [f for f in glob.glob("gaijin_market_*.json") if not f.endswith('.bak')]
    
    if not json_files:
        print("\n[错误] 未找到任何导出的市场 JSON 数据文件。")
        print("\n请按以下步骤操作：")
        print("1. 用 Chrome 浏览器登录 https://trade.gaijin.net/?category=vehicles")
        print("2. 按 F12 打开开发者工具，在 Console (控制台) 中运行 exporter.js 脚本")
        print("3. 将下载的 JSON 数据文件移动到当前脚本所在的目录下:")
        print(f"   {os.getcwd()}")
        print("4. 重新运行此 Python 脚本。")
        return
        
    # 2. 读取元数据文件
    meta_path = "market_meta.json"
    meta_data = {"added_dates": {}, "purchase_prices": {}} # 为兼容模板占位符，保留 purchase_prices 键但始终为空
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as mf:
                meta_data = json.load(mf)
                if not isinstance(meta_data, dict):
                    meta_data = {"added_dates": {}, "purchase_prices": {}}
                if "added_dates" not in meta_data:
                    meta_data["added_dates"] = {}
                if "purchase_prices" not in meta_data:
                    meta_data["purchase_prices"] = {}
        except Exception as e:
            print(f"[警告] 读取大盘元数据文件失败: {str(e)}")

    # 3. 升序排序历史文件，建立价格和市场大盘的历史时间线
    history_files = sorted(json_files)
    history_trend = []
    history_snapshots = {}
    
    print(f"[信息] 正在构建多版本历史大盘账本...")
    for h_file in history_files:
        h_date = datetime.now().strftime('%Y-%m-%d')
        match = re.search(r'gaijin_market_(\d{4}-\d{2}-\d{2})', h_file)
        if match:
            h_date = match.group(1)
            
        print(f"      - 分析历史大盘快照: {h_file} [{h_date}]")
        h_list, h_summary = analyze_single_file(h_file, meta_data)
        if h_list:
            history_snapshots[h_date] = h_list
            history_trend.append({
                "date": h_date,
                **h_summary
            })
            
    if not history_trend:
        print("[错误] 未能成功解析任何有效的市场大盘快照数据。")
        return
        
    # 最新版数据
    latest_date = history_trend[-1]["date"]
    analyzed_data = history_snapshots[latest_date]
    latest_summary = history_trend[-1]
    
    # 4. 获取次新数据进行差量比对
    prev_items = {}
    prev_file = None
    if len(history_trend) >= 2:
        prev_date = history_trend[-2]["date"]
        # 次新文件名
        prev_file = next((f for f in json_files if prev_date in f), None)
        prev_items = {item['name']: item for item in history_snapshots[prev_date]}
        
    latest_items = {item['name']: item for item in analyzed_data if 'name' in item}
    meta_dirty = False
    added_list = []
    removed_list = []
    
    # 5. 双向大盘存在性差异比对 (大盘上架和下架)
    all_names = set(list(latest_items.keys()) + list(prev_items.keys()))
    for name in all_names:
        in_latest = name in latest_items
        in_prev = name in prev_items
        
        is_brand_new = (not in_prev and in_latest)
        
        item_added_date = meta_data["added_dates"].get(name)
        if is_brand_new and not item_added_date:
            item_added_date = latest_date
            meta_data["added_dates"][name] = latest_date
            meta_dirty = True
            
        if in_latest:
            latest_items[name]["addedDate"] = item_added_date if item_added_date else ""
            
        if prev_file:
            if not in_prev and in_latest: # 本期新上架
                item = latest_items[name]
                added_list.append({
                    "name": name,
                    "imageUrl": item.get("imageUrl", ""),
                    "url": item.get("url", ""),
                    "quantity": 1,
                    "isBrandNew": True,
                    "sellPrice": item.get("sellPrice"),
                    "addedDate": item_added_date if item_added_date else latest_date
                })
            elif in_prev and not in_latest: # 本期下架售罄
                item = prev_items[name]
                removed_list.append({
                    "name": name,
                    "imageUrl": item.get("imageUrl", ""),
                    "url": item.get("url", ""),
                    "quantity": 1,
                    "isFullySold": True,
                    "sellPrice": item.get("sellPrice")
                })
        else:
            if in_latest:
                item = latest_items[name]
                added_list.append({
                    "name": name,
                    "imageUrl": item.get("imageUrl", ""),
                    "url": item.get("url", ""),
                    "quantity": 1,
                    "isBrandNew": True,
                    "sellPrice": item.get("sellPrice"),
                    "addedDate": item_added_date if item_added_date else latest_date
                })
                
    # 如果大盘元数据被更新，回写文件
    if meta_dirty:
        try:
            with open(meta_path, 'w', encoding='utf-8') as mf:
                json.dump(meta_data, mf, ensure_ascii=False, indent=4)
            print(f"[成功] 自动检测到大盘新录入载具，已更新大盘元数据文件: {meta_path}")
        except Exception as e:
            print(f"[警告] 写入元数据文件失败: {str(e)}")
            
    # 5.5 计算最低在售价跨快照真实波动趋势与大盘潜力修正
    print(f"[信息] 正在分析跨快照最低售价真实波动趋势并校准潜力得分...")
    vehicle_snapshots_prices = {}
    for h_date in sorted(history_snapshots.keys()):
        for item in history_snapshots[h_date]:
            name = item.get("name")
            sell_price = item.get("sellPrice")
            if name and sell_price is not None and sell_price > 0:
                if name not in vehicle_snapshots_prices:
                    vehicle_snapshots_prices[name] = []
                vehicle_snapshots_prices[name].append([h_date, sell_price])
                
    # 联动修正大盘潜力分与行动建议
    for item in analyzed_data:
        name = item.get("name")
        prices = vehicle_snapshots_prices.get(name, [])
        
        growth_pct = 0.0
        growth_mod = 0.0
        volatility = 0.0
        
        if len(prices) >= 2:
            p_first = prices[0][1]
            p_last = prices[-1][1]
            if p_first > 0:
                growth_pct = (p_last - p_first) / p_first
                # 计算修正分：10% 波动折合 3 分，加扣分限制在 [-15.0, 15.0]
                growth_mod = max(-15.0, min(15.0, growth_pct * 30.0))
                
            p_avg = sum(pt[1] for pt in prices) / len(prices)
            if p_avg > 0:
                p_var = sum((pt[1] - p_avg) ** 2 for pt in prices) / len(prices)
                p_std = p_var ** 0.5
                volatility = p_std / p_avg
                
        item["snapshotGrowthPct"] = round(growth_pct * 100.0, 1)
        item["snapshotVolatility"] = round(volatility * 100.0, 1)
        item["snapshotPriceHistoryCount"] = len(prices)
        
        # 修正潜力分并限制在 [0.0, 100.0]
        orig_score = item.get("growthScore", 50.0)
        new_score = max(0.0, min(100.0, orig_score + growth_mod))
        item["growthScore"] = round(new_score, 1)
        
        # 重新校准行动建议
        sell_orders = item.get('sellOrders') or 0
        buy_orders = item.get('buyOrders') or 0
        sell_price = item.get('sellPrice')
        avg_price = item.get('avgPrice') or 0.0
        daily_growth_rate = item.get('dailySlope') / avg_price if avg_price > 0 else 0.0
        
        is_extremely_scarce = (sell_orders > 0 and sell_orders <= 10) or (sell_orders == 0 and buy_orders > 0)
        is_heavy_supply = sell_orders >= 120
        
        if sell_price is not None:
            if is_extremely_scarce and sell_price <= (avg_price * 1.30):
                if new_score >= 50:
                    item["action"] = "STRONG_HOLD"
            elif new_score >= 70 and daily_growth_rate >= 0.0005:
                if not is_heavy_supply:
                    item["action"] = "STRONG_HOLD"
                else:
                    item["action"] = "HOLD_NEUTRAL"
            elif new_score < 40 and sell_price > (avg_price * 1.15):
                item["action"] = "GRADUAL_SELL"

    print(f"[分析完成] 当前最新大盘日期: {latest_date}")
    print(f"[分析完成] 市场收录总载具: {latest_summary['totalVehicles']} 种")
    print(f"[分析完成] 超跌/低估机会: {latest_summary['opportunityCount']} 种")
    print(f"[分析完成] 极度稀缺物品: {latest_summary['scarceCount']} 种")
    print(f"[分析完成] 历史回溯: 累积分析了 {len(history_trend)} 期大盘快照")
    if prev_file:
        print(f"[分析完成] 大盘变动对比: 新上架 {len(added_list)} 种，已下架 {len(removed_list)} 种")
        
    # 6. 读取 HTML 模板并合并生成最终报告
    template_path = "report_template.html"
    report_path = "report.html"
    
    if not os.path.exists(template_path):
        print(f"[错误] 未找到 HTML 模板文件 {template_path}，无法生成大盘分析面板。")
        return
        
    try:
        with open(template_path, 'r', encoding='utf-8') as tf:
            template_content = tf.read()
            
        # 将分析的数据序列化为 JSON 字符串
        json_data_str = json.dumps(analyzed_data, ensure_ascii=False)
        
        diff_data = {
            "added": added_list,
            "removed": removed_list
        }
        json_diff_str = json.dumps(diff_data, ensure_ascii=False)
        json_meta_str = json.dumps(meta_data, ensure_ascii=False)
        
        # 序列化历史相关数据
        json_trend_str = json.dumps(history_trend, ensure_ascii=False)
        json_snapshots_str = json.dumps(history_snapshots, ensure_ascii=False)
        
        # 替换模板占位符
        final_content = template_content.replace("{{INVENTORY_DATA_JSON}}", json_data_str)
        final_content = final_content.replace("{{INVENTORY_DIFF_JSON}}", json_diff_str)
        final_content = final_content.replace("{{INVENTORY_META_JSON}}", json_meta_str)
        final_content = final_content.replace("{{HISTORY_TREND_JSON}}", json_trend_str)
        final_content = final_content.replace("{{HISTORY_SNAPSHOTS_JSON}}", json_snapshots_str)
        
        # 写入 report.html
        with open(report_path, 'w', encoding='utf-8') as rf:
            rf.write(final_content)
            
        print("\n" + "=" * 50)
        print(f"[成功] 可视化分析大盘报告已生成: {report_path}")
        print("请在浏览器中直接双击打开 report.html 查看华丽的黑金分析面板！")
        print("=" * 50)
        
    except Exception as e:
        print(f"[错误] 合并 HTML 报表失败: {str(e)}")

if __name__ == "__main__":
    main()
