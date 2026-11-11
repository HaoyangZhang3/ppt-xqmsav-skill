# 配色主题库（变形转场视频）

同一套场景链可以套不同视觉风格。风格一旦确定，**4 张关键帧 + 4 段提示词必须全部统一**，否则转场处跳色。

## 一、三套成型主题

### A. 平面海报风（红/白/黑）
- 适用：城市地标、历史感、抖音爆款、PPT 开场
- 风格词：
```
flat vector screen-print poster illustration, strictly limited palette of crimson red,
pure white and deep black, bold geometric silhouettes, high contrast, no gradients,
no texture, crisp vector edges, cinematic wide composition
```
- 三色分工：**红色 = 主角/强调**，白色 = 建筑体块与骨架，黑色 = 剪影/地面/阴影
- 后期：`palette_unify.py` 把各图天空与地面统一到同一套红白黑

### B. 暗场·核能蓝金（深空蓝黑 + 电光钴蓝 + 香槟金）
- 适用：电力/能源/核工业/科技主题、沉稳高级感
- 风格词：
```
Dark cinematic flat-vector poster illustration, night scene, deep midnight-navy blue
background, near-black silhouettes, electric cobalt blue rim light and glow,
champagne gold highlights and luminous accents, high contrast, no gradients,
bold geometric silhouettes, flat screen-print aesthetic, nuclear energy mood
```
- 配色比例：**蓝 70% + 金 30%** —— 蓝做底与轮廓光，金只用在发光点（校名/窗格/膜骨架/桥拱倒影）
- 提示词里要把"金"具体点名到发光元素：`glowing champagne gold rooftop sign`、`champagne gold lattice skeleton`、`traced in electric cobalt blue rim light`
- 后期：`assemble_video.py --accent gold`（字幕改香槟金 `#E3BE6A`）

### C. 暗场·酒红（黑底 + 深酒红蒙版 + 暖黄灯源）
- 适用：悬疑、复古、暖调叙事
- 风格词：`deep burgundy red on near-black, warm amber key light, soft light cone, vintage film grain`
- 后期：`assemble_video.py --accent red`

## 二、关键结论：换暗场风格必须 AI 重画，不能靠本地重映射

**踩过的坑**：把红白黑海报本地按亮度重映射成蓝金，结果大片白色区域过曝成白块，达不到暗场。

原因有二：
1. 亮度映射**分不清"白色天空"和"白色建筑"** —— 两者都是高亮度低饱和，映射到同一个颜色后要么天空变亮蓝（失去夜色），要么建筑变暗（主体消失）
2. 高亮区域做辉光（bloom）时，大面积白区会互相叠加直接过曝

结论：
- **换风格 = 重新生成 4 张关键帧**（ImageGen 成本低：4 张约 30-40 credits，远低于视频）
- 本地重映射只适合"同亮度层级换色相"，例如红→蓝这种暗部替代表
- 若必须本地处理：`palette_recolor.py` 的 bloom 阈值调高、强度调低（<0.12），并接受天空不会变夜色

## 三、换风格时的完整动作清单

1. 重写 4 张关键帧的 ImageGen 提示词（风格词 + 主体描述 + 配色比例），构图保持不变，保证闭环关系不破
2. 4 段视频提示词里的**颜色词全部替换**（红→深蓝/电光蓝，白→香槟金，黑→近黑），主体与动作描述不动
3. 重新跑 VideoGen（分辨率按需选 `768P` / `2K`）
4. `assemble_video.py --accent <gold|white|red>` 换字幕配色
5. 抽帧验收：看色调是否全程统一、有无过曝白块

## 四、验收清单

- [ ] 4 张关键帧色调一致（天空/地面不各说各话）
- [ ] 蓝色元素是"轮廓光+体块"而不是"整片死蓝"
- [ ] 金色只出现在发光点，不铺满
- [ ] 无大面积纯白过曝块
- [ ] 视频结尾回到首帧（闭环成立）
- [ ] 字幕在暗场下仍清晰（深色衬底 + 描边）
