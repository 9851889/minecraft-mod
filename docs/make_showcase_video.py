# -*- coding: utf-8 -*-
"""飞行鞋 (Flying Shoe) 展示短片渲染器。

用 Pillow 逐帧绘制像素风格的宣传动画，输出 PNG 帧序列，
再由 encode_video.py 编码为 MP4 / GIF / WebP。

同时导出游戏内实际使用的 16x16 物品贴图，保证视频与游戏美术一致。

注意：ImageDraw 直接绘制会覆盖 alpha 通道，所有半透明元素一律先画在
独立图层上再 alpha_composite 回主画布，否则转 RGB 时会变成实心色块。
"""
import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
FRAMES = os.path.join(HERE, "frames")

W, H = 640, 360
FPS = 20
DURATION = 14.0
TOTAL = int(FPS * DURATION)

FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"

# ---------------------------------------------------------------- 调色板
PAL = {
    "k": (43, 31, 18, 255),      # 深描边
    "b": (139, 90, 43, 255),      # 皮革中间色
    "B": (185, 121, 63, 255),     # 皮革亮部
    "m": (93, 58, 23, 255),       # 皮革暗部
    "w": (242, 247, 255, 255),    # 羽毛白
    "W": (176, 219, 255, 255),    # 羽毛浅蓝
    "c": (95, 212, 255, 255),     # 青色辉光
    "g": (255, 210, 74, 255),     # 金色
    "h": (226, 178, 122, 255),    # 皮肤
    "e": (60, 42, 29, 255),       # 眼睛
    "t": (47, 127, 208, 255),     # 衣服
    "p": (59, 74, 154, 255),      # 裤子
    "s": (90, 58, 30, 255),       # 鞋
    "G": (90, 170, 60, 255),      # 草
    "D": (134, 96, 67, 255),      # 土
    "n": (64, 56, 44, 255),       # 石头
}

# 16x16 物品贴图：带羽翼的战靴（同时用于游戏内 /item/flying_shoe.png）
BOOT = [
    "................",
    "..........wWw...",
    "........wWWwcc..",
    "......wWWwwc....",
    "....wWwwwc......",
    "..kkkkkk........",
    ".kBBBk..........",
    ".kBBBk..........",
    ".kBBBk..........",
    ".kBBk...........",
    ".kbbk...........",
    "kkkkk...........",
    "kmmmk...........",
    ".kkk............",
    "................",
    "................",
]

# 14x10 羽翼，三段拍翅姿态
WING_OPEN = [
    "..w..w..w.....",
    ".wwWWwWWw.....",
    "wWwwwwwwWw....",
    "wwwwwwwwwW....",
    ".wWwwwwwW.....",
    "..wWwwwW......",
    "...wWwW.......",
    "....wW........",
    "..............",
    "..............",
]
WING_MID = [
    "..............",
    "..w..w..w.....",
    ".wwWWwWWw.....",
    "wWwwwwwwWw....",
    "wwwwwwwwwW....",
    ".wWwwwwwW.....",
    "..wWwwwW......",
    "...wWwW.......",
    "....wW........",
    "..............",
]
WING_CLOSED = [
    "..............",
    "..............",
    "..............",
    "..w..w........",
    ".wwWWw........",
    "wWwwwwW.......",
    "wwwwwwwW......",
    ".wwwwwW.......",
    "..www.........",
    "..............",
]

# 8x16 玩家角色
PLAYER = [
    "..kkkk..",
    ".khhhhk.",
    ".khhehk.",
    ".khhhhk.",
    ".khhehk.",
    ".khhhhk.",
    "..kmmk..",
    ".kttttk.",
    ".kttttk.",
    ".kttttk.",
    ".kttttk.",
    "..pppp..",
    "..pppp..",
    "..p..p..",
    "..s..s..",
    "..s..s..",
]


# ---------------------------------------------------------------- 基础工具
def make_sprite(grid, scale=1, palette=None):
    pal = palette or PAL
    h, w = len(grid), len(grid[0])
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            c = pal.get(ch)
            if c:
                px[x, y] = c
    if scale != 1:
        im = im.resize((w * scale, h * scale), Image.NEAREST)
    return im


def overlay():
    """新建一个透明图层，用于绘制半透明元素。"""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return lay, ImageDraw.Draw(lay)


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_PATH, size)


