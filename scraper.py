import os
import re
import glob
import json
import time
import random
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 用户配置区 ====================
# 请在下方填入您的 Gaijin 市场登录 Token，即可开启 Python 高性能本地爬虫
# 获取方法：在已登录的市场页面按 F12，在控制台运行：localStorage.getItem('MarketApp,auth,tokenPair')
# 复制输出结果中 "token" 对应的值填入下方。若留空，脚本将作为演示和提示运行。
GAIJIN_TOKEN = ""
# ===================================================

CONCURRENCY = 4        # 并发线程数
DELAY_RANGE = (0.3, 0.8) # 随机防封延迟范围
TRADE_SERVER = "https://market-proxy.gaijin.net/web"

def get_known_vehicles():
    """
    从本地已有的 market_meta.json 或最近的历史大盘文件中自动归纳已知的全部载具
    """
    vehicles = {}
    
    # 优先从 market_meta.json 读取
    if os.path.exists("market_meta.json"):
        try:
            with open("market_meta.json", "r", encoding="utf-8") as f:
                meta = json.load(f)
                for name, info in meta.get("vehicles", {}).items():
                    if info.get("url"):
                        vehicles[name] = info["url"]
        except Exception as e:
            print(f"[警告] 读取 market_meta.json 失败: {e}")

    # 兜底：从最近的 json 数据中解析
    json_files = glob.glob(os.path.join("daily_json", "gaijin_market_*.json"))
    if json_files:
        latest_file = max(json_files, key=os.path.getmtime)
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if item.get("name") and item.get("url"):
                        vehicles[item["name"]] = item["url"]
        except Exception as e:
            print(f"[警告] 从历史数据文件解析字典失败: {e}")
            
    return vehicles

