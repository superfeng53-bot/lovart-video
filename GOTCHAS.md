# 踩过的坑

这些都已经写进 `generate_video.py` 的默认行为。自己改官方客户端、或在网页里手写提示词时，按下面原句照做。少写一条，常见结果就是：**扣了积分，视频没有声音**，或者先烧出一张静图。

## 默认已经固定的参数

直接跑 `python3 generate_video.py --prompt "..."` 时，脚本会做这些事，不用再手写：

| 项 | 默认 |
| --- | --- |
| 账号生成模式 | 每次生成前 `set-mode --fast`（扣积分、不排队） |
| Agent 推理 | `--mode fast` |
| 模型 | Seedance 2.5，`generate_video_seedance_v2_5` |
| 工具锁 | `--include-tools` 只放这一个视频工具，`--prefer-models` 只留 `VIDEO` |
| 画幅 | `1080p`，`9:16` |
| 声音 | 提示词里写死「有声=…，禁止只出无声画面」 |
| 验收 | 下载后用 `ffprobe` 查音轨；没有音轨则退出码 `4` |

口播（人对镜头说话）再加上 `--spoken`。只有明确要无声画面才加 `--silent`。

## 1. 两条「fast」不是一回事

| 名字 | 命令 | 作用 |
| --- | --- | --- |
| 账号模式 | `set-mode --fast` | 服务器开关。fast = 扣积分、不排队。`unlimited` = 免费队列，适合生图，**不适合当生视频默认** |
| 推理模式 | `chat --mode fast` | 这一次 Agent 怎么想。`thinking` 会先规划，经常先出分镜图、首帧图 |

不要在提示词里写「快速模式」「fast mode」。写了也不会切账号。账号模式是持久的：曾经设成 `unlimited` 之后，后面所有生成都跟着排队，直到再执行 `set-fast`。

```bash
python3 generate_video.py set-fast
python3 generate_video.py check
```

`check` 只查询，不改模式，也不生视频。

## 2. 不写死「有声=」，成片经常没有音轨

「有环境声」「加个声音」「with audio」都不够。模型会当气氛词，照样出一条无声 mp4。

脚本加在规格里的原句：

- 普通视频：`有声=必须带可听见的音轨（环境声/动作声/人声均可，禁止只出无声画面）`
- 口播（`--spoken`）：`有声=必须带口播人声音轨（开口同步出声，禁止只出无声画面）`

手写提示词时，整段前缀用这一句（口播把「一条视频」改成「一条口播视频」，并加上「一字不改台词」）：

```text
用 Seedance 2.5 直接生成一条视频，规格：1080p，9:16，时长 5 秒，有声=必须带可听见的音轨（环境声/动作声/人声均可，禁止只出无声画面）。严格按下面提示词执行。禁止先生成分镜图、规划图、首帧图或任何静图；禁止视觉规划子代理；只调用视频工具出视频，不要先出图。
```

落盘后自己查：

```bash
ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 视频.mp4
```

有输出 `audio` 才算有声音。本机没有 `ffprobe` 时脚本会跳过验收并打印警告，请安装 ffmpeg。

无声文件的退出码是 `4`。这时不要马上再提交一条：先看 `output/last-run.json` 里的实际提示词有没有上面的「有声=」。本来就要无声片，用 `--silent`。

## 3. 参考音频 ≠ 成片自己的音轨

`--file 参考.wav` 只是给模型听的参考，**不会**自动变成成片音轨。

- 要成片能听见：靠提示词里的「有声=…」
- 要口型跟上某段人声：参考音频照常 `--file`，命令再加 `--spoken`，正文写清谁在说、说哪一句
- 不要让 Lovart 先「生成一段配音」再拿去对口型。配音在别的工具做好，这里只上传成品音频

真人脸不能拿普通 CDN 直链当角色。先在网页 **主体库** 审核通过，再用过审后的地址。裸传证件照式人脸，常见结果是直接拒绝、还没进确认页。

## 4. 只锁视频工具，禁止先出图

只写「用 Seedance」不够。Agent 仍可能先出分镜、规划图、首帧，静图也扣积分。

提交必须同时有：

- 提示词里的「禁止先生成分镜图、规划图、首帧图或任何静图」
- `--include-tools generate_video_seedance_v2_5`
- `--prefer-models '{"VIDEO":["generate_video_seedance_v2_5"]}'`
- `--mode fast`

返回的是 png、或问你「先确认分镜」：**不要 confirm**。那次静图不要付钱。视频还没真正开始时，用本脚本重新提交（会带上上面的锁）。已经有 `thread_id` 并且状态还在跑，就不要再开一条。

## 5. 超时、断线：只收回原来那一条

生成常常要几分钟。超时、网络断了、终端关了，都**不要**再跑一次 `--prompt`。再跑会再扣一次。

```bash
python3 generate_video.py resume --thread-id 线程号 --out ./output
```

线程号在终端，也在 `output/last-run.json` 的 `thread_id`。同一条对话里改画面才带 `--thread-id`；换一个新题目不要带。

下载失败、`local_path` 为空：对**同一个** `thread_id` 再 `resume`，不要重新 `chat`。生成成功和本机下不下来是两件事。

## 6. 确认页出现之前不要当它已经在做

视频是高价操作。第一次返回经常是 `pending_confirmation`，退出码 `2`。这时**还没按确认价扣费**。

看过预估积分再执行：

```bash
python3 generate_video.py confirm --thread-id 线程号 --out ./output
```

没有明确说「直接扣费」之前，不要加 `--yes`。

积分分两笔：模型生成一笔，Agent 推理另要一笔余额。模型额度看起来还够，仍可能报：

```text
Insufficient credits to start the request. Unlimited covers generation models only — the agent that runs your request still needs a credit balance for its reasoning steps.
```

这是推理余额不够，不是提示词写错。去网页看 Usage，补上推理积分再继续。不要为了试错连开好几条。

## 7. 分辨率和模型不要随手降

默认 `1080p` + Seedance 2.5。不要因为想省积分改成 720p / 480p，也不要改成 Mini，除非你明确只要无人出镜的空镜。

有人脸、有人说话：用默认的 2.5 / 1080p。Mini 出的人脸和口型都不适合当正式口播。

提示词里写 3 秒，成片仍可能是 4–5 秒。时长以落盘 `ffprobe` 为准，积分以确认页和网页 Usage 为准。

## 8. 不要关掉的开关

| 参数 | 什么时候才能用 |
| --- | --- |
| `--no-set-fast` | 你知道账号必须留在 unlimited |
| `--mode thinking` | 你接受它先做规划，并自己盯着不要先出图 |
| `--no-direct` | 你的提示词正文里已经有完整前缀（含有声=和禁止出图） |
| `--silent` | 你就要一条没有音轨的画面 |
| `--allow-silent-output` | 仍要求有声，但没音轨时只警告、不当失败 |
| `--yes` | 你已经同意按确认价扣费 |

编程助手：只跑本仓库的 `generate_video.py`。不要自己拼 Lovart 的 HTTP，也不要改去调用 `vendor/` 里的官方脚本。官方脚本没有这些默认值，别人漏写就会得到无声视频。