def _draw_text(d, s, xy, size, color, bold, anchor, spacing):
    f = font(size, bold)
    if not spacing:
        d.text(xy, s, font=f, fill=color, anchor=anchor)
        return
    widths = [d.textlength(ch, font=f) for ch in s]
    total = sum(widths) + spacing * (len(s) - 1)
    if anchor[0] == "m":
        x = xy[0] - total / 2
    elif anchor[0] == "r":
        x = xy[0] - total
    else:
        x = xy[0]
    for ch, w in zip(s, widths):
        d.text((x, xy[1]), ch, font=f, fill=color, anchor="l" + anchor[1])
        x += w + spacing


def text(im, s, xy, size=16, color=(255, 255, 255), bold=False, anchor="lt", spacing=0, alpha=255):
    """带 alpha 安全的文字绘制（alpha<255 时走图层合成）。"""
    if alpha >= 255:
        _draw_text(ImageDraw.Draw(im), s, xy, size, color, bold, anchor, spacing)
        return
    lay, d = overlay()
    _draw_text(d, s, xy, size, color, bold, anchor, spacing)
    a = lay.split()[3].point(lambda v: int(v * alpha / 255))
    lay.putalpha(a)
    im.alpha_composite(lay)


def ring(im, cx, cy, r, color, width=3, alpha=220):
    lay, d = overlay()
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color + (alpha,), width=width)
    im.alpha_composite(lay)


def soft_glow(im, cx, cy, r, color, alpha=60, steps=9):
    lay, d = overlay()
    for i in range(steps, 0, -1):
        rr = r * i / steps
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=color + (int(alpha / steps * 1.6),))
    im.alpha_composite(lay)


# ---------------------------------------------------------------- 背景
def make_background():
    top = np.array([12, 16, 34], dtype=float)
    bot = np.array([42, 28, 66], dtype=float)
    ramp = np.linspace(0, 1, H)[:, None]
    arr = top[None, :] * (1 - ramp) + bot[None, :] * ramp
    arr = np.repeat(arr[:, None, :], W, axis=1)
    rng = np.random.default_rng(7)
    stars = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stars)
    for _ in range(110):
        x, y = rng.integers(0, W), rng.integers(0, int(H * 0.75))
        r = 0.6 if rng.random() < 0.85 else 1.3
        a = int(60 + rng.random() * 160)
        sd.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a))
    base = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    base.alpha_composite(stars.filter(ImageFilter.GaussianBlur(0.4)))
    return base


BG = make_background()


def sky(im, t):
    lay, bd = overlay()
    for col, amp, y0, ph in [
        ((60, 200, 255, 20), 26, 150, 0.0),
        ((150, 120, 255, 17), 34, 190, 1.7),
        ((255, 140, 220, 13), 22, 118, 3.1),
    ]:
        pts = [(x, y0 + math.sin(x / 90.0 + t * 0.35 + ph) * amp) for x in range(0, W + 8, 8)]
        bd.polygon(pts + [(W, H), (0, H)], fill=col)
    im.alpha_composite(lay)


def vignette(im, strength=105):
    yy, xx = np.mgrid[0:H, 0:W]
    dx = (xx - W / 2) / (W / 2)
    dy = (yy - H / 2) / (H / 2)
    r = np.sqrt(dx * dx + dy * dy) / 1.414
    mask = np.clip((r - 0.48) * strength, 0, 140).astype(np.uint8)
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dark.putalpha(Image.fromarray(mask))
    im.alpha_composite(dark)


def sweep_highlight(sprite, pos):
    w, h = sprite.size
    grad = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(grad)
    for x in range(w):
        gd.line([(x, 0), (x, h)], fill=int(255 * max(0.0, 1.0 - abs((x / w) - pos) * 7.0)))
    grad = grad.filter(ImageFilter.GaussianBlur(5))
    hl = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    hl.putalpha(Image.fromarray((np.array(grad) * 0.7).astype(np.uint8)))
    mask = sprite.split()[3]
    out = sprite.copy()
    out.alpha_composite(Image.composite(hl, Image.new("RGBA", (w, h), (0, 0, 0, 0)), mask))
    return out


