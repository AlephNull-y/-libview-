# -*- coding: utf-8 -*-
"""
V3 优化论证脚本：证明「8 片 × 12 组 = 4 相位 × 2 子状态」，从而说明 COLOR 表可以整张删掉。

做三件事：
1. 读基准表 完整灯态逐秒表.csv，统计 96 格里有几格是 0、有几列其实是同一张图样；
2. 用「每组灯只归属一个相位 + 片号奇偶决定绿/黄」这个模型，重新算出 175 秒 × 12 组，
   和基准表逐值比对（等价性证明）；
3. 输出 V3 译码对照表 CSV（12 组 × 归属片号/绿条件/黄条件/红条件），供搭建时照抄。

用法：python verify_phase_model.py
"""
import sys, os, csv
from collections import OrderedDict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
LABVIEW = os.path.dirname(HERE)

GROUPS = ["MV_NS_TH", "MV_NS_LT", "MV_EW_TH", "MV_EW_LT",
          "BK_NS_TH", "BK_NS_LT", "BK_EW_TH", "BK_EW_LT",
          "PW_N", "PW_S", "PW_E", "PW_W"]

# 模型：每组的「绿灯片号」（0 基）；黄灯只对机动车存在，且永远紧跟其绿灯片
GREEN_SLICE = {
    "MV_NS_TH": 0, "MV_NS_LT": 2, "MV_EW_TH": 4, "MV_EW_LT": 6,
    "BK_NS_TH": 0, "BK_NS_LT": 2, "BK_EW_TH": 4, "BK_EW_LT": 6,
    "PW_N": 4, "PW_S": 4, "PW_E": 0, "PW_W": 0,
}
HAS_YELLOW = set(GROUPS[:4])          # 只有 4 个机动车组有黄灯


def find_csv(name):
    for d in (LABVIEW, HERE, os.path.join(LABVIEW, "V2-功能实现")):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def main():
    path = find_csv("完整灯态逐秒表.csv")
    if not path:
        print("[错误] 找不到 完整灯态逐秒表.csv")
        return 2
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    print(f"基准表：{path}")
    print(f"共 {len(rows)} 行（{len(rows) and rows[0]['周期内秒t']}~{rows[-1]['周期内秒t']} 秒）")

    # ---------- 1. 表格「含金量」统计 ----------
    table = {}                                  # (slice, group) -> value
    for r in rows:
        s = int(r["片号"]) - 1
        for g in GROUPS:
            table[(s, g)] = int(r[g + "数值"])
    cells = len(table)
    zeros = sum(1 for v in table.values() if v == 0)
    ones = sum(1 for v in table.values() if v == 1)
    twos = sum(1 for v in table.values() if v == 2)
    print(f"\n[1] 96 格构成：{cells} 格，其中 0 有 {zeros} 格（{zeros/cells:.1%}）、"
          f"1 有 {ones} 格、2 有 {twos} 格")
    print(f"    非零格只有 {ones + twos} 格 —— 表里 {zeros/cells:.0%} 是填充的 0。")

    # 12 列里有几种「不同的 8 位图样」
    patterns = OrderedDict()
    for g in GROUPS:
        pat = tuple(table[(s, g)] for s in range(8))
        patterns.setdefault(pat, []).append(g)
    print(f"    12 列其实只有 {len(patterns)} 种不同的图样：")
    for pat, gs in patterns.items():
        print(f"      {' '.join(str(v) for v in pat)}   →  {'、'.join(gs)}")

    # ---------- 2. 用相位模型重算，与基准逐值比对 ----------
    bad = []
    for r in rows:
        s = int(r["片号"]) - 1
        for g in GROUPS:
            k = GREEN_SLICE[g]
            if s == k:
                exp = 1
            elif s == k + 1 and g in HAS_YELLOW:
                exp = 2
            else:
                exp = 0
            got = int(r[g + "数值"])
            if got != exp:
                bad.append((r["周期内秒t"], g, got, exp))
    total = len(rows) * len(GROUPS)
    print(f"\n[2] 用「归属片号 + 奇偶黄灯」模型重算：{total} 个值（{len(rows)} 秒 × 12 组）")
    if bad:
        print(f"    [不一致] {len(bad)} 处，前 10 条：")
        for t, g, got, exp in bad[:10]:
            print(f"      t={t} {g}: 表中 {got}，模型 {exp}")
    else:
        print(f"    [通过] 全部一致 —— 96 格表可以用「12 个归属片号 + 1 条奇偶规则」完全替代。")

    # 每组的「非零片号」是否真的都落在同一相位对里
    print("\n[3] 每组非零出现在哪些片（0 基）：")
    for g in GROUPS:
        s_list = [s for s in range(8) if table[(s, g)] != 0]
        kind = "红/绿两态" if g not in HAS_YELLOW else "红/黄/绿三态"
        print(f"    {g:<9} 片 {s_list}   {kind}")

    # ---------- 3. 输出 V3 译码对照表 ----------
    header = ["灯组", "几态", "归属片号(1基)", "归属相位", "绿灯条件", "黄灯条件", "红灯条件"]
    rows_out = []
    for g in GROUPS:
        k = GREEN_SLICE[g]
        if g in HAS_YELLOW:
            rows_out.append([g, "红黄绿", k + 1, f"相位{k//2 + 1}",
                             f"i = {k}", f"i = {k+1}", f"i ≠ {k} 且 i ≠ {k+1}"])
        else:
            rows_out.append([g, "红绿", k + 1, f"相位{k//2 + 1}",
                             f"i = {k}", "无黄灯", f"i ≠ {k}"])

    out = os.path.join(HERE, "V3译码对照表.csv")
    try:
        with open(out, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows_out)
        print(f"\n[输出] V3 译码对照表 → {out}")
    except PermissionError:
        print(f"\n[提示] 写不进 {out}（文件被占用或当前环境只读），下面是同一张表：")
        print("  " + " | ".join(header))
        for r in rows_out:
            print("  " + " | ".join(str(x) for x in r))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
