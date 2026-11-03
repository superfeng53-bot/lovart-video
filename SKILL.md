---
name: lovart-video
description: >-
  用本目录脚本通过 Lovart 生成并下载视频。用户要出视频、Seedance、Lovart 生视频、
  填 AK/SK 跑视频时使用。只跑 generate_video.py，不直接请求 Lovart HTTP 接口。
---

# Lovart 出视频

执行文件是仓库根目录的 `generate_video.py`。账号只来自调用方自己的 `.env` 或 `accounts.json`。没有密钥就停下来，让对方按 `README.md` 填写，不要编造密钥，也不要改用别的账号。

## 先做

1. 工作目录是本仓库根目录。
2. 没有 `.env` 且没有填好的 `accounts.json`：说明要复制 `.env.example`，到 Lovart 头像菜单 → AK/SK 管理复制两把密钥。不要继续生成。
3. 密钥已填：先跑 `python3 generate_video.py check`。失败就把终端原文给用户，不要换一套请求方式重试。

## 生成

```bash
python3 generate_video.py --prompt "用户的提示词" --resolution 1080p --aspect 9:16 --seconds 5 --out ./output
```

- 提示词用用户原文。不要擅自改成另一段广告词。
- 默认模型是 Seedance 2.5。用户点名别的模型时才改 `--model` 或 `--tool`。
- 有本地参考图或音频：加重复的 `--file`。
- 默认不要加 `--yes`。

## 确认扣费

返回「待确认」或退出码 2 时，把预估积分和线程号告诉用户，然后停。只有用户明确同意这笔费用，才执行：

```bash
python3 generate_video.py confirm --thread-id 线程号 --out ./output
```

用户事先说「直接扣费 / 不用问我」，才可以在生成命令上加 `--yes`。

## 超时和断线

不要再发一次生成。用上次的 `thread_id`：

```bash
python3 generate_video.py resume --thread-id 线程号 --out ./output
```

线程号在终端输出或 `output/last-run.json`。

## 交回什么

把 mp4 的本地路径、线程号、画布链接交给用户。没有视频文件时说明返回状态，不要声称已经生成成功。
