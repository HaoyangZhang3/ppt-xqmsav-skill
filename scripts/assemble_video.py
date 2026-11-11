"""合成 AI 一镜到底变形转场成片。

功能:
  1. 按顺序拼接多段首尾帧变形视频
  2. 裁掉模型生成图角标("AI生成")并统一为 1280x720
  3. 段与段之间做交叉淡化,消除接缝跳变
  4. 叠加中文主标题与地标字幕

用法: python assemble_video.py <out.mp4> <seg1.mp4> [seg2.mp4 ...]
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
FPS = 24
XFADE = 10  # 交叉淡化帧数

FONT_CN = "C:/Windows/Fonts/msyhbd.ttc"
FONT_CN_L = "C:/Windows/Fonts/msyh.ttc"

# 字幕/标题配色主题(BGR)
ACCENTS = {
    "gold": {"main": (106, 190, 227), "sub": (120, 170, 195)},   # 香槟金 #E3BE6A / 淡金蓝
    "white": {"main": (255, 255, 255), "sub": (232, 232, 232)},
    "red": {"main": (235, 235, 245), "sub": (230, 230, 230)},
}
ACCENT = ACCENTS["gold"]

# 每段的地标字幕(中/英)
SUBTITLES = [
    ("北京校区主楼", "NCEPU MAIN BUILDING"),
    ("大礼堂 · 汽轮发电机转子", "AUDITORIUM · TURBINE ROTOR"),
    ("六十周年雕塑 · 校园水系", "ANNIVERSARY SCULPTURE · CAMPUS LAKE"),
    ("回到起点 · 一镜到底", "ONE-TAKE LOOP"),
]
TITLE = ("华北电力大学北京校区", "NCEPU BEIJING CAMPUS")


def load(path, crop_top_frac=0.085, crop_bottom_frac=0.065):
    """读入视频 -> 裁掉角标(视频在左上/静帧在右下)-> 等比缩放到 1280x720 的 BGR 帧列表。"""
    cap = cv2.VideoCapture(path)
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        top = int(h * crop_top_frac)
        bot = int(h * crop_bottom_frac)
        frame = frame[top: h - bot]
        # 裁完可能不是 16:9, 再从两侧补裁保持比例
        target = frame.shape[0] * W / H
        if frame.shape[1] > target:
            cw = int((frame.shape[1] - target) / 2)
            frame = frame[:, cw: cw + int(target)]
        else:
            th = int(frame.shape[1] * H / W)
            frame = frame[:th]
        frames.append(cv2.resize(frame, (W, H)))
    cap.release()
    return frames


def draw_text(frame_bgr, text, pos, size, color=(255, 255, 255), anchor="lt", alpha=1.0,
              panel=None):
    """在 BGR 帧上绘制中文/英文文本。panel=(pad, alpha) 时先铺深色衬底,保证浅色背景可读。"""
    img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_CN if size >= 30 else FONT_CN_L, size)
    x, y = pos
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    w, h = r - l, b - t
    if anchor == "rt":
        x -= w
    elif anchor == "mm":
        x -= w // 2
        y -= h // 2
    xy = (x - l, y - t)
    if panel:
        pad, pa = panel
        d.rectangle([xy[0] - pad, xy[1] - pad // 2, xy[0] + w + pad, xy[1] + h + pad // 2],
                    fill=(0, 0, 0, int(150 * pa)))
    d.text(xy, text, font=font, fill=color + (255,),
           stroke_width=max(3, size // 12), stroke_fill=(0, 0, 0, 255))
    out = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    if alpha < 1.0:
        out = cv2.addWeighted(out, alpha, frame_bgr, 1 - alpha, 0)
    return out


def fade(a, b, i, n):
    """i/n 混合两帧。"""
    return cv2.addWeighted(a, 1 - i / n, b, i / n, 0)


def main():
    global W, H, ACCENT
    args = sys.argv[1:]
    if "--w" in args:
        W = int(args[args.index("--w") + 1])
    if "--h" in args:
        H = int(args[args.index("--h") + 1])
    if "--accent" in args:
        ACCENT = ACCENTS[args[args.index("--accent") + 1]]
    segs = [a for a in args[1:] if a.endswith(".mp4")]
    if not segs:
        raise SystemExit(__doc__)
    out_path = args[0]
    print(f"输出尺寸 {W}x{H} / 配色 {args[args.index('--accent')+1] if '--accent' in args else 'gold'}")

    clips = [load(s) for s in segs]
    print("段数:", len(clips), "各段帧数:", [len(c) for c in clips])

    # 拼接:段间做交叉淡化
    seq = list(clips[0])
    for prev, nxt in zip(clips, clips[1:]):
        tail = seq[-XFADE:]
        head = nxt[:XFADE]
        blended = [fade(tail[i], head[i], i, XFADE) for i in range(XFADE)]
        seq = seq[:-XFADE] + blended + list(nxt[XFADE:])
    total = len(seq)
    print("成片帧数:", total, "时长:", total / FPS, "s")

    # 字幕:每段对应一组,按段在成片中的帧区间叠加
    bounds = []
    pos = 0
    for c in clips:
        bounds.append((pos, pos + len(c)))
        pos += len(c) - (XFADE if bounds[:-1] else 0)

    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for idx, frame in enumerate(seq):
        seg_idx = 0
        for i, (s, e) in enumerate(bounds):
            if s <= idx < e:
                seg_idx = i
                break
        s, e = bounds[seg_idx]
        local = (idx - s) / max(1, (e - s))
        cn, en = SUBTITLES[min(seg_idx, len(SUBTITLES) - 1)]

        # 地标字幕:段内后 65% 时间出现,前段淡入
        if local > 0.35:
            a = min(1.0, (local - 0.35) / 0.15)
            f = draw_text(frame, cn, (64, H - 152), 44, ACCENT["main"], alpha=a, panel=(26, a))
            f = draw_text(f, en, (66, H - 92), 24, ACCENT["sub"], alpha=a, panel=(20, a))
            frame = f

        # 主标题:仅第一段前 3 秒,带深色衬底
        if idx < int(3.0 * FPS):
            a = min(1.0, idx / (0.8 * FPS))
            t1 = draw_text(frame, TITLE[0], (W - 64, 58), 52, ACCENT["main"],
                           anchor="rt", alpha=a, panel=(30, a))
            t2 = draw_text(t1, TITLE[1], (W - 66, 126), 25, ACCENT["sub"],
                           anchor="rt", alpha=a, panel=(24, a))
            frame = t2

        writer.write(frame)
    writer.release()
    print("输出:", out_path, os.path.getsize(out_path) // 1024, "KB")


if __name__ == "__main__":
    main()
