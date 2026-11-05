---
name: lovart-video
description: >-
  用本目录 generate_video.py 通过 Lovart 生成并下载视频。用户要出视频、Seedance、
  Lovart 生视频、填 AK/SK 跑视频时使用。默认已锁定 fast、1080p、9:16、必须有音轨。
  只跑这个脚本，不要直接请求 Lovart HTTP，也不要改调 vendor 里的官方客户端。
---

# Lovart 出视频

执行文件是仓库根目录的 `generate_video.py`。账号只来自调用方自己的 `.env` 或 `accounts.json`。没有密钥就停下来，让对方按 `README.md` 填写，不要编造密钥，也不要改用别的账号。

踩坑和原句在 `GOTCHAS.md`。下面这些默认值脚本会自己加上，**不要删、不要改成自己的说法**：

- 生成前 `set-mode --fast`（账号扣积分、不排队）
- 这一次 `--mode fast`（不要用 thinking，除非用户点名）
- Seedance 2.5、1080p、9:16
- 提示词规格里的 `有声=必须带…音轨，禁止只出无声画面`
- 只允许视频工具，禁止先出分镜图、规划图、首帧图
- 下载后用 ffprobe 验音轨；退出码 `4` 表示落盘文件没有声音

## 先做

1. 工作目录是本仓库根目录。
2. 没有 `.env` 且没有填好的 `accounts.json`：说明要复制 `.env.example`，到 Lovart 头像菜单 → AK/SK 管理复制两把密钥。不要继续生成。
3. 密钥已填：先跑 `python3 generate_video.py check`。失败就把终端原文给用户，不要换一套请求方式重试。

## 生成

```bash
python3 generate_video.py --prompt "用户的提示词" --seconds 5 --out ./output
```

人对镜头说话时加 `--spoken`：

```bash
python3 generate_video.py --spoken --prompt "用户的台词和画面" --seconds 5 --out ./output
```

- 提示词用用户原文。不要改写成另一段广告，也不要自己再写一套「有环境声 / with audio」。脚本会追加固定的「有声=」原句；你改写或删掉它，成片就会没声音。
- 不要加 `--no-direct`、`--no-set-fast`、`--mode thinking`、`--silent`，除非用户明确要求无声、排队模式或深度规划。
- 默认模型是 Seedance 2.5 / 1080p。用户点名别的模型或分辨率时才改 `--model`、`--tool`、`--resolution`。
- 有本地参考图或参考音频：加重复的 `--file`。参考音频不会变成成片音轨，成片有没有声音仍看「有声=」。
- 默认不要加 `--yes`。

## 确认扣费

返回「待确认」或退出码 2 时，把预估积分和线程号告诉用户，然后停。只有用户明确同意这笔费用，才执行：

```bash
python3 generate_video.py confirm --thread-id 线程号 --out ./output
```

用户事先说「直接扣费 / 不用问我」，才可以在生成命令上加 `--yes`。

若返回的是图片，或 Agent 要求先确认分镜：不要 confirm。那不是这条视频。

## 超时和断线

不要再发一次生成。用上次的 `thread_id`：

```bash
python3 generate_video.py resume --thread-id 线程号 --out ./output
```

线程号在终端输出或 `output/last-run.json`。下载失败同样只 resume，不要重新 `--prompt`。

## 没有声音时

退出码 `4`：文件在，但没有音轨。把路径告诉用户，并说明不要立刻再提交一条（会再扣费）。先核对这次实际提示词里有没有 `有声=`。用户确认要重做之后，才开新的一条，并带上 `--spoken`（口播）或保持默认（环境声/动作声）。

## 交回什么

把 mp4 的本地路径、有没有音轨、线程号、画布链接交给用户。没有视频文件时说明返回状态，不要声称已经生成成功。
