#!/usr/bin/env python3
"""用 Lovart 官方客户端生成一条视频并下载到本地。

账号只从本目录 .env 或 accounts.json 读取，不写进命令历史以外的仓库文件。
首次运行会把官方客户端克隆到 vendor/（不提交）。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OFFICIAL_REPO = "https://github.com/lovartai/lovart-skill.git"
CLI_REL = Path("vendor/lovart-skill/skills/lovart-skill/scripts/agent_skill.py")
PLACEHOLDERS = {
    "",
    "ak_xxx",
    "sk_xxx",
    "ak_yyy",
    "sk_yyy",
    "your_access_key",
    "your_secret_key",
}
MODELS = {
    "seedance2.5": "generate_video_seedance_v2_5",
    "seedance2.0": "generate_video_seedance_v2_0",
    "seedance2.0-fast": "generate_video_seedance_v2_0_fast",
    "mini": "generate_video_seedance_v2_0_mini",
}


def die(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_account_file(account_id: str | None) -> None:
    path = ROOT / "accounts.json"
    if account_id and not path.is_file():
        die("指定了 --account，但还没有 accounts.json。请复制 accounts.example.json 再填写。")
    if not path.is_file():
        return
    if not account_id and os.environ.get("LOVART_ACCESS_KEY") and os.environ.get("LOVART_SECRET_KEY"):
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    accounts = data.get("accounts") or []
    if not accounts:
        die(f"{path} 里没有 accounts。")
    if account_id:
        chosen = next((item for item in accounts if str(item.get("id")) == account_id), None)
        if chosen is None:
            ids = ", ".join(str(item.get("id")) for item in accounts)
            die(f"accounts.json 里没有 id={account_id}。现有：{ids}")
    else:
        index = int(data.get("active_index") or 0)
        if index < 0 or index >= len(accounts):
            die(f"active_index={index} 超出账号列表。")
        chosen = accounts[index]
    os.environ["LOVART_ACCESS_KEY"] = str(chosen.get("access_key") or "")
    os.environ["LOVART_SECRET_KEY"] = str(chosen.get("secret_key") or "")


def require_keys() -> None:
    load_dotenv(ROOT / ".env")
    access = os.environ.get("LOVART_ACCESS_KEY", "").strip()
    secret = os.environ.get("LOVART_SECRET_KEY", "").strip()
    if access in PLACEHOLDERS or secret in PLACEHOLDERS:
        die(
            "还没有可用的 Lovart 账号。\n"
            "  1. 复制 .env.example 为 .env\n"
            "  2. 填入 LOVART_ACCESS_KEY 和 LOVART_SECRET_KEY\n"
            "     （Lovart 网页 → 头像菜单 → AK/SK 管理）\n"
            "多账号可改用 accounts.json（见 accounts.example.json），再用 --account 选择。"
        )


def ensure_cli() -> Path:
    cli = ROOT / CLI_REL
    if cli.is_file():
        return cli
    dest = ROOT / "vendor" / "lovart-skill"
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    print("首次运行，正在下载官方客户端 https://github.com/lovartai/lovart-skill …", flush=True)
    subprocess.run(["git", "clone", "--depth", "1", OFFICIAL_REPO, str(dest)], check=True)
    if not cli.is_file():
        die(f"官方仓库已下载，但没有找到 {cli}")
    return cli


def parse_json(text: str) -> dict:
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start < 0:
        die(text.strip() or "命令没有返回 JSON")
    try:
        obj, _ = decoder.raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        die(f"无法解析返回 JSON：{exc}\n{text[:1000]}")
    if not isinstance(obj, dict):
        die("返回的不是 JSON 对象")
    return obj


def run_cli(cli: Path, args: list[str], *, heartbeat: str = "") -> dict:
    cmd = [sys.executable, str(cli), *args]
    stop = threading.Event()

    def beat() -> None:
        started = time.time()
        while not stop.wait(30):
            elapsed = int(time.time() - started)
            print(f"…{heartbeat}已等待 {elapsed} 秒（仍是同一条，没有重新提交）", flush=True)

    worker = None
    if heartbeat:
        worker = threading.Thread(target=beat, daemon=True)
        worker.start()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        stop.set()
    if proc.stderr.strip():
        print(proc.stderr, file=sys.stderr, end="" if proc.stderr.endswith("\n") else "\n")
    if proc.returncode != 0:
        if proc.stdout.strip():
            print(proc.stdout, file=sys.stderr)
        raise SystemExit(proc.returncode)
    return parse_json(proc.stdout)


def save_last(out_dir: Path, payload: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "last-run.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def local_files(payload: dict) -> list[str]:
    found = []
    for item in payload.get("downloaded") or []:
        path = item.get("local_path")
        if path:
            found.append(path)
    return found


def report(payload: dict, out_dir: Path) -> None:
    save_last(out_dir, payload)
    status = payload.get("final_status") or payload.get("status") or ""
    thread_id = payload.get("thread_id") or ""
    project_id = payload.get("project_id") or ""
    print(f"状态: {status or '未知'}")
    if thread_id:
        print(f"线程: {thread_id}")
    if project_id:
        print(f"项目: {project_id}")
        print(f"画布: https://www.lovart.ai/canvas?projectId={project_id}")
    files = local_files(payload)
    if files:
        print("文件:")
        for path in files:
            print(f"  {path}")
    videos = [path for path in files if path.lower().endswith((".mp4", ".mov", ".webm"))]
    if status == "done" and not videos:
        print("这次没有下载到视频文件。请看上面的返回；若只有图片，改提示词明确只要视频。")
    print(f"记录: {out_dir / 'last-run.json'}")


def cost_text(pending: dict) -> str:
    if not isinstance(pending, dict):
        return ""
    for key in ("estimated_cost", "estimatedCost", "cost", "credits"):
        if pending.get(key) not in (None, ""):
            return f"预估消耗约 {pending[key]} 积分。"
    return "返回里没有单独的预估积分字段，完整确认信息如下。"


def build_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip()
    else:
        prompt = (args.prompt or "").strip()
    if not prompt:
        die("请用 --prompt 或 --prompt-file 提供提示词。")
    specs = []
    if args.resolution:
        specs.append(args.resolution)
    if args.aspect:
        specs.append(args.aspect)
    if args.seconds:
        specs.append(f"时长 {args.seconds} 秒")
    if specs:
        prompt = prompt.rstrip() + "\n规格：" + "，".join(specs) + "。"
    if not args.no_direct:
        prompt = (
            "直接生成视频，不要先出分镜、规划图或静图，只出视频文件。\n" + prompt
        )
    return prompt


def tool_name(args: argparse.Namespace) -> str:
    if args.tool:
        return args.tool
    if args.model not in MODELS:
        die(f"未知模型 {args.model}。可选：{', '.join(MODELS)}")
    return MODELS[args.model]


def upload_files(cli: Path, files: list[str]) -> list[str]:
    urls = []
    for file_name in files:
        path = Path(file_name).expanduser().resolve()
        if not path.is_file():
            die(f"找不到参考文件: {path}")
        print(f"上传 {path.name} …", flush=True)
        payload = run_cli(cli, ["upload", "--file", str(path)])
        url = payload.get("url")
        if not url:
            die(f"上传没有返回 URL：{json.dumps(payload, ensure_ascii=False)}")
        print(url)
        urls.append(url)
    return urls


def confirm(cli: Path, thread_id: str, out_dir: Path, timeout: int) -> dict:
    print("正在确认这条视频并等待完成…", flush=True)
    return run_cli(
        cli,
        [
            "--timeout",
            str(timeout),
            "confirm",
            "--thread-id",
            thread_id,
            "--json",
            "--download",
            "--output-dir",
            str(out_dir),
        ],
        heartbeat="确认后仍在生成，",
    )


def fetch_result(cli: Path, thread_id: str, out_dir: Path, *, download: bool) -> dict:
    args = ["result", "--thread-id", thread_id]
    if download:
        args.extend(["--download", "--output-dir", str(out_dir)])
    return run_cli(cli, args)


def resume(cli: Path, thread_id: str, out_dir: Path, timeout: int) -> dict:
    """盯住已经提交的线程直到完成、放弃或再次待确认。不会重新发送提示词。"""
    print(f"继续等待原线程 {thread_id}，不会重新提交。", flush=True)
    deadline = time.time() + timeout
    started = time.time()
    while time.time() < deadline:
        status_payload = run_cli(cli, ["status", "--thread-id", thread_id])
        status = str(status_payload.get("status") or "")
        elapsed = int(time.time() - started)
        print(f"…原线程状态 {status or '未知'}，已等待 {elapsed} 秒", flush=True)
        if status == "done":
            time.sleep(5)
            status_payload = run_cli(cli, ["status", "--thread-id", thread_id])
            status = str(status_payload.get("status") or status)
        if status in {"done", "abort"}:
            payload = fetch_result(cli, thread_id, out_dir, download=True)
            payload["thread_id"] = payload.get("thread_id") or thread_id
            payload["final_status"] = status
            return payload
        try:
            peeked = fetch_result(cli, thread_id, out_dir, download=False)
        except SystemExit:
            peeked = {}
        if peeked.get("pending_confirmation"):
            peeked["thread_id"] = peeked.get("thread_id") or thread_id
            peeked["final_status"] = "pending_confirmation"
            return peeked
        time.sleep(15)
    die(
        "等待超时，生成可能还在进行。不要重新提交。过一会儿再执行：\n"
        f"  python3 generate_video.py resume --thread-id {thread_id} --out {out_dir}",
        code=3,
    )
    return {}


def generate(cli: Path, args: argparse.Namespace, out_dir: Path) -> dict:
    prompt = build_prompt(args)
    tool = tool_name(args)
    attachments = list(args.attachment or [])
    if args.file:
        attachments.extend(upload_files(cli, args.file))
    cmd = [
        "--timeout",
        str(args.timeout),
        "chat",
        "--prompt",
        prompt,
        "--json",
        "--download",
        "--output-dir",
        str(out_dir),
        "--mode",
        args.mode,
        "--prefer-models",
        json.dumps({"VIDEO": [tool]}, ensure_ascii=False),
        "--include-tools",
        tool,
    ]
    if args.project_id:
        cmd.extend(["--project-id", args.project_id])
    if args.thread_id:
        cmd.extend(["--thread-id", args.thread_id])
    if attachments:
        cmd.append("--attachments")
        cmd.extend(attachments)
    print(
        f"提交一条视频（模型 {tool}）。高价操作会先停在确认，不会自动扣费。",
        flush=True,
    )
    payload = run_cli(cli, cmd, heartbeat="正在生成，")
    status = payload.get("final_status")
    thread_id = str(payload.get("thread_id") or "")
    project_id = payload.get("project_id")
    if status == "timeout" and thread_id:
        print("等待超时。继续盯同一条，不重新提交。", flush=True)
        payload = resume(cli, thread_id, out_dir, args.timeout)
        payload.setdefault("project_id", project_id)
        status = payload.get("final_status")
        thread_id = str(payload.get("thread_id") or thread_id)
    if status == "pending_confirmation":
        payload = stop_or_confirm(cli, payload, out_dir, args.yes, args.timeout)
    return payload


def stop_or_confirm(cli: Path, payload: dict, out_dir: Path, auto_yes: bool, timeout: int) -> dict:
    thread_id = str(payload.get("thread_id") or "")
    pending = payload.get("pending_confirmation") or {}
    print(cost_text(pending))
    print(json.dumps(pending, ensure_ascii=False, indent=2))
    if not auto_yes:
        print(
            "还没有扣费。看过价钱后执行：\n"
            f"  python3 generate_video.py confirm --thread-id {thread_id} --out {out_dir}"
        )
        save_last(out_dir, payload)
        raise SystemExit(2)
    confirmed = confirm(cli, thread_id, out_dir, timeout)
    confirmed.setdefault("thread_id", thread_id)
    confirmed.setdefault("project_id", payload.get("project_id"))
    if confirmed.get("final_status") == "timeout":
        confirmed = resume(cli, thread_id, out_dir, timeout)
        confirmed.setdefault("project_id", payload.get("project_id"))
    return confirmed


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--account",
        default="",
        help="accounts.json 里的 id。不填则用 .env，或文件里的 active_index",
    )
    parser = argparse.ArgumentParser(
        description="填好 Lovart AK/SK 后生成并下载一条视频。直接写 --prompt 时等价于 generate。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python3 generate_video.py check\n"
            "  python3 generate_video.py --prompt \"雨夜街道\" --resolution 1080p --aspect 9:16 --seconds 5\n"
            "  python3 generate_video.py confirm --thread-id 线程号\n"
            "  python3 generate_video.py resume --thread-id 线程号"
        ),
    )
    sub = parser.add_subparsers(dest="command")

    gen = sub.add_parser("generate", parents=[common], help="生成一条视频（默认命令）")
    gen.add_argument("--prompt", default="", help="提示词原文")
    gen.add_argument("--prompt-file", default="", help="从文件读提示词")
    gen.add_argument("--out", default=str(ROOT / "output"), help="下载目录")
    gen.add_argument("--timeout", type=int, default=1200, help="单次等待秒数，默认 1200")
    gen.add_argument("--model", default="seedance2.5", choices=sorted(MODELS))
    gen.add_argument("--tool", default="", help="直接指定工具名，覆盖 --model")
    gen.add_argument("--seconds", type=int, default=0, help="写入提示词的时长，0 表示不追加")
    gen.add_argument("--resolution", default="", help="例如 1080p。空则不追加")
    gen.add_argument("--aspect", default="", help="例如 9:16。空则不追加")
    gen.add_argument("--file", action="append", default=[], help="本地参考图或音频，可重复")
    gen.add_argument("--attachment", action="append", default=[], help="已经上传好的 URL，可重复")
    gen.add_argument("--project-id", default="", help="复用已有项目")
    gen.add_argument("--thread-id", default="", help="在同一对话里继续改")
    gen.add_argument("--mode", choices=["fast", "thinking"], default="fast")
    gen.add_argument("--yes", action="store_true", help="确认页出现后直接同意扣费")
    gen.add_argument("--no-direct", action="store_true", help="不在提示词前加「只出视频」")

    chk = sub.add_parser("check", parents=[common], help="只用账号查当前生成模式，不生视频")
    chk.add_argument("--timeout", type=int, default=60)

    up = sub.add_parser("upload", parents=[common], help="上传本地文件，打印 CDN URL")
    up.add_argument("--file", required=True)

    con = sub.add_parser("confirm", parents=[common], help="同意一条已经报价的视频并下载")
    con.add_argument("--thread-id", required=True)
    con.add_argument("--out", default=str(ROOT / "output"))
    con.add_argument("--timeout", type=int, default=1200)

    res = sub.add_parser("resume", parents=[common], help="超时或断线后继续等原来那一条并下载")
    res.add_argument("--thread-id", required=True)
    res.add_argument("--out", default=str(ROOT / "output"))
    res.add_argument("--timeout", type=int, default=1200)
    return parser


def main() -> None:
    argv = sys.argv[1:]
    known = {"check", "upload", "confirm", "resume", "generate", "-h", "--help"}
    if not argv:
        argv = ["-h"]
    elif argv[0] not in known:
        argv = ["generate", *argv]
    parser = build_parser()
    args = parser.parse_args(argv)
    load_dotenv(ROOT / ".env")
    load_account_file(args.account or None)
    require_keys()
    cli = ensure_cli()

    if args.command == "check":
        payload = run_cli(cli, ["query-mode"])
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.command == "upload":
        urls = upload_files(cli, [args.file])
        print(json.dumps({"url": urls[0]}, ensure_ascii=False))
        return

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.command == "confirm":
        payload = confirm(cli, args.thread_id, out_dir, args.timeout)
        if payload.get("final_status") == "timeout":
            payload = resume(cli, args.thread_id, out_dir, args.timeout)
        if payload.get("final_status") == "pending_confirmation":
            payload = stop_or_confirm(cli, payload, out_dir, False, args.timeout)
        report(payload, out_dir)
        return

    if args.command == "resume":
        payload = resume(cli, args.thread_id, out_dir, args.timeout)
        if payload.get("final_status") == "pending_confirmation":
            payload = stop_or_confirm(cli, payload, out_dir, False, args.timeout)
        report(payload, out_dir)
        return

    payload = generate(cli, args, out_dir)
    report(payload, out_dir)


if __name__ == "__main__":
    main()
