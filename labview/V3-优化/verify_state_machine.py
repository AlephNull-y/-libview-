# -*- coding: utf-8 -*-
"""
V3.2（状态机版）的等价性验证（不用 LabVIEW，先在 Python 里把状态机跑一遍）。

模型：
    状态 = (i, sec)      i = 片号 0…7，sec = 本片已过秒数
    时长表 DUR = [46, 4, 26, 4, 60, 5, 25, 5]
    每拍：
        n      = DUR[i]
        sec+1 >= n  →（i+1, 0）
        否则        →（i, sec+1）
    派生显示：t = START[i] + sec，remain = DUR[i] - sec

跑 175 拍，把 (t, 片号, 12 组灯态, remain) 与 完整灯态逐秒表.csv 逐值比对。
另外打印状态转移表，供《操作报告-V3.md》阶段 F 照抄。

用法：python verify_state_machine.py
"""
import sys, os, csv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
LABVIEW = os.path.dirname(HERE)

START = [0, 46, 50, 76, 80, 140, 145, 170]
DUR = [46, 4, 26, 4, 60, 5, 25, 5]
CYCLE = sum(DUR)

GROUPS = ["MV_NS_TH", "MV_NS_LT", "MV_EW_TH", "MV_EW_LT",
          "BK_NS_TH", "BK_NS_LT", "BK_EW_TH", "BK_EW_LT",
          "PW_N", "PW_S", "PW_E", "PW_W"]
GREEN_SLICE = {"MV_NS_TH": 0, "MV_NS_LT": 2, "MV_EW_TH": 4, "MV_EW_LT": 6,
               "BK_NS_TH": 0, "BK_NS_LT": 2, "BK_EW_TH": 4, "BK_EW_LT": 6,
               "PW_N": 4, "PW_S": 4, "PW_E": 0, "PW_W": 0}
HAS_YELLOW = set(GROUPS[:4])


def lamp(s, g):
    k = GREEN_SLICE[g]
    if s == k:
        return 1
    if s == k + 1 and g in HAS_YELLOW:
        return 2
    return 0


def run_states(cycles=1):
    """按状态机推进，逐拍产出 (t, i, sec)。"""
    i, sec = 0, 0
    out = []
    for _ in range(CYCLE * cycles):
        out.append((START[i] + sec, i, sec))
        nxt = sec + 1
        if nxt >= DUR[i]:
            i, sec = (i + 1) % 8, 0
        else:
            sec = nxt
    return out


def find_csv(name):
    for d in (LABVIEW, HERE, os.path.join(LABVIEW, "V2-功能实现")):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def main():
    print(f"周期 = {CYCLE} s，时长表 DUR = {DUR}")
    assert START[0] == 0 and all(sum(DUR[:k]) == START[k] for k in range(8)), "DUR 与 START 不自洽"
    print("自洽性检查：START[k] == sum(DUR[:k]) 全部成立 ✓")

    print("\n=== 状态转移表（照这张表接 7 个节点）===")
    print(" 当前片  时长  当前秒 sec=0…n-1   sec+1 ≥ n ?   次态")
    for k in range(8):
        print(f"  片{k+1}    {DUR[k]:>2}   0…{DUR[k]-1:<2}          "
              f"{'是' if DUR[k] == 1 else '只有 sec=' + str(DUR[k]-1) + ' 时为是':<12} "
              f"片{(k+1) % 8 + 1}")

    # ---- 等价性：状态机 vs 基准逐秒表 ----
    csv_path = find_csv("完整灯态逐秒表.csv")
    if not csv_path:
        print("\n[错误] 找不到 完整灯态逐秒表.csv")
        return 2
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
    states = run_states()
    print(f"\n基准表：{csv_path}（{len(rows)} 行）")
    print(f"状态机跑出：{len(states)} 拍")

    bad = []
    for (t_sm, i, sec), row in zip(states, rows):
        t_csv = int(row["周期内秒t"])
        slice_csv = int(row["片号"]) - 1
        remain_csv = int(row["本片剩余s"])
        if t_sm != t_csv:
            bad.append((t_csv, "t", t_sm, t_csv))
        if i != slice_csv:
            bad.append((t_csv, "片号", i + 1, slice_csv + 1))
        if DUR[i] - sec != remain_csv:
            bad.append((t_csv, "remain", DUR[i] - sec, remain_csv))
        for g in GROUPS:
            if lamp(i, g) != int(row[g + "数值"]):
                bad.append((t_csv, g, lamp(i, g), int(row[g + "数值"])))

    print(f"\n=== 逐值比对：{len(rows)} 秒 × (t + 片号 + remain + 12 灯) ===")
    if bad:
        print(f"[不一致] {len(bad)} 处，前 10 条：")
        for t, what, got, exp in bad[:10]:
            print(f"  t={t} {what}: 状态机 {got}，基准 {exp}")
        return 1
    total = len(rows) * (3 + len(GROUPS))
    print(f"[通过] {total} 个值全部一致 —— 状态机方案与 V3.1 查表方案**逐秒等价**。")

    print("\n=== 抽取：3 个切换边界（最容易错的地方）===")
    for k in (0, 1, 4):
        t_edge = START[k] + DUR[k]
        s_before = states[t_edge - 1]
        s_after = states[t_edge] if t_edge < len(states) else None
        print(f"  片{k+1}→片{k+2} 边界 t={t_edge}: "
              f"前一拍 (t={s_before[0]}, 片{s_before[1]+1}, sec={s_before[2]}) → "
              f"本拍 (t={s_after[0]}, 片{s_after[1]+1}, sec={s_after[2]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
