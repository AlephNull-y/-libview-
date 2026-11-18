# -*- coding: utf-8 -*-
"""生成开发报告用的插图（Pillow，无 matplotlib 依赖）。"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "figures")
os.makedirs(OUT, exist_ok=True)

FONT = r"C:\Windows\Fonts\simhei.ttf"
def F(sz):
    return ImageFont.truetype(FONT, sz)

INK = (33, 37, 41)
GREY = (240, 242, 245)
LINE = (120, 126, 134)
GREEN = (32, 170, 80)
YELLOW = (240, 190, 40)
RED = (225, 70, 70)
BLUE = (58, 110, 200)
WHITE = (255, 255, 255)


def arrow(d, x1, y1, x2, y2, w=3, color=LINE):
    d.line((x1, y1, x2, y2), fill=color, width=w)
    # 箭头三角
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    L, sp = 14, 0.38
    p1 = (x2 - L * math.cos(ang - sp), y2 - L * math.sin(ang - sp))
    p2 = (x2 - L * math.cos(ang + sp), y2 - L * math.sin(ang + sp))
    d.polygon([(x2, y2), p1, p2], fill=color)


# ---------------- 图 1：系统分层结构 ----------------
def fig1():
    W, H = 1180, 790
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    layers = [
        ("数据层：DUR[8] 片长表、END[8] 片终点、NAME[8] 片名、CYCLE=175",
         "只填 8+8+8+1 个数值；与配时脚本生成的 CSV 一致", (232, 240, 254)),
        ("时序层：状态机 (i, sec)  ——  片号推进 + 片内秒计数",
         "索引 DUR 取片长 → 比较 sec+1 ≥ DUR[i] → 选择写入下一状态", (232, 248, 236)),
        ("译码层：最小项译码  E0…E7  =  (i == 0…7)",
         "8 个等于? + 4 个或 + 8 个非  →  28 个布尔", (255, 247, 224)),
        ("显示层：页② 28 只单灯  /  页① 20 个实体灯头  /  页③ 参数与证据",
         "t_s、remain_s、slice_name、loop_count、cycle_no", (250, 232, 232)),
    ]
    y = 36
    for i, (title, sub, color) in enumerate(layers):
        box_h = 118
        d.rounded_rectangle((60, y, W - 60, y + box_h), radius=12, fill=color, outline=LINE, width=2)
        d.text((90, y + 22), title, font=F(24), fill=INK)
        d.text((90, y + 66), sub, font=F(19), fill=(80, 84, 90))
        if i < len(layers) - 1:
            arrow(d, W // 2, y + box_h + 6, W // 2, y + box_h + 44)
        y += box_h + 50

    d.text((60, H - 44), "注：任意一层出错都会表现为“某些灯不按预期变化”，而四层的故障特征不同（数据错／时序错／译码错／接线错）。",
           font=F(18), fill=(90, 94, 100))
    img.save(os.path.join(OUT, "fig1_architecture.png"))


# ---------------- 图 2：状态矩阵稀疏性热力图 ----------------
GROUPS = ["MV_NS_TH", "MV_NS_LT", "MV_EW_TH", "MV_EW_LT",
          "BK_NS_TH", "BK_NS_LT", "BK_EW_TH", "BK_EW_LT",
          "PW_N", "PW_S", "PW_E", "PW_W"]
TABLE = [
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1],
    [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0],
    [0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
    [0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0],
]
SLICE = ["片1", "片2", "片3", "片4", "片5", "片6", "片7", "片8"]


def fig2():
    cw, ch = 62, 56
    left, top = 130, 76
    W = left + cw * 12 + 80
    H = top + ch * 8 + 180
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    for j, g in enumerate(GROUPS):
        d.text((left + j * cw + 4, top - 62), f"{j+1}", font=F(20), fill=INK)
    d.text((left + 12 * cw + 8, top - 62), "列", font=F(18), fill=LINE)

    for i in range(8):
        d.text((52, top + i * ch + 14), SLICE[i], font=F(22), fill=INK)
        for j in range(12):
            v = TABLE[i][j]
            fill = (238, 240, 243) if v == 0 else (GREEN if v == 1 else YELLOW)
            x0, y0 = left + j * cw, top + i * ch
            d.rectangle((x0, y0, x0 + cw - 3, y0 + ch - 3), fill=fill, outline=WHITE, width=2)
            if v:
                d.text((x0 + 20, y0 + 14), str(v), font=F(22), fill=WHITE)

    # 图例
    ly = top + ch * 8 + 26
    d.rectangle((60, ly, 100, ly + 30), fill=(238, 240, 243), outline=LINE)
    d.text((112, ly + 2), "0 = 红（80 格，83.3%）", font=F(20), fill=INK)
    d.rectangle((420, ly, 460, ly + 30), fill=GREEN, outline=LINE)
    d.text((472, ly + 2), "1 = 绿（12 格）", font=F(20), fill=INK)
    d.rectangle((660, ly, 700, ly + 30), fill=YELLOW, outline=LINE)
    d.text((712, ly + 2), "2 = 黄（4 格）", font=F(20), fill=INK)

    # 列名对照（两行）
    d.text((60, ly + 50), "列名：" + "  ".join(f"{i+1}={g}" for i, g in enumerate(GROUPS[:6])), font=F(18), fill=(80, 84, 90))
    d.text((60, ly + 80), "　　　" + "  ".join(f"{i+7}={g}" for i, g in enumerate(GROUPS[6:])), font=F(18), fill=(80, 84, 90))
    img.save(os.path.join(OUT, "fig2_matrix.png"))


# ---------------- 图 3：配时时间轴 ----------------
DUR = [46, 4, 26, 4, 60, 5, 25, 5]
NAMES = ["南北直行绿", "南北直行黄", "南北左转绿", "南北左转黄",
         "东西直行绿", "东西直行黄", "东西左转绿", "东西左转黄"]


def fig3():
    W, H = 1320, 400
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    x0, x1, ybar = 90, W - 60, 40
    scale = (x1 - x0) / 175.0
    t = 0
    for k, dur in enumerate(DUR):
        xa = x0 + t * scale
        xb = x0 + (t + dur) * scale
        color = GREEN if k % 2 == 0 else YELLOW
        d.rectangle((xa, ybar, xb, ybar + 74), fill=color, outline=WHITE, width=2)
        if dur >= 20:
            d.text((xa + 12, ybar + 24), f"片{k+1} {dur}s", font=F(22), fill=WHITE)
        t += dur
    # 时间刻度
    for tt in range(0, 176, 25):
        xx = x0 + tt * scale
        d.line((xx, ybar + 80, xx, ybar + 96), fill=LINE, width=2)
        d.text((xx - 14, ybar + 100), str(tt), font=F(18), fill=INK)
    d.text((x1 - 26, ybar + 130), "t / s", font=F(18), fill=INK)

    # 片号与名称
    y = ybar + 170
    t = 0
    for k, dur in enumerate(DUR):
        xa = x0 + t * scale
        d.line((xa, ybar + 74, xa, y), fill=(200, 204, 210), width=1)
        d.text((xa + 4, y - 4 + (k % 2) * 26), f"片{k+1}", font=F(17), fill=INK)
        t += dur

    y2 = y + 96
    d.text((60, y2), "绿信比（绿灯时长 / 周期）：南北直行 46/175 = 26.3%　南北左转 26/175 = 14.9%",
           font=F(19), fill=(80, 84, 90))
    d.text((60, y2 + 32), "东西直行 60/175 = 34.3%　东西左转 25/175 = 14.3%　黄灯合计 18/175 = 10.3%",
           font=F(19), fill=(80, 84, 90))
    img.save(os.path.join(OUT, "fig3_timeline.png"))


# ---------------- 图 4：状态转移图 ----------------
import math


def fig4():
    W, H = 1020, 860
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    cx, cy, R = W // 2, 400, 235
    pts = []
    for k in range(8):
        a = -math.pi / 2 + k * 2 * math.pi / 8
        pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))

    # 先画边
    for k in range(8):
        x1, y1 = pts[k]
        x2, y2 = pts[(k + 1) % 8]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        r = 54
        sx, sy = x1 + ux * r, y1 + uy * r
        ex, ey = x2 - ux * r, y2 - uy * r
        arrow(d, sx, sy, ex, ey, w=3, color=(150, 155, 162))

        # 标签放在中点、沿径向往外挪，避免压住节点
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        ox, oy = mx - cx, my - cy
        ol = math.hypot(ox, oy) or 1
        lx, ly = mx + ox / ol * 44, my + oy / ol * 44
        lab = f"sec+1 ≥ {DUR[k]}"
        tw = d.textlength(lab, font=F(16))
        d.text((lx - tw / 2, ly - 10), lab, font=F(16), fill=(70, 74, 80))

    # 再画状态
    for k, (x, y) in enumerate(pts):
        r = 54
        color = GREEN if k % 2 == 0 else YELLOW
        d.ellipse((x - r, y - r, x + r, y + r), fill=color, outline=INK, width=2)
        d.text((x - 22, y - 26), f"片{k+1}", font=F(22), fill=WHITE)
        d.text((x - 24, y + 2), f"{DUR[k]}s", font=F(18), fill=WHITE)

    yt = H - 110
    d.text((40, yt), "初始状态：片1（sec = 0）。每拍先算 sec+1：未达片长则留在本状态（sec ← sec+1），",
           font=F(18), fill=(80, 84, 90))
    d.text((40, yt + 30), "达到片长则沿环推进到下一片并令 sec ← 0；片8 推进后回到片1，构成 175 s 周期。",
           font=F(18), fill=(80, 84, 90))
    d.text((40, yt + 60), "状态寄存器 = 两个整型移位寄存器；次态逻辑 = 7 个基础算子；输出译码 = 8 个最小项。",
           font=F(18), fill=(80, 84, 90))
    img.save(os.path.join(OUT, "fig4_fsm.png"))


fig1(); fig2(); fig3(); fig4()
print("figures written to", OUT)
for f in sorted(os.listdir(OUT)):
    print("  ", f, os.path.getsize(os.path.join(OUT, f)), "bytes")
