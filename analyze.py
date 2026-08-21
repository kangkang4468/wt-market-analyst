import os
import json
import glob
from datetime import datetime, timedelta
import sys
import re

# 尝试在 Windows 下启用 UTF-8 输出，防止控制台中文乱码
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ==========================================
# 核心数据分析与智能分类算法 (纯 Python 标准库实现)
# ==========================================

def classify_item(name):
    """
    智能识别 Gaijin 市场物品类别: 载具 / 涂装 / 箱子 / 道具/挂饰 / 活动材料 / 其他
    """
    if not name:
        return '其他'
    n = name.strip()
    
    # 1. 箱子 / 战利品 (Crates / Trophies / Chests)
    if any(k in n for k in ['百宝箱', '物资箱', '战利品', '箱', 'Trophy', 'Chest', 'Crate', 'Container']):
        return '箱子'
        
    # 2. 涂装 / 迷彩 (Camouflages / Skins)
    if any(k in n for k in ['涂装', '迷彩', 'camo', 'Camo', 'Skin', 'skin', 'Squadron', 'Regiment', 'Régiment', 'Marine Corps', 'Battalion', 'Chutai', 'Sensha-gun', 'Red Devils', 'Red Arrows', 'HMS Bulldog', 'Cat Squadron', 'division', 'PLA', 'Indonesian']):
        return '涂装'
    if "'" in n or "‘" in n or "’" in n:
        return '涂装'
    if ':' in n and any(k in n for k in ['冬季', '夏季', '斑点', '双色', '三色', '沙漠', '林地', '历史', '非标准', '迷彩', '涂装']):
        return '涂装'
        
    # 3. 活动材料 / 零件 / 工具 (Crafting / Event Materials)
    if any(k in n for k in ['材料', '零件', '工具', 'Toolkit', 'Material', '蓝图', 'Blueprint', '方案', '升级套件', '订单', '合同', 'Contract', 'Order']):
        return '活动材料'
        
    # 4. 道具 / 挂饰 / 贴花 / 头像 / 钥匙 (Decorators / Decals / Avatars / Items)
    if any(k in n for k in [
        '钥匙', 'Key', '贴花', 'Decal', '徽标', '涂鸦', '头像', '资料头像', 'Avatar', 'Icon', '头衔', 'Title', '挂饰', 'Decorator',
        '机枪', '步枪', '骑枪', '防弹衣', '背心', '足球', '仙女棒', '风筝', '圣诞老人', '战士', '九头蛇', '斯芬克斯',
        '女巫', '哈比', '马头鱼尾兽', '仙女', '旗帜', 'Flag', '冻人飞霜', '即兴炫技', '圣火', '探索不止', '攀登新高峰',
        '树不会走路', '汉斯·踹普', '滑翔风筝', '灼痛吐息', '炙烈印记', '炽热火焰', '焰色华彩', '燎原火星', '爆燃烈焰', '雪地会说话'
    ]):
        return '道具/挂饰'
        
    # 5. 载具判定 (Vehicles)
    country_tags = [
        '（苏联）', '（德国）', '（美国）', '（英国）', '（中国）', '（法国）', '（日本）', '（意大利）', '（瑞典）', '（以色列）',
        '(USSR)', '(USA)', '(Germany)', '(Britain)', '(China)', '(France)', '(Japan)', '(Italy)', '(Sweden)', '(Israel)'
    ]
    if any(tag in n for tag in country_tags):
        return '载具'
    if any(k in n for k in [
        '坦克', '工程', '战斗机', '直升机', '巡洋舰', '驱逐舰', '战列舰', '舰', '型', '现代化', '豹', '虎', '狼',
        '百夫长', '丘吉尔', '拳师犬', '掠夺者', '美洲', '幼狮', '米格', 'F-', 'T-', 'Sd.Kfz.', 'M6', 'M4', 'IS-', 'PT-'
    ]):
        return '载具'
        
    return '其他'

def calculate_linear_regression(history):
    """
    计算价格历史数据的线性回归斜率和均价
    history: [[timestamp_ms, price_f, (volume)], ...]
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
    计算最近几天 (自然天) 的成交移动平均线
    """
    if not history:
        return None
    sorted_history = sorted(history, key=lambda x: x[0], reverse=True)
    t_latest = sorted_history[0][0]
    
    # 过滤出最近 days 天的数据点
    cutoff = t_latest - (days * 24 * 60 * 60 * 1000)
    recent_pts = [pt[1] for pt in sorted_history if pt[0] >= cutoff]
    return sum(recent_pts) / len(recent_pts) if recent_pts else None

