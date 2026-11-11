"""把海报图按方案重映射配色（暗场换风格请优先用 AI 重画，见 references/color-themes.md）。

原理: 保持海报的扁平结构与明暗关系不变, 只换色相归属
    红色系 -> 电光蓝 / 钴蓝 渐变
    白色系 -> 香槟金 / 暖白 渐变
    黑色系 -> 深空蓝黑 渐变
再叠加 gamma 压暗 + 暗角 + 高光辉光, 得到暗场质感。

用法: python palette_recolor.py <in.png> <out.png> [--scheme bluegold|darkred] [--gamma 1.35]
"""
import sys

import cv2
import numpy as np


def hx2bgr(s: str):
    s = s.lstrip("#")
    r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    return np.array([b, g, r], dtype=np.float32)


SCHEMES = {
    "bluegold": {
        "red_ramp": ["#05070F", "#0A1630", "#123A8C", "#1E63D8", "#3FA2FF", "#8FD4FF"],
        "white_ramp": ["#2A1A08", "#6B4A12", "#B98A32", "#E3BE6A", "#F5DFA8", "#FFF7E6"],
        "black_ramp": ["#02040A", "#04070F", "#061021", "#08152E", "#0A1A38", "#0C2044"],
        "gamma": 1.35,
    },
    "darkred": {
        "red_ramp": ["#120406", "#2A070C", "#4E0A10", "#7A0D12", "#B2141B", "#E8323C"],
        "white_ramp": ["#2A2118", "#6B5842", "#B39670", "#E0C9A2", "#F5E6C8", "#FFF8EA"],
        "black_ramp": ["#050203", "#0A0507", "#10080C", "#170C12", "#1E1219", "#241820"],
        "gamma": 1.25,
    },
}


def ramp_lut(colors):
    """按 6 个色标线性插值出 256 级 LUT。"""
    stops = np.array([hx2bgr(c) for c in colors], dtype=np.float32)
    out = np.zeros((256, 3), dtype=np.float32)
    seg = len(stops) - 1
    for i in range(256):
        t = i / 255 * seg
        k = min(int(t), seg - 1)
        f = t - k
        out[i] = stops[k] * (1 - f) + stops[k + 1] * f
    return out


def recolor(img: np.ndarray, scheme: str = "bluegold", gamma: float | None = None,
            bloom: float = 0.10, vignette: float = 0.45) -> np.ndarray:
    cfg = SCHEMES[scheme]
    gam = cfg["gamma"] if gamma is None else gamma

    bgr = img.astype(np.float32) / 255.0
    b, g, r = bgr[:, :, 0], bgr[:, :, 1], bgr[:, :, 2]
    mx = np.maximum(np.maximum(b, g), r)
    mn = np.minimum(np.minimum(b, g), r)
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    lum = (0.114 * b + 0.587 * g + 0.299 * r)

    # 分类: 红(高饱和暖色) / 白(低饱和高亮) / 黑(暗)
    is_red = (sat > 0.28) & (r >= g)
    is_white = (~is_red) & (mx > 0.62) & (sat < 0.45)
    is_black = (~is_red) & (~is_white)

    lut_r = ramp_lut(cfg["red_ramp"])
    lut_w = ramp_lut(cfg["white_ramp"])
    lut_k = ramp_lut(cfg["black_ramp"])

    idx = np.clip((lum * 255).astype(np.uint8), 0, 255)
    out = np.zeros_like(bgr)
    out[is_red] = lut_r[idx[is_red]]
    out[is_white] = lut_w[idx[is_white]]
    out[is_black] = lut_k[idx[is_black]]

    # 暗场: gamma 压暗
    out = np.power(np.clip(out, 0, 1), gam)

    # 高光辉光: 取最亮的一层做模糊后加回
    if bloom > 0:
        bright = np.clip((lum - 0.86) / 0.14, 0, 1)[:, :, None] * out
        blur = cv2.GaussianBlur(bright, (0, 0), 8)
        out = np.clip(out + blur * bloom, 0, 1)

    # 暗角
    if vignette > 0:
        h, w = out.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        v = np.clip(1 - vignette * np.clip(d - 0.55, 0, None) ** 1.6 * 2.2, 0, 1)
        out *= v[:, :, None]

    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    scheme = "bluegold"
    gamma = None
    if "--scheme" in sys.argv:
        scheme = sys.argv[sys.argv.index("--scheme") + 1]
    if "--gamma" in sys.argv:
        gamma = float(sys.argv[sys.argv.index("--gamma") + 1])
    img = cv2.imread(src)
    if img is None:
        raise SystemExit(f"无法读取: {src}")
    cv2.imwrite(dst, recolor(img, scheme, gamma))
    print(f"{src} -> {dst}  (scheme={scheme})")


if __name__ == "__main__":
    main()