# ---------------------------------------------------------------- 场景
def scene_item(im, t):
    """场景 A：物品亮相。"""
    t0, t1 = 0.0, 3.3
    p = (t - t0) / (t1 - t0)
    boot = make_sprite(BOOT, 7)
    bw, bh = boot.size
    bob = math.sin(t * 2.2) * 6
    cx, cy = W // 2, 124 + bob

    # 深色圆盘 + 青色描边，让靴子轮廓跳出背景
    lay, d = overlay()
    d.ellipse([cx - 104, cy - 104, cx + 104, cy + 104], fill=(8, 11, 26, 235))
    d.ellipse([cx - 104, cy - 104, cx + 104, cy + 104], outline=(95, 212, 255, 150), width=3)
    d.ellipse([cx - 116, cy - 116, cx + 116, cy + 116], outline=(95, 212, 255, 55), width=2)
    im.alpha_composite(lay)
    soft_glow(im, cx, cy, 150, (70, 175, 235), 52)

    d = ImageDraw.Draw(im)
    for i in range(3):
        rr = 78 + i * 24 + math.sin(t * 1.6 + i) * 5
        d.ellipse([cx - rr, 218 - rr * 0.15, cx + rr, 218 + rr * 0.15],
                  outline=(95, 212, 255, 40 - i * 10), width=2)

    spr = boot
    if 0.6 < p < 2.0:
        spr = sweep_highlight(boot, (t - 0.6) / 1.4)

    lay, d = overlay()
    for i in range(5):
        ang = t * 1.1 + i * math.tau / 5
        sx = cx + math.cos(ang) * 138
        sy = cy + math.sin(ang) * 86
        s = 2 if i % 2 else 3
        d.ellipse([sx - s, sy - s, sx + s, sy + s], fill=(220, 245, 255, 170))
    im.alpha_composite(lay)

    im.alpha_composite(spr, (int(cx - bw / 2), int(cy - bh / 2)))

    a_title = int(255 * min(1.0, max(0.0, (p - 0.22) * 2.4)))
    a_sub = int(255 * min(1.0, max(0.0, (p - 0.48) * 2.4)))
    text(im, "飞 行 鞋", (cx, 236), 46, (255, 255, 255), bold=True, anchor="mt", alpha=a_title)
    text(im, "F L Y I N G   S H O E", (cx, 292), 15, (95, 212, 255), anchor="mt", spacing=2, alpha=a_sub)
    text(im, "穿上即起飞 · 鞘翅式滑翔 · 落地无摔伤", (cx, 318), 15, (200, 212, 240), anchor="mt", alpha=a_sub)
    text(im, "Minecraft 1.20.4  ·  Fabric 模组  ·  v1.0.0", (16, H - 28), 13, (140, 152, 185))


