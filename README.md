# Lovart 出视频

下载这个仓库，填入自己的 Lovart 账号密钥，就可以生成一条视频并下载到本机。

不需要浏览器登录、Cookie 或画布点选。密钥只放在你自己的 `.env` 或 `accounts.json` 里，仓库里没有任何人的账号。

官方请求由 [lovartai/lovart-skill](https://github.com/lovartai/lovart-skill) 发出（MIT）。第一次运行时脚本会自动克隆它到 `vendor/`，不用单独安装。

直接跑下面的命令即可。**不用**自己在提示词里写「快速模式」或「加声音」——漏写这两句时，别人生成的视频经常没有音轨。脚本已经把它们固定进每次提交。细节和原句见 [GOTCHAS.md](GOTCHAS.md)。

## 每次生成已经固定

| 项 | 默认 |
| --- | --- |
| 账号 | `set-mode --fast`：扣积分、不排队。这是服务器开关，写进提示词无效 |
| 推理 | `--mode fast`。`thinking` 容易先出分镜图 |
| 模型 | Seedance 2.5，1080p，9:16 |
| 声音 | 提示词强制 `有声=必须带可听见的音轨…禁止只出无声画面` |
| 工具 | 只允许这个视频工具，禁止先出静图 |
| 验收 | 下载后用 ffprobe 查音轨，没有音轨就失败（退出码 4） |

口播加 `--spoken`（改成「必须带口播人声音轨」）。明确要无声画面才加 `--silent`。

## 你需要

- Python 3.10 或更高
- git
- ffmpeg（提供 `ffprobe`，用来确认成片真有音轨）
- 一组 Lovart OpenAPI 密钥：网页右上角头像 → **AK/SK 管理**

视频会消耗该账号的积分。脚本默认停在确认页，把预估积分打出来，你同意之后才继续。

## 三步开始

```bash
git clone https://github.com/superfeng53-bot/lovart-video.git
cd lovart-video
cp .env.example .env
```

编辑 `.env`：

```bash
LOVART_ACCESS_KEY=ak_你的密钥
LOVART_SECRET_KEY=sk_你的密钥
```

检查账号是否可用（只查询模式，不生成视频，也不改 fast/unlimited）：

```bash
python3 generate_video.py check
```

生成一条视频。分辨率、画幅、fast、有声都不用再写：

```bash
python3 generate_video.py --prompt "雨夜城市街道，霓虹倒映在湿地，镜头缓慢向前" \
  --seconds 5 --out ./output
```

也可以把画面放进文件（文件里只写画面，不要自己改规格）：

```bash
python3 generate_video.py --prompt-file examples/prompt.txt --seconds 5 --out ./output
```

人对镜头说话：

```bash
python3 generate_video.py --spoken --prompt-file examples/prompt-spoken.txt --seconds 5 --out ./output
```

成功后，mp4 在 `--out` 目录里，终端会打印本地路径、音轨验收和画布链接。同一次运行的返回写在 `output/last-run.json`。

想看脚本实际提交的全文，加上 `--show-prompt`。

## 扣费确认

视频属于高价操作。第一次提交常常返回「待确认」，并带预估积分。这时**还没有按确认价扣费**。

看过价钱后，用终端里打印的线程号继续：

```bash
python3 generate_video.py confirm --thread-id 线程号 --out ./output
```

如果你本来就确定要扣这笔费用，可以在提交时加上 `--yes`，脚本会在确认页出现后直接同意并等待下载。

模型积分和 Agent 推理积分是两笔。推理余额不够时，模型额度看起来还有也会直接拒绝。到网页 Usage 里看，不要连开多条去试。

## 超时或断线

生成经常要几分钟，默认单次最多等 1200 秒。超时、网络断开、终端关掉，都**不要再跑一条新的生成**，否则会再扣一次。

用原来的线程号把同一条收回来：

```bash
python3 generate_video.py resume --thread-id 线程号 --out ./output
```

线程号在终端输出和 `output/last-run.json` 的 `thread_id` 字段里。文件没下载下来时同样用 `resume`，不要重新提交。

## 参考图或参考音频

先上传，再把打印出来的 URL 挂到生成命令上。也可以让生成命令直接读本地文件，它会先上传再提交。

```bash
python3 generate_video.py upload --file ./参考图.jpg

python3 generate_video.py --prompt "按参考图的场景生成视频" \
  --file ./参考图.jpg --file ./环境声.wav \
  --seconds 5
```

参考音频只给模型听，**不会**自动写进成片音轨。成片有没有声音，靠脚本加上的「有声=」。要口型跟上这段人声，再加 `--spoken`。

真人脸如果被平台拒绝，需要先在 Lovart 网页的主体库里过审，再使用过审后的地址。本仓库不提供任何人物素材。

## 模型

默认锁定 **Seedance 2.5**（`generate_video_seedance_v2_5`），1080p、9:16，并且只出视频、不先出静图。

| `--model` | 工具 |
| --- | --- |
| `seedance2.5` | `generate_video_seedance_v2_5`（默认） |
| `seedance2.0` | `generate_video_seedance_v2_0` |
| `seedance2.0-fast` | `generate_video_seedance_v2_0_fast` |
| `mini` | `generate_video_seedance_v2_0_mini` |

有人脸或有人说话时保持默认 2.5 / 1080p。Mini 只适合无人出镜的空镜。

其它视频工具用 `--tool`，例如：

```bash
python3 generate_video.py --tool generate_video_kling_v3 --prompt "海浪拍打岩石" --seconds 5
```

`--no-direct` 会去掉脚本自动加在最前面的整段前缀。不要加，除非你的正文里已经包含同样的「有声=」和「禁止先出图」。

## 多个账号

复制示例再填写，不要把真密钥提交到 git：

```bash
cp accounts.example.json accounts.json
python3 generate_video.py --account main --prompt "一条海边日落的航拍" --seconds 5
```

同时存在 `.env` 和 `accounts.json` 时，默认用 `.env`。加上 `--account` 才改用文件里的那个 id。

## 命令

| 命令 | 作用 |
| --- | --- |
| `python3 generate_video.py check` | 验证密钥，查询当前是快速模式还是无限模式 |
| `python3 generate_video.py set-fast` | 把账号切到 fast（生成命令默认会先做这一步） |
| `python3 generate_video.py --prompt "..."` | 提交一条视频并下载 |
| `python3 generate_video.py confirm --thread-id ...` | 同意报价并等待下载 |
| `python3 generate_video.py resume --thread-id ...` | 断线后继续等原来那一条 |
| `python3 generate_video.py upload --file ...` | 上传参考文件，得到 URL |

常用参数：`--prompt-file`、`--out`、`--seconds`、`--spoken`、`--resolution`、`--aspect`、`--model`、`--file`、`--yes`、`--timeout`、`--project-id`、`--thread-id`、`--show-prompt`。

在同一条对话里改画面时带上原来的 `--thread-id`。换一个全新题目就不要带线程号。

## 给编程助手用

仓库根目录有 `SKILL.md`。把本仓库放进助手的技能目录后，助手只应调用 `generate_video.py`，不要自己拼 Lovart 的 HTTP，也不要改去调用 `vendor/` 里的官方脚本。官方脚本没有 fast 和有声这两条默认，漏写就会得到无声视频。未看到你明确同意扣费前，不要加 `--yes`。

## 不会发生的事

- 仓库不包含任何 AK/SK、Cookie、浏览器用户目录或余额截图
- `.env`、`accounts.json`、`output/`、`vendor/` 已在 `.gitignore`
- 脚本不会在你没同意时自动确认视频扣费
- 超时后续等使用原来的线程，不会悄悄再提交一次
- 默认不会把「快速模式」只写进提示词里就当作已经切到 fast

## 许可

本仓库脚本使用 MIT，见 `LICENSE`。实际请求 Lovart 的客户端来自官方仓库，遵循其自身许可。视频内容与账号费用由调用方自己负责。