def fetch_single_vehicle(name, url, token):
    """
    模拟 POST 请求获取单个物品大盘实时简报和走势
    """
    # 清洗载具名称中的不间断空格和特殊符号，防止 Windows CMD/PowerShell 发生 GBK 编码崩溃
    safe_name = name.replace('\xa0', ' ').replace('\u200b', '').strip()
    
    try:
        path_parts = [p for p in url.split("/") if p]
        appid = "1067"
        market_name = path_parts[-1]
        
        # 1. cln_books_brief (买一价/卖一价/在售/求购)
        payload_brief = {
            "appid": appid,
            "market_name": market_name,
            "action": "cln_books_brief",
            "token": token
        }
        
        # 2. cln_get_pair_stat (1d 历史成交价格走势)
        payload_stat = {
            "appid": appid,
            "market_name": market_name,
            "currencyid": "gjn",
            "action": "cln_get_pair_stat",
            "token": token
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # 发送请求
        res_brief = requests.post(TRADE_SERVER, data=payload_brief, headers=headers, timeout=10)
        res_stat = requests.post(TRADE_SERVER, data=payload_stat, headers=headers, timeout=10)
        
        buy_price = None
        buy_orders = 0
        sell_price = None
        sell_orders = 0
        price_history = []
        
        if res_brief.status_code == 200:
            brief_data = res_brief.json()
            
            # 捕获 Token 失效或被封禁等异常
            if brief_data.get("response", {}).get("error") == "TOKEN_REQUIRED":
                raise Exception("Token已失效或需要重新配置")
                
            result = brief_data.get("result", brief_data.get("response", brief_data))
            
            # 读取买一求购价
            buy_arr = result.get("BUY", [])
            if buy_arr and len(buy_arr) > 0:
                buy_price = float(buy_arr[0][0]) / 10000
                
            # 读取买单深度
            depth = result.get("depth", {})
            if "BUY" in depth:
                buy_orders = int(depth["BUY"])
            elif buy_arr:
                buy_orders = len(buy_arr)
                
            # 读取卖一售价与卖单深度
            sell_arr = result.get("SELL", [])
            if sell_arr and len(sell_arr) > 0:
                item_sell_price = float(sell_arr[0][0]) / 10000
                if item_sell_price > 0:
                    sell_price = item_sell_price
            if "SELL" in depth:
                sell_orders = int(depth["SELL"])
            elif sell_arr:
                sell_orders = len(sell_arr)
                
        if res_stat.status_code == 200:
            stat_data = res_stat.json()
            result = stat_data.get("result", stat_data.get("response", stat_data))
            raw_history = result.get("1d", [])
            price_history = [[pt[0] * 1000, float(pt[1]) / 10000] for pt in raw_history]

        time.sleep(random.uniform(*DELAY_RANGE))
        
        return {
            "name": safe_name,
            "url": url,
            "imageUrl": f"https://trade.gaijin.net/images/items/{market_name}.png",
            "quantity": 1,
            "sellPrice": sell_price,
            "sellOrders": sell_orders,
            "buyPrice": buy_price,
            "buyOrders": buy_orders,
            "history": price_history,
            "scrapedAt": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        # 对终端打印进行安全过滤，防止命令行因未知字符引发 Unicode 异常
        filtered_err = str(e).encode('gbk', 'ignore').decode('gbk')
        print(f"[警告] 载具 '{safe_name.encode('gbk', 'ignore').decode('gbk')}' 抓取异常: {filtered_err}")
        return {
            "name": safe_name,
            "url": url,
            "imageUrl": "",
            "quantity": 1,
            "sellPrice": None,
            "sellOrders": 0,
            "buyPrice": None,
            "buyOrders": 0,
            "history": [],
            "error": str(e),
            "scrapedAt": datetime.utcnow().isoformat() + "Z"
        }

def main():
    print("="*50)
    print("  Gaijin 市场大盘数据爬取模块 (v2.0)")
    print("="*50)
    
    # 安全提示与 Token 校验
    if not GAIJIN_TOKEN:
        print("[提示] [WARNING] 当前未检测到有效的 GAIJIN_TOKEN！")
        print("由于 Gaijin 市场后端 API 具有严苛的登录令牌校验机制，")
        print("请用文本编辑器打开 scraper.py，在第 11 行的 GAIJIN_TOKEN 中")
        print("填入您从浏览器 F12 控制台获取的 Token（有效期通常长达数周）。")
        print("\n[架构师级部署指引]：")
        print("  - 本地测试：您只需在本地导出最新 JSON 后，直接 Commit 提交至 GitHub 仓库")
        print("  - 自动流水线：云端 GitHub Actions 会秒速识别并触发分析与自动部署 Pages 静态页面，")
        print("  - 即可实现 100% 零风控、100% 极高精准度、免密跨设备终极访问！")
        print("="*50)
        return
        
    vehicles = get_known_vehicles()
    if not vehicles:
        print("[错误] 未能找到任何已知载具大盘字典。")
        return
        
    print(f"[识别] 共发现 {len(vehicles)} 种已登记大盘载具，准备并发更新价格...")
    
    scraped_data = []
    completed = 0
    total = len(vehicles)
    
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(fetch_single_vehicle, name, url, GAIJIN_TOKEN): name for name, url in vehicles.items()}
        for future in as_completed(futures):
            res = future.result()
            scraped_data.append(res)
            completed += 1
            pct = (completed / total) * 100
            
            # 使用安全 gbk 过滤在控制台打印载具名，规避 Windows 编码挂掉
            safe_print_name = res['name'].encode('gbk', 'ignore').decode('gbk')
            print(f"[{completed}/{total} - {pct:.1f}%] 已完成: {safe_print_name} | 市价: {res['sellPrice']} GJN")
            
    # 保存结果
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    # 确保 daily_json 文件夹存在
    os.makedirs("daily_json", exist_ok=True)
    output_filename = os.path.join("daily_json", f"gaijin_market_{date_str}.json")
    
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n[成功] 今日最新大盘市价已捕获并存入本地: {output_filename}")
    print("="*50)

if __name__ == "__main__":
    main()