def calculate_fair_price(sell_price, buy_price, ma30, spread):
    """
    计算公允估值 (Fair Price)：
    如果挂单价过高（如虚高挂单/无买盘承接的大价差），进行保守公允估值折价，避免总资产虚高
    """
    if sell_price is None or sell_price <= 0:
        return 0.0
    
    if spread is None or spread <= 0.25:
        return sell_price
    
    # 当价差 > 25% 时，存在一定流动性折价或挂单泡沫
    if buy_price and buy_price > 0:
        if ma30 and ma30 > 0:
            anchor = max(buy_price, ma30 * 1.05)
            fair = min(sell_price, anchor)
        else:
            fair = min(sell_price, buy_price * 1.20)
    else:
        if ma30 and ma30 > 0:
            fair = min(sell_price, ma30 * 1.10)
        else:
            fair = sell_price * 0.80
            
    return round(fair, 2)

def detect_last_crash(history):
    """
    分析历史价格数据，寻找最近一次在 30 天内价格大跌超 30% 的事件
    history: [[timestamp_ms, price_f, ...], ...]
    返回: (crash_date, crash_drop_pct)
    """
    if not history or len(history) < 2:
        return "暂无大跌记录", 0.0
        
    # 按照时间戳升序排序
    sorted_history = sorted(history, key=lambda x: x[0])
    
    max_drops = [] # [(valley_time, drop_pct), ...]
    window_ms = 30 * 24 * 60 * 60 * 1000 # 30天
    
    for i in range(len(sorted_history)):
        t_i, p_i = sorted_history[i][0], sorted_history[i][1]
        if p_i <= 0:
            continue
            
        # 寻找 i 之后 30 天内的最低价格点
        min_p = p_i
        min_t = t_i
        for j in range(i + 1, len(sorted_history)):
            t_j, p_j = sorted_history[j][0], sorted_history[j][1]
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
        ("春季胜利日大促", (5, 8)),
        ("夏季马拉松活动", (8, 20)),
        ("周年庆狂欢大促", (11, 1)),
        ("冬季圣诞特惠活动", (12, 28))
    ]
    
    future_events = []
    # 考虑今年和明年的活动
    for y in [year, year + 1]:
        for name, (m, d) in events:
            evt_date = datetime(y, m, d)
            if evt_date >= base_date:
                future_events.append((name, evt_date))
                
    # 按名称去重，保留日期最早的
    unique_events = {}
    for name, dt in future_events:
        if name not in unique_events or dt < unique_events[name]:
            unique_events[name] = dt
            
    sorted_events = sorted(unique_events.items(), key=lambda x: x[1])
    return sorted_events[:n]