def scene_equip(im, t):
    """场景 B：穿上鞋子，羽翼展开。"""
    t0, t1 = 3.3, 6.6
    p = (t - t0) / (t1 - t0)
    lay, d = overlay()
    d.rectangle([0, 262, W, H], fill=(32, 28, 40, 255))
    for x in range(0, W, 28):
        d.rectangle([x, 262, x + 13, 274], fill=(44, 38, 52, 255))
    d.line([(0, 262), (W, 262)], fill=(95, 212, 255, 70), width=2)
    im.alpha_composite(lay)

    cx = W // 2
    feet = 262
    pl = make_sprite(PLAYER, 6)
    im.alpha_composite(pl, (cx - pl.size[0] // 2, feet - pl.size[1]))

    boot = make_sprite(BOOT, 3)
    drop = int((1 - min(1.0, p / 0.45)) ** 2 * -150)
    im.alpha_composite(boot, (cx - 8, feet - 22 + drop))

    if p > 0.40:
        q = min(1.0, (p - 0.40) / 0.28)
        grid = WING_OPEN if q > 0.5 else WING_MID
        wing = make_sprite(grid, 5)
        wl = wing.transpose(Image.FLIP_LEFT_RIGHT)
        im.alpha_composite(wl, (cx - 30 - wl.size[0], feet - 108))
        im.alpha_composite(wing, (cx + 16, feet - 108))
        r = int(14 + 66 * (p - 0.40) / 0.5)
        if p < 0.92:
            ring(im, cx, feet - 92, r, (95, 212, 255), 3, int(210 * (1 - (p - 0.40) / 0.52)))

    a = int(255 * min(1.0, max(0.0, (p - 0.12) * 3)))
    text(im, "装备于靴子槽", (cx, 44), 30, (255, 255, 255), bold=True, anchor="mt", alpha=a)
    text(im, "穿上的瞬间，羽翼自动展开", (cx, 86), 15, (150, 210, 240), anchor="mt", alpha=a)
    text(im, "护甲值 +1   ·   耐久 200   ·   抗摔落", (cx, 110), 13, (145, 155, 188), anchor="mt", alpha=a)


def scene_glide(im, t):
    """场景 C：鞘翅式滑翔。"""
    t0, t1 = 6.6, 10.6
    p = (t - t0) / (t1 - t0)

    lay, d = overlay()
    rng = np.random.default_rng(3)
    for i in range(8):
        cx0 = int((rng.integers(0, W) - p * 110 * (0.5 + i * 0.12)) % (W + 260)) - 130
        cy0 = 22 + i * 14
        wdt = 46 + i * 8
        d.ellipse([cx0, cy0, cx0 + wdt, cy0 + 13], fill=(255, 255, 255, 20))
        d.ellipse([cx0 + 18, cy0 - 6, cx0 + wdt - 10, cy0 + 11], fill=(255, 255, 255, 20))
    im.alpha_composite(lay)

    # 远山
    far = 232
    lay, d = overlay()
    for i in range(18):
        x = int((i * 90 - (t - t0) * 22) % (W + 180)) - 90
        hgt = 26 + (i % 3) * 16
        d.polygon([(x, far), (x + 45, far - hgt), (x + 90, far)], fill=(44, 46, 78, 255))
        d.polygon([(x + 45, far - hgt), (x + 90, far), (x + 20, far)], fill=(52, 54, 90, 255))
    im.alpha_composite(lay)

    # 近景方块地形
    base = 272
    blocks = [(0, 1), (1, 0), (2, 2), (3, 1), (4, 0), (5, 3), (6, 1), (7, 0),
              (8, 2), (9, 1), (10, 0), (11, 2), (12, 1), (13, 0), (14, 1), (15, 0)]
    off = (t - t0) * 190
    lay, d = overlay()
    for k, (bx, bh) in enumerate(blocks):
        x = int(bx * 40 - off) % (len(blocks) * 40 * 4) - 160
        for c in range(8):
            xx = x + c * 40
            if xx < -40 or xx > W:
                continue
            top = base - bh * 12
            d.rectangle([xx, top, xx + 39, top + 11], fill=PAL["G"])
            d.rectangle([xx, top + 12, xx + 39, top + 39], fill=PAL["D"])
            if k % 5 == 2:
                d.rectangle([xx + 6, top - 16, xx + 14, top - 1], fill=(46, 92, 40, 255))
                d.rectangle([xx + 1, top - 12, xx + 19, top - 1], fill=(58, 120, 50, 255))
                d.rectangle([xx + 9, top - 1, xx + 11, top + 6], fill=(94, 62, 34, 255))
    d.rectangle([0, base + 28, W, H], fill=(28, 24, 34, 255))
    im.alpha_composite(lay)

    # 玩家展翅
    cx, cy = 238, 146 + math.sin(t * 2.0) * 5
    flap = int((t * 7) % 3)
    wing = make_sprite([WING_OPEN, WING_MID, WING_CLOSED][flap], 4)
    wl = wing.transpose(Image.FLIP_LEFT_RIGHT)
    wl = wl.rotate(20, resample=Image.NEAREST, expand=True)
    wr = wing.rotate(-20, resample=Image.NEAREST, expand=True)
    pl = make_sprite(PLAYER, 5).rotate(-14, resample=Image.NEAREST, expand=True)

    im.alpha_composite(wl, (int(cx - 30 - wl.size[0]), int(cy - 40)))
    im.alpha_composite(wr, (int(cx + 16), int(cy - 52)))
    im.alpha_composite(pl, (int(cx - pl.size[0] / 2), int(cy - 6)))

    lay, d = overlay()
    for i in range(8):
        y = 104 + i * 15
        ln = 44 + (i % 3) * 30
        x = int((t * 460 + i * 101) % (W + 220)) - 200
        d.line([(x, y), (x + ln, y)], fill=(255, 255, 255, 60), width=2)
    im.alpha_composite(lay)

    a = int(255 * min(1.0, p * 4))
    text(im, "鞘翅式滑翔", (24, 30), 32, (255, 255, 255), bold=True, alpha=a)
    text(im, "空中按住前进键加速，俯仰决定滑翔方向", (26, 70), 14, (150, 210, 240), alpha=a)
    text(im, "↑ 爬升      ↓ 俯冲", (26, 94), 13, (145, 155, 188), alpha=a)


def scene_land(im, t):
    """场景 D：落地无摔伤。"""
    t0, t1 = 10.6, 12.6
    p = (t - t0) / (t1 - t0)
    lay, d = overlay()
    d.rectangle([0, 268, W, H], fill=(32, 28, 40, 255))
    for x in range(0, W, 28):
        d.rectangle([x, 268, x + 13, 280], fill=(44, 38, 52, 255))
    d.line([(0, 268), (W, 268)], fill=(95, 212, 255, 65), width=2)
    im.alpha_composite(lay)

    drop = int((1 - min(1.0, p / 0.5)) ** 2 * -130)
    cx = W // 2
    feet = 268 + drop
    pl = make_sprite(PLAYER, 5)
    im.alpha_composite(pl, (cx - pl.size[0] // 2, feet - pl.size[1]))

    if p > 0.42:
        q = (p - 0.42) / 0.58
        ring(im, cx, feet - 46, int(14 + 74 * q), (95, 212, 255), 3, int(215 * (1 - q)))
        lay, d = overlay()
        for i in range(12):
            ang = i / 12 * math.tau
            rr = 20 + 50 * q
            x = cx + math.cos(ang) * rr
            y = feet - 46 + math.sin(ang) * rr * 0.45
            s = 3 if i % 2 == 0 else 2
            d.rectangle([x, y, x + s, y + s], fill=(150, 220, 255, int(215 * (1 - q))))
        im.alpha_composite(lay)

    hx, hy = cx - 66, 92
    lay, d = overlay()
    for i in range(10):
        x = hx + i * 14
        d.polygon([(x + 4, hy + 1), (x + 4, hy - 2), (x + 6, hy - 4), (x + 8, hy - 2),
                   (x + 8, hy + 1), (x + 6, hy + 4), (x + 4, hy + 1)], fill=(232, 78, 78, 255))
    im.alpha_composite(lay)

    a = int(255 * min(1.0, p * 4))
    text(im, "落地无摔伤", (cx, 28), 34, (255, 255, 255), bold=True, anchor="mt", alpha=a)
    text(im, "滑翔状态下完全免疫坠落伤害", (cx, 70), 15, (150, 210, 240), anchor="mt", alpha=a)


def scene_end(im, t):
    """场景 E：尾板。"""
    t0 = 12.6
    p = (t - t0) / (14.0 - t0)
    a = int(255 * min(1.0, p * 3))
    boot = make_sprite(BOOT, 6)
    im.alpha_composite(boot, (W // 2 - boot.size[0] // 2, 40))

    text(im, "飞 行 鞋", (W // 2, 150), 34, (255, 255, 255), bold=True, anchor="mt", alpha=a)
    text(im, "FLYING SHOE", (W // 2, 194), 13, (95, 212, 255), anchor="mt", spacing=3, alpha=a)

    lay, d = overlay()
    d.rounded_rectangle((W // 2 - 175, 226, W // 2 + 175, 258), radius=7,
                        fill=(14, 18, 38, 235), outline=(95, 212, 255, int(a * 0.75)), width=2)
    im.alpha_composite(lay)
    text(im, "/give @s flyingshoe:flying_shoe", (W // 2, 242), 15, (235, 240, 255), anchor="mm", alpha=a)
    text(im, "Minecraft 1.20.4   ·   Fabric   ·   星辉兽模组 v1.0.0", (W // 2, 276), 13,
         (145, 155, 188), anchor="mt", alpha=a)


SCENES = [(scene_item, 0.0, 3.3), (scene_equip, 3.3, 6.6), (scene_glide, 6.6, 10.6),
          (scene_land, 10.6, 12.6), (scene_end, 12.6, 14.0)]


def render():
    if os.path.isdir(FRAMES):
        for f in os.listdir(FRAMES):
            os.remove(os.path.join(FRAMES, f))
    else:
        os.makedirs(FRAMES)

    for i in range(TOTAL):
        t = i / FPS
        im = BG.copy()
        sky(im, t)
        for fn, a, b in SCENES:
            if a <= t < b:
                fn(im, t)
                break
        vignette(im)
        im.convert("RGB").save(os.path.join(FRAMES, "f%04d.png" % i))
    print("frames:", TOTAL, "->", FRAMES)


def export_item_textures():
    """把视频里的靴子导出为游戏内 16x16 物品贴图。"""
    root = os.path.join(PROJ, "src", "main", "resources", "assets", "flyingshoe", "textures")
    item_dir = os.path.join(root, "item")
    os.makedirs(item_dir, exist_ok=True)
    make_sprite(BOOT, 1).save(os.path.join(item_dir, "flying_shoe.png"))
    print("item texture ->", os.path.join(item_dir, "flying_shoe.png"))


if __name__ == "__main__":
    import sys
    export_item_textures()
    if "--textures-only" not in sys.argv:
        render()
