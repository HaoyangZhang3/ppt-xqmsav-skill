"""把一组生成图统一到 红 / 白 / 黑 三色海报调。

用于 AI 变形转场视频的"风格化统一"步骤：不同批次生成的图往往带各自的
天空色和渐变，直接用于视频会在转场处跳色。本脚本按规则做颜色归拢：

  - 极暗像素      -> 纯黑
  - 高亮度低饱和  -> 纯白
  - 低饱和中间调  -> 按亮度映射到深红
  - 高饱和(红系)  -> 保留亮度但统一到 crimson 色相

用法: python palette_unify.py <in.png> <out.png> [--posterize]
"""
import sys
import cv2
import numpy as np

CRIMSON = np.array([46, 16, 200], dtype=np.float32)  # BGR


def unify(img: np.ndarray, posterize: bool = True) -> np.ndarray:
    b, g, r = [cv2.split(img)[i].astype(np.float32) for i in range(3)]
    mx = np.maximum(np.maximum(b, g), r)
    mn = np.minimum(np.minimum(b, g), r)
    sat = (mx - mn) / np.maximum(mx, 1.0)

    out = np.zeros_like(img, dtype=np.float32)

    # 1) 黑区
    dark = mx < 72
    # 2) 白区（亮且几乎无色）
    white = (~dark) & (sat < 0.30) & (mx > 150)
    # 3) 红系（已有明显饱和度）——统一色相，保留明暗
    red = (~dark) & (~white)
    # 4) 中间调灰（天空/地面渐变）——按亮度映射到 crimson
    grey = (~dark) & (~white) & (sat >= 0.30)
    grey = (~dark) & (~white) & (~red)

    # 红色：保持原亮度，统一色相
    scale = (mx / 200.0)[:, :, None]
    red_col = np.clip(CRIMSON[None, None, :] * scale, 0, 255)
    out[red] = red_col[red]

    # 中间调：亮度 -> crimson 强度
    t = np.clip(mx / 200.0, 0, 1)[:, :, None]
    grey_col = CRIMSON[None, None, :] * (0.35 + 0.65 * t)
    out[grey] = grey_col[grey]

    out[dark] = 0
    out[white] = 255

    res = np.clip(out, 0, 255).astype(np.uint8)

    if posterize:
        # 轻度色阶压缩，去掉残留渐变
        levels = 8
        res = (res.astype(np.float32) // (256 / levels)) * (256 / levels)
        res = np.clip(res, 0, 255).astype(np.uint8)

    return res


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    post = "--posterize" in sys.argv
    img = cv2.imread(src)
    if img is None:
        raise SystemExit(f"无法读取: {src}")
    cv2.imwrite(dst, unify(img, post))
    print(f"{src} -> {dst}")


if __name__ == "__main__":
    main()