def evaluate_item(item, current_date_str=None):
    """
    运行重构后的 5 因子量化评估模型 (含全市场公允估值、防天花板抑制与智能品类感知)，生成精准评分与大盘操作建议
    """
    if not current_date_str:
        current_date_str = datetime.now().strftime('%Y-%m-%d')
    current_date = datetime.strptime(current_date_str, '%Y-%m-%d')

    item_name = item.get('name', '')
    category = item.get('category') or classify_item(item_name)
    item['category'] = category

    sell_price = item.get('sellPrice')
    buy_price = item.get('buyPrice')
    sell_orders = item.get('sellOrders') or 0
    buy_orders = item.get('buyOrders') or 0
    raw_history = item.get('history') or []
    
    # 清洗历史数据：兼容 2 元组 [t, p] 与 3 元组 [t, p, volume]
    history = []
    for pt in raw_history:
        if len(pt) >= 2:
            t = pt[0]
            p = float(pt[1])
            # 兼容自适应逻辑：如果历史价格 pt[1] 大于 10000 (因为单个售卖上限是 2000 GJN)，则除以 10000
            if p > 10000.0:
                p = p / 10000.0
            
            if len(pt) >= 3:
                v = int(pt[2])
                history.append([t, p, v])
            else:
                history.append([t, p])
            
    item['history'] = history
    
    # 计算价差比率 (买卖贴合度)
    spread = None
    if sell_price and buy_price and sell_price > 0:
        spread = (sell_price - buy_price) / sell_price

    # 历史趋势基本分析
    slope, avg_price = calculate_linear_regression(history)
    ma7 = calculate_recent_ma(history, days=7) or (sell_price or 0.0)
    ma30 = calculate_recent_ma(history, days=30) or (sell_price or 0.0)
    
    # 归一化日均斜率收益率（去除绝对价格量纲影响）
    norm_daily_slope = (slope / avg_price) if avg_price > 0 else 0.0
    
    recent_trend_pct = 0.0
    if ma7 and avg_price > 0:
        recent_trend_pct = (ma7 - avg_price) / avg_price

    # 公允价值估算
    fair_price = calculate_fair_price(sell_price, buy_price, ma30, spread)
    is_near_ceiling = bool(sell_price and sell_price >= 1800.0)

    # 分析时间跨度与首次挂载
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

    # 兜底判定：如果没有有效的成交历史，给出稳健的默认评测指标
    if not history or sell_price is None or sell_price <= 0:
        return {
            "category": category,
            "spread": spread,
            "dailySlope": 0.0,
            "normDailySlope": 0.0,
            "avgPrice": sell_price or 0.0,
            "fairPrice": sell_price or 0.0,
            "isNearCeiling": is_near_ceiling,
            "recentTrendPct": 0.0,
            "growthScore": 40.0,
            "action": "HOLD_NEUTRAL",
            "firstListedDate": first_listed_date,
            "firstListedDays": first_listed_days,
            "lastCrashDate": "未检测到大跌",
            "lastCrashDrop": 0.0,
            "nextValleyEvent": "官方胜利日大促",
            "nextValleyDate": "2026-05-08",
            "nextValleyDays": 0,
            "suggestedBuyDate": current_date_str,
            "suggestedSellDate": current_date_str
        }

    sorted_history = sorted(history, key=lambda x: x[0])
    p_current = sell_price
    min_price = min(pt[1] for pt in sorted_history)
    max_price = max(pt[1] for pt in sorted_history)

    # ==========================================
    # 核心 5 因子动态量化模型 (0 - 100分)
    # ==========================================

    # A. 稀缺度与供应因子 (Scarcity Factor) —— 权重 25%
    if sell_orders <= 3:
        f_scarcity = 100.0
    elif sell_orders <= 10:
        f_scarcity = 100.0 - (sell_orders - 3) * 2.5 # 10 -> 82.5
    elif sell_orders <= 30:
        f_scarcity = 82.5 - (sell_orders - 10) * 1.5 # 30 -> 52.5
    elif sell_orders <= 80:
        f_scarcity = 52.5 - (sell_orders - 30) * 0.65 # 80 -> 20.0
    elif sell_orders <= 150:
        f_scarcity = 20.0 - (sell_orders - 80) * 0.25 # 150 -> 2.5
    else:
        f_scarcity = 0.0

    # B. 真实买盘承接力与流动性质量 (Demand & Liquidity Factor) —— 权重 20%
    if spread is not None and sell_price > 0:
        if spread <= 0.05:
            spread_score = 100.0
        elif spread <= 0.35:
            spread_score = 100.0 - ((spread - 0.05) / 0.30) * 70.0
        else:
            spread_score = max(5.0, 30.0 - (spread - 0.35) * 60.0)
    else:
        spread_score = 40.0
        
    latest_t = sorted_history[-1][0]
    cutoff_30d = latest_t - 30 * 24 * 60 * 60 * 1000
    recent_pts_count = sum(1 for pt in sorted_history if pt[0] >= cutoff_30d)
    activity_score = min(100.0, (recent_pts_count / 8.0) * 100.0)
    f_demand = 0.60 * spread_score + 0.40 * activity_score

    # C. 归一化趋势动量因子 (Trend Momentum Factor) —— 权重 20%
    slope_score = 50.0 + (norm_daily_slope * 25000.0)
    slope_score = max(0.0, min(100.0, slope_score))
    
    ma_bias = (ma7 - ma30) / ma30 if ma30 > 0 else 0.0
    bias_score = 50.0 + (ma_bias * 250.0)
    bias_score = max(0.0, min(100.0, bias_score))
    
    f_momentum = 0.50 * slope_score + 0.50 * bias_score

    # D. 估值分位与安全边际因子 (Valuation & Safety Factor) —— 权重 20%
    all_prices = sorted([pt[1] for pt in sorted_history])
    if all_prices and len(all_prices) >= 2:
        rank = sum(1 for p in all_prices if p <= p_current) / len(all_prices)
        f_safety = 100.0 - (rank * 70.0)
        f_safety = max(10.0, min(100.0, f_safety))
    else:
        f_safety = 50.0

    # E. 2000 GJN 交易所硬顶抑制因子 (Ceiling Headroom Factor) —— 权重 15%
    if p_current >= 1900.0:
        f_ceiling = 10.0
    elif p_current >= 1600.0:
        f_ceiling = 60.0 - ((p_current - 1600.0) / 300.0) * 50.0
    elif p_current >= 800.0:
        f_ceiling = 90.0 - ((p_current - 800.0) / 800.0) * 30.0
    else:
        f_ceiling = 100.0

    # 综合潜力得分
    growth_score = (
        0.25 * f_scarcity +
        0.20 * f_demand +
        0.20 * f_momentum +
        0.20 * f_safety +
        0.15 * f_ceiling
    )

    # 惩罚项：如果高供给(>40)且价差过大(>35%)，说明流动性黑洞与泡沫，重扣 15 分
    if sell_orders > 40 and spread and spread > 0.35:
        growth_score = max(0.0, growth_score - 15.0)

    # 特殊品类规则校准：
    if category == '箱子':
        # 箱子长期无限掉落通胀，增长潜力受限
        growth_score = min(growth_score, 35.0)
    elif category == '活动材料':
        growth_score = min(growth_score, 25.0)

    growth_score = round(max(0.0, min(100.0, growth_score)), 1)

    # ==========================================
    # 决策树与行动建议 (Action Decision Tree)
    # ==========================================
    is_heavy_supply = sell_orders >= 100
    is_deep_valley = (p_current <= min_price * 1.12) or (avg_price > 0 and p_current <= avg_price * 0.85)

    if category == '活动材料':
        action = "QUICK_SELL" # 活动材料时效性强，尽快变现
    elif category == '箱子':
        action = "GRADUAL_SELL" if p_current > 0.15 else "HOLD_NEUTRAL"
    elif is_near_ceiling:
        action = "GRADUAL_SELL" # 触及 2000 GJN 极值天花板，分批止盈
    elif growth_score >= 72 and not is_heavy_supply:
        action = "STRONG_HOLD"  # 高评分+稀缺通缩：强力持有
    elif is_deep_valley and not is_heavy_supply and growth_score >= 48:
        action = "HOLD_DIP"     # 处于底部区域：低位吸筹/持有
    elif growth_score < 40 and p_current > (avg_price * 1.15):
        action = "GRADUAL_SELL" # 估值偏高且潜力衰竭：建议分批止盈
    elif is_heavy_supply and norm_daily_slope < -0.002:
        action = "QUICK_SELL"   # 供应泛滥且持续走跌：即刻变现止损
    elif growth_score >= 50:
        action = "HOLD_NEUTRAL" # 稳健观察
    elif norm_daily_slope < -0.0015:
        action = "GRADUAL_SELL" # 持续下行：减仓
    else:
        action = "HOLD_NEUTRAL"
        
    # 检测最近大跌
    crash_date, crash_drop = detect_last_crash(history)
    
    # 预测未来的活动低谷
    future_valleys = predict_future_valleys(current_date, 2)
    next_valley = future_valleys[0]
    next_next_valley = future_valleys[1] if len(future_valleys) > 1 else future_valleys[0]
    
    next_valley_date_str = next_valley[1].strftime('%Y-%m-%d')
    days_to_next_valley = (next_valley[1] - current_date).days
    
    # 建议买入日期：
    if action in ["STRONG_HOLD", "HOLD_DIP"] or is_deep_valley:
        suggested_buy_date = current_date_str
    else:
        suggested_buy_date = next_valley_date_str

    # 建议卖出日期：
    if action in ["GRADUAL_SELL", "QUICK_SELL"] or is_near_ceiling or category == '活动材料':
        suggested_sell_date = current_date_str
    elif action == "STRONG_HOLD":
        # 强力持有：锁定大促后的主升浪，在下下个大促前 20 天锁定利润
        target_date = next_next_valley[1] - timedelta(days=20)
        if target_date <= current_date:
            target_date = next_next_valley[1] + timedelta(days=40)
        suggested_sell_date = target_date.strftime('%Y-%m-%d')
    else:
        # 稳健持有 / 低谷等待
        # 如果距离下一次大促已不足 15 天，市场正处于恐慌砸盘期，严禁此时割肉，应建议在反弹窗口期卖出
        if days_to_next_valley <= 15:
            target_date = next_valley[1] + timedelta(days=35)
        else:
            target_date = next_valley[1] - timedelta(days=15)
        suggested_sell_date = target_date.strftime('%Y-%m-%d')
        
    return {
        "category": category,
        "spread": spread,
        "dailySlope": slope,
        "normDailySlope": norm_daily_slope,
        "avgPrice": avg_price,
        "fairPrice": fair_price,
        "isNearCeiling": is_near_ceiling,
        "recentTrendPct": recent_trend_pct,
        "growthScore": growth_score,
        "action": action,
        "firstListedDate": first_listed_date,
        "firstListedDays": first_listed_days,
        "lastCrashDate": crash_date,
        "lastCrashDrop": round(crash_drop, 1),
        "nextValleyEvent": next_valley[0],
        "nextValleyDate": next_valley_date_str,
        "nextValleyDays": days_to_next_valley,
        "suggestedBuyDate": suggested_buy_date,
        "suggestedSellDate": suggested_sell_date
    }

