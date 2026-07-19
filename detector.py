"""
UniDebugger - 急减速异常检测模块
基于车速时序数据，自动识别校园无人车急减速异常事件。
"""

import csv
from pathlib import Path

# ========== 配置 ==========
CSV_FILE = "sample_speed.csv"       # 输入：车速数据
DECEL_THRESHOLD = 3.0               # 急减速阈值 (m/s²)
WINDOW_BEFORE = 10                  # 异常前截取秒数
WINDOW_AFTER = 10                   # 异常后截取秒数


def load_speed_data(path):
    """读取 CSV，要求列名包含 'timestamp' 和 'speed_kmh'"""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def detect_hard_brakes(rows):
    """
    遍历数据，按 (v₁² - v₀²) / (2·Δt) 近似减速度，
    超过阈值则记录异常事件。
    """
    events = []
    for i in range(1, len(rows)):
        t0, v0 = float(rows[i - 1]["timestamp"]), float(rows[i - 1]["speed_kmh"])
        t1, v1 = float(rows[i]["timestamp"]), float(rows[i]["speed_kmh"])
        dt = t1 - t0
        if dt <= 0 or v1 >= v0:
            continue  # 跳过非减速段

        decel = (v0 - v1) / (3.6 * dt)  # km/h → m/s
        if decel >= DECEL_THRESHOLD:
            start = max(0, i - WINDOW_BEFORE)
            end = min(len(rows), i + WINDOW_AFTER + 1)
            events.append({
                "trigger_index": i,
                "timestamp": rows[i]["timestamp"],
                "decel_m_s2": round(decel, 2),
                "speed_before_kmh": round(v0, 1),
                "speed_after_kmh": round(v1, 1),
                "snapshot": rows[start:end],
            })
    return events


def generate_sample_csv(path, seconds=120):
    """生成模拟车速 CSV（仅用于演示，实际数据来自车载黑匣子）"""
    import math
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "speed_kmh", "lat", "lng"])
        for t in range(seconds):
            # 模拟校园无人车：15 km/h 巡航 + 随机波动，穿插两次急刹
            v = 15 + 2 * math.sin(t / 5)
            if 25 < t < 28:      # 第一次急刹：电动车横穿
                v = max(0, v - (t - 25) * 5)
            if 70 < t < 73:      # 第二次急刹：学生突然冲出
                v = max(0, v - (t - 70) * 6)
            w.writerow([t, round(v, 1), "30.5123", "114.4156"])
    print(f"✅ 已生成模拟数据 → {path}")


# ========== 主流程 ==========
if __name__ == "__main__":
    if not Path(CSV_FILE).exists():
        generate_sample_csv(CSV_FILE)

    data = load_speed_data(CSV_FILE)
    events = detect_hard_brakes(data)

    print(f"共检测到 {len(events)} 次急减速异常：\n")
    for i, e in enumerate(events, 1):
        print(f"异常 #{i} | 时间 {e['timestamp']}s | "
              f"减速度 {e['decel_m_s2']} m/s² | "
              f"车速 {e['speed_before_kmh']}→{e['speed_after_kmh']} km/h")
    print("\n✅ 完成。实际接入ROS Bag或黑匣子CSV即可替换 sample_speed.csv。")
