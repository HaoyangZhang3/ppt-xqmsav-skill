"""对视频等间隔抽帧并拼成带时间标注的九宫格检查图。

用于检查变形转场视频的段间衔接是否穿帮。

用法:
    python extract_frames.py <video.mp4> [输出目录] [帧数]

依赖: opencv-python (pip install opencv-python)
"""
import sys
import os
import glob

import cv2
import numpy as np


def extract(src: str, out_dir: str = "video_frames", k: int = 24) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"无法打开视频: {src}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps <= 0 or n <= 0:
        raise SystemExit("读取视频信息失败")
    print(f"fps={fps:.2f} frames={n} dur={n / fps:.1f}s")

    paths = []
    for i in range(k):
        idx = min(int(n * i / (k - 1)) if k > 1 else 0, n - 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            h, w = frame.shape[:2]
            scale = 480 / w
            frame = cv2.resize(frame, (480, int(h * scale)))
            p = os.path.join(out_dir, f"f{idx:05d}_t{idx / fps:05.1f}s.jpg")
            cv2.imwrite(p, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            paths.append(p)
    cap.release()
    return paths


def sheet(files: list[str], out: str, cols: int = 4) -> None:
    rows = (len(files) + cols - 1) // cols
    tw, th = 320, 480
    canvas = np.full((rows * (th + 26), cols * tw, 3), 20, np.uint8)
    for i, f in enumerate(files):
        img = cv2.imread(f)
        img = cv2.resize(img, (tw, th))
        r, c = divmod(i, cols)
        y = r * (th + 26)
        canvas[y : y + th, c * tw : (c + 1) * tw] = img
        label = os.path.basename(f).split("_t")[1].replace("s.jpg", "").lstrip("0") + "s"
        cv2.putText(canvas, label, (c * tw + 8, y + th + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imwrite(out, canvas, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(f"检查图: {out}")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "video_frames"
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    paths = extract(src, out_dir, k)
    half = (len(paths) + 1) // 2
    base = os.path.join(out_dir, "sheet")
    sheet(paths[:half], base + "1.jpg")
    sheet(paths[half:], base + "2.jpg")


if __name__ == "__main__":
    main()