def analyze_single_file(file_path, meta_data):
    """
    分析单个大盘JSON快照文件，输出分析物品列表与大盘汇总数据 (含挂牌市值与公允估值双口径)
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
    total_fair = 0.0
    
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
        fair_price = metrics.get('fairPrice') or sell_price
        total_val += sell_price
        total_fair += fair_price
        
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
        "totalSellValue": round(total_val, 2),
        "totalFairValue": round(total_fair, 2),
        "netValue": round(total_val * 0.85, 2),
        "netFairValue": round(total_fair * 0.85, 2)
    }
    
    return analyzed_list, summary

# ==========================================
# 主流程控制
# ==========================================

def main():
    print("=" * 50)
    print("      Gaijin 全市场大盘载具分析脚本启动 (v4.1 智能分类与量化版)")
    print("=" * 50)
    
    # 1. 查找所有的数据导出文件
    json_files = [f for f in glob.glob(os.path.join("daily_json", "gaijin_market_*.json")) if not f.endswith('.bak')]
    
    if not json_files:
        print("\n[错误] 未找到任何导出的市场 JSON 数据文件。")
        print("\n请按以下步骤操作：")
        print("1. 用 Chrome 浏览器登录 https://trade.gaijin.net/?category=vehicles")
        print("2. 按 F12 打开开发者工具，在 Console (控制台) 中运行 exporter.js 脚本")
        print("3. 将下载的 JSON 数据文件移动到当前脚本所在目录的 daily_json 文件夹下:")
        print(f"   {os.path.join(os.getcwd(), 'daily_json')}")
        print("4. 重新运行此 Python 脚本。")
        return
        
    # 2. 读取元数据文件
    meta_path = "market_meta.json"
    meta_data = {"added_dates": {}, "purchase_prices": {}}
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
            print(f"[警告] 读取元数据文件失败: {str(e)}")

    # 3. 升序排序历史文件，建立资产增值时间走势
    history_files = sorted(json_files)
    history_trend = []
    history_snapshots = {}
    
    print(f"[信息] 正在构建多版本历史大盘账本...")
    for h_file in history_files:
        h_date = datetime.now().strftime('%Y-%m-%d')
        match = re.search(r'gaijin_market_(\d{4}-\d{2}-\d{2})', h_file)
        if match:
            h_date = match.group(1)
            
        print(f"      - 分析历史快照: {h_file} [{h_date}]")
        h_list, h_summary = analyze_single_file(h_file, meta_data)
        if h_list:
            history_snapshots[h_date] = h_list
            history_trend.append({
                "date": h_date,
                **h_summary
            })
            
    if not history_trend:
        print("[错误] 未能成功解析任何有效的大盘快照数据。")
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
        prev_file = next((f for f in json_files if prev_date in f), None)
        prev_items = {item['name']: item for item in history_snapshots[prev_date]}
        
    latest_items = {item['name']: item for item in analyzed_data if 'name' in item}
    meta_dirty = False
    added_list = []
    removed_list = []
    
    # 5. 双向差异比对（新增上架 / 售罄下架）
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
            if in_latest and not in_prev:
                item = latest_items[name]
                added_list.append({
                    "name": name,
                    "imageUrl": item.get("imageUrl", ""),
                    "url": item.get("url", ""),
                    "quantity": 1,
                    "isBrandNew": is_brand_new,
                    "sellPrice": item.get("sellPrice"),
                    "category": item.get("category", "其他"),
                    "addedDate": item_added_date if item_added_date else latest_date
                })
            elif in_prev and not in_latest:
                item = prev_items[name]
                removed_list.append({
                    "name": name,
                    "imageUrl": item.get("imageUrl", ""),
                    "url": item.get("url", ""),
                    "quantity": 1,
                    "isFullySold": True,
                    "sellPrice": item.get("sellPrice"),
                    "category": item.get("category", "其他")
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
                    "category": item.get("category", "其他"),
                    "addedDate": item_added_date if item_added_date else latest_date
                })
                
    # 如果元数据被更新，回写文件
    if meta_dirty:
        try:
            with open(meta_path, 'w', encoding='utf-8') as mf:
                json.dump(meta_data, mf, ensure_ascii=False, indent=4)
            print(f"[成功] 自动检测到新上市载具，已更新本地元数据文件: {meta_path}")
        except Exception as e:
            print(f"[警告] 写入元数据文件失败: {str(e)}")
            
    # 5.5 计算真实在售价跨快照波动与潜力微调
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
                
    # 修正最新快照的潜力分与行动建议
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
                growth_mod = max(-10.0, min(10.0, growth_pct * 25.0))
                
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
        
        # 联动校准行动建议
        category = item.get("category", "其他")
        sell_orders = item.get('sellOrders') or 0
        sell_price = item.get('sellPrice')
        avg_price = item.get('avgPrice') or 0.0
        norm_daily_slope = item.get('normDailySlope', 0.0)
        is_scarce = (sell_orders > 0 and sell_orders <= 15)
        is_heavy_supply = sell_orders >= 100
        is_near_ceiling = item.get("isNearCeiling", False)
        
        if category == '载具' and sell_price is not None:
            if is_near_ceiling:
                item["action"] = "GRADUAL_SELL"
            elif is_scarce and new_score >= 65 and not is_near_ceiling:
                item["action"] = "STRONG_HOLD"
            elif new_score >= 72 and norm_daily_slope >= 0.0003 and not is_heavy_supply:
                item["action"] = "STRONG_HOLD"
            elif new_score < 38 and sell_price > (avg_price * 1.15):
                item["action"] = "GRADUAL_SELL"

    print(f"[分析完成] 当前最新大盘日期: {latest_date}")
    print(f"[分析完成] 大盘载具/物品数: {latest_summary['totalVehicles']} 种")
    print(f"[分析完成] 大盘最低挂牌总额: {latest_summary['totalSellValue']:.2f} GJN (税后净值: {latest_summary['netValue']:.2f} GJN)")
    print(f"[分析完成] 大盘保守公允估值: {latest_summary['totalFairValue']:.2f} GJN (公允净值: {latest_summary['netFairValue']:.2f} GJN)")
    print(f"[分析完成] 超跌与低估机会: {latest_summary['opportunityCount']} 种 | 极度稀缺: {latest_summary['scarceCount']} 种")
    print(f"[分析完成] 历史回溯: 累积分析了 {len(history_trend)} 期快照")
    if prev_file:
        print(f"[分析完成] 变动对比: 新增上架 {len(added_list)} 种，售罄/下架 {len(removed_list)} 种")
        
    # 6. 读取 HTML 模板并合并生成最终报告
    template_path = "report_template.html"
    report_path = "report.html"
    
    if not os.path.exists(template_path):
        print(f"[错误] 未找到 HTML 模板文件 {template_path}，无法生成分析面板。")
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
        
        # 写入 report.html 同时也更新 index.html 确保看板最新
        for path in [report_path, "index.html"]:
            with open(path, 'w', encoding='utf-8') as rf:
                rf.write(final_content)
            
        print("\n" + "=" * 50)
        print(f"[成功] 可视化分析报告已同步生成: {report_path} & index.html")
        print("请在浏览器中直接双击打开 report.html 或 index.html 查看全市场黑金量化分析面板！")
        print("=" * 50)
        
    except Exception as e:
        print(f"[错误] 合并 HTML 报表失败: {str(e)}")

if __name__ == "__main__":
    main()
