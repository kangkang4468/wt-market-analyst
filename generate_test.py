import json
from datetime import datetime, timedelta

def generate_growing_history(start_price, days_count, end_date):
    history = []
    base_time = end_date - timedelta(days=days_count)
    current_price = start_price
    for i in range(days_count):
        current_price *= 1.002
        timestamp_ms = int((base_time + timedelta(days=i)).timestamp() * 1000)
        history.append([timestamp_ms, round(current_price, 2)])
    return history

def generate_crash_history(start_price, days_count, end_date):
    history = []
    base_time = end_date - timedelta(days=days_count)
    current_price = start_price
    for i in range(days_count):
        day_offset = days_count - i
        if day_offset == 20:
            current_price = start_price * 0.65  # 跌幅 35%
        else:
            current_price *= 0.999
        timestamp_ms = int((base_time + timedelta(days=i)).timestamp() * 1000)
        history.append([timestamp_ms, round(current_price, 2)])
    return history

def main():
    # 模拟三个不同日期的市场快照，用于测试历史回溯与大盘变动比对
    dates = [
        datetime(2026, 5, 20),
        datetime(2026, 5, 21),
        datetime(2026, 5, 22)
    ]
    
    # 定义测试物品数据在三个快照中的状态变化
    snapshot_data = {
        0: [  # 2026-05-20 快照
            {
                "name": "A-1H (美国)",
                "url": "https://trade.gaijin.net/market/1067/id50190_a_1h_usa",
                "imageUrl": "https://static-ggc.gaijin.net/units/us_a_1h.png",
                "quantity": 1,
                "sellPrice": 75.0,
                "sellOrders": 5,
                "buyPrice": 70.0,
                "buyOrders": 45,
                "history": generate_growing_history(61.0, 90, dates[0]),
                "scrapedAt": dates[0].isoformat()
            },
            {
                "name": "292 工程 (苏联)",
                "url": "https://trade.gaijin.net/market/1067/id50257_object_292_ussr",
                "imageUrl": "https://static-ggc.gaijin.net/units/ussr_object_292.png",
                "quantity": 1,
                "sellPrice": 70.0,
                "sellOrders": 42,
                "buyPrice": 65.0,
                "buyOrders": 100,
                "history": generate_crash_history(105.0, 90, dates[0]),
                "scrapedAt": dates[0].isoformat()
            },
            {
                "name": "T-80U-M1 (苏联)",
                "url": "https://trade.gaijin.net/market/1067/id50201_t_80u_m1_ussr",
                "imageUrl": "https://static-ggc.gaijin.net/units/ussr_t_80u_m1.png",
                "quantity": 1,
                "sellPrice": 42.0,
                "sellOrders": 140,
                "buyPrice": 32.0,
                "buyOrders": 8,
                "history": generate_growing_history(43.0, 60, dates[0]),
                "scrapedAt": dates[0].isoformat()
            },
            {
                "name": "模拟下架载具 (德国)",
                "url": "https://trade.gaijin.net/market/1067/id50000_german_test_item",
                "imageUrl": "",
                "quantity": 1,
                "sellPrice": 10.0,
                "sellOrders": 1,
                "buyPrice": 9.0,
                "buyOrders": 2,
                "history": generate_growing_history(9.0, 30, dates[0]),
                "scrapedAt": dates[0].isoformat()
            }
        ],
        1: [  # 2026-05-21 快照
            {
                "name": "A-1H (美国)",
                "url": "https://trade.gaijin.net/market/1067/id50190_a_1h_usa",
                "imageUrl": "https://static-ggc.gaijin.net/units/us_a_1h.png",
                "quantity": 1,
                "sellPrice": 77.0,
                "sellOrders": 4,
                "buyPrice": 72.0,
                "buyOrders": 48,
                "history": generate_growing_history(63.0, 90, dates[1]),
                "scrapedAt": dates[1].isoformat()
            },
            {
                "name": "292 工程 (苏联)",
                "url": "https://trade.gaijin.net/market/1067/id50257_object_292_ussr",
                "imageUrl": "https://static-ggc.gaijin.net/units/ussr_object_292.png",
                "quantity": 1,
                "sellPrice": 68.0,
                "sellOrders": 43,
                "buyPrice": 62.0,
                "buyOrders": 110,
                "history": generate_crash_history(102.0, 90, dates[1]),
                "scrapedAt": dates[1].isoformat()
            },
            {
                "name": "T-80U-M1 (苏联)",
                "url": "https://trade.gaijin.net/market/1067/id50201_t_80u_m1_ussr",
                "imageUrl": "https://static-ggc.gaijin.net/units/ussr_t_80u_m1.png",
                "quantity": 1,
                "sellPrice": 43.5,
                "sellOrders": 145,
                "buyPrice": 33.5,
                "buyOrders": 9,
                "history": generate_growing_history(44.5, 60, dates[1]),
                "scrapedAt": dates[1].isoformat()
            },
            {
                "name": "F-14A IRIAF (美国)",
                "url": "https://trade.gaijin.net/market/1067/id50311_f_14a_iriaf",
                "imageUrl": "https://static-ggc.gaijin.net/units/us_f_14a_iriaf.png",
                "quantity": 1,
                "sellPrice": 78.0,
                "sellOrders": 28,
                "buyPrice": 68.0,
                "buyOrders": 12,
                "history": generate_growing_history(76.0, 45, dates[1]),
                "scrapedAt": dates[1].isoformat()
            }
            # "模拟下架载具" 在本期下架消失了
        ],
        2: [  # 2026-05-22 快照
            {
                "name": "A-1H (美国)",
                "url": "https://trade.gaijin.net/market/1067/id50190_a_1h_usa",
                "imageUrl": "https://static-ggc.gaijin.net/units/us_a_1h.png",
                "quantity": 1,
                "sellPrice": 79.0,
                "sellOrders": 3,
                "buyPrice": 75.0,
                "buyOrders": 50,
                "history": generate_growing_history(65.0, 90, dates[2]),
                "scrapedAt": dates[2].isoformat()
            },
            {
                "name": "292 工程 (苏联)",
                "url": "https://trade.gaijin.net/market/1067/id50257_object_292_ussr",
                "imageUrl": "https://static-ggc.gaijin.net/units/ussr_object_292.png",
                "quantity": 1,
                "sellPrice": 65.0,
                "sellOrders": 45,
                "buyPrice": 60.0,
                "buyOrders": 120,
                "history": generate_crash_history(100.0, 90, dates[2]),
                "scrapedAt": dates[2].isoformat()
            },
            {
                "name": "T-80U-M1 (苏联)",
                "url": "https://trade.gaijin.net/market/1067/id50201_t_80u_m1_ussr",
                "imageUrl": "https://static-ggc.gaijin.net/units/ussr_t_80u_m1.png",
                "quantity": 1,
                "sellPrice": 45.0,
                "sellOrders": 150,
                "buyPrice": 35.0,
                "buyOrders": 10,
                "history": generate_growing_history(46.0, 60, dates[2]),
                "scrapedAt": dates[2].isoformat()
            },
            {
                "name": "F-14A IRIAF (美国)",
                "url": "https://trade.gaijin.net/market/1067/id50311_f_14a_iriaf",
                "imageUrl": "https://static-ggc.gaijin.net/units/us_f_14a_iriaf.png",
                "quantity": 1,
                "sellPrice": 80.0,
                "sellOrders": 25,
                "buyPrice": 70.0,
                "buyOrders": 15,
                "history": generate_growing_history(78.0, 45, dates[2]),
                "scrapedAt": dates[2].isoformat()
            }
        ]
    }

    for idx, date in enumerate(dates):
        date_str = date.strftime('%Y-%m-%d')
        filename = f"gaijin_market_{date_str}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(snapshot_data[idx], f, ensure_ascii=False, indent=4)
        print(f"Successfully generated {filename}")

if __name__ == "__main__":
    main()
