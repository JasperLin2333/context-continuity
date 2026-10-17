#!/usr/bin/env python3
"""本仓库的验证、确定性打包与显式安装；只使用 Python 3.10+ 标准库。"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
from urllib.parse import unquote
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("generic", "workbuddy", "skillhub", "claude", "openai")
SEMVER = r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def split_skill(markdown):
    """源 frontmatter 采用平铺的 JSON 字符串（YAML 子集），拒绝未支持语法。"""
    match = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", markdown, re.S)
    if not match:
        raise ValueError("SKILL.md 缺少有效 frontmatter")
    fields = {}
    for line in match[1].splitlines():
        item = re.fullmatch(r"([a-z][a-z_-]*): (.+)", line)
        if not item or item[1] in fields:
            raise ValueError("源 frontmatter 应为不重复的平铺字段")
        value = json.loads(item[2])
        if not isinstance(value, str) or not value.strip():
            raise ValueError("源 frontmatter 字段应为非空 JSON 字符串")
        fields[item[1]] = value
    if set(fields) != {"name", "description", "license"}:
        raise ValueError("平台与版本字段由打包器注入，源只维护 name、description、license")
    return fields, match[2]


def safe_source(root, relative):
    item = PurePosixPath(relative)
    if item.is_absolute() or not item.parts or any(p in ("..", ".") for p in item.parts) or "\\" in relative:
        raise ValueError("资源必须使用仓库内相对路径：" + relative)
    current = root
    for part in item.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("分发资源不能是符号链接：" + relative)
    if not current.is_file():
        raise ValueError("缺少分发文件：" + relative)
    return current


def load_source(root=ROOT):
    config = json.loads((root / "distribution.json").read_text(encoding="utf-8"))
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", config["name"]) or len(config["name"]) > 64:
        raise ValueError("name 不符合 Agent Skills 标准")
    if not re.fullmatch(SEMVER, config["version"]):
        raise ValueError("version 必须为 SemVer")
    if len(config["files"]) != len(set(config["files"])):
        raise ValueError("分发清单包含重复路径")
    payload = {name: safe_source(root, name).read_bytes() for name in config["files"]}
    fields, body = split_skill(payload["SKILL.md"].decode())
    if fields["name"] != config["name"] or fields["license"] != config["license"]:
        raise ValueError("源 Skill 与分发标识或许可证不一致")
    if len(fields["description"]) > 1024 or not body.strip():
        raise ValueError("Skill 描述过长或正文为空")
    for name in ("author", "display_name", "description_zh", "description_en", "repository"):
        if not isinstance(config.get(name), str) or not config[name].strip():
            raise ValueError("缺少发布字段：" + name)
    # 只检查被分发的 Markdown，运行包必须不依赖仓库外的相对引用。
    validate_links(payload)
    return config, fields, body, payload


def validate_links(payload):
    for name, data in payload.items():
        if not name.endswith(".md"):
            continue
        for link in re.findall(r"\]\(([^\s)]+)(?:\s+[^)]*)?\)", data.decode()):
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", link) or link.startswith("#"):
                continue
            target = unquote(link.split("#", 1)[0])
            combined = PurePosixPath(name).parent / target
            # 规范化 ..，但不允许越过包根目录。
            parts = []
            for part in combined.parts:
                if part == "..":
                    if not parts:
                        raise ValueError("引用越过包根目录：" + link)
                    parts.pop()
                elif part != ".":
                    parts.append(part)
            if "/".join(parts) not in payload:
                raise ValueError(f"{name} 引用不在包内：{link}")


def render_skill(config, fields, body, target):
    values = dict(fields)
    if target == "workbuddy":
        values.update(display_name=config["display_name"], display_name_en="Context Continuity",
                      description_zh=config["description_zh"], description_en=config["description_en"],
                      version=config["version"], author=config["author"])
    elif target == "skillhub":
        values.update(slug=config["name"], version=config["version"], displayName=config["display_name"],
                      summary=config["description_zh"], homepage=config["repository"])
    front = "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in values.items())
    front += "\nmetadata:\n" + "\n".join(
        f"  {key}: {json.dumps(value, ensure_ascii=False)}" for key, value in {
            "version": config["version"], "author": config["author"], "repository": config["repository"]}.items())
    return ("---\n" + front + "\n---\n" + body).encode()


def package_files(root=ROOT, target="generic"):
    if target not in TARGETS:
        raise ValueError("未知发布通道：" + target)
    config, fields, body, payload = load_source(root)
    payload["SKILL.md"] = render_skill(config, fields, body, target)
    if target in ("workbuddy", "skillhub"):
        payload["LICENSE.txt"] = payload.pop("LICENSE")
    validate_links(payload)
    if target not in ("claude", "openai"):
        return config, payload
    files = {"skills/" + config["name"] + "/" + name: value for name, value in payload.items()}
    files["LICENSE"] = payload["LICENSE"]
    manifest = {"name": config["name"], "version": config["version"],
                "description": config["description_zh"], "author": {"name": config["author"]},
                "repository": config["repository"], "license": config["license"]}
    if target == "claude":
        files[".claude-plugin/plugin.json"] = json_bytes(manifest)
        files[".claude-plugin/marketplace.json"] = json_bytes({
            "name": "context-continuity-marketplace", "owner": {"name": config["author"]},
            "plugins": [{"name": config["name"], "source": "./", "description": config["description_zh"]}]})
    else:
        manifest["$schema"] = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
        files["plugin.json"] = json_bytes(manifest)
    return config, files


def archive_bytes(name, files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name + "/" + relative, date_time=(2020, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    return buffer.getvalue()


def atomic_write(file, data):
    file.parent.mkdir(parents=True, exist_ok=True)
    if file.is_symlink() or file.parent.is_symlink():
        raise ValueError("不能通过符号链接覆盖发布输出")
    fd, temporary = tempfile.mkstemp(prefix=".pack-", dir=file.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temporary, file)
    finally:
        Path(temporary).unlink(missing_ok=True)


def pack(root=ROOT, targets=TARGETS):
    if (root / "dist").is_symlink():
        raise ValueError("dist 不能是符号链接")
    outputs = []
    for target in targets:
        config, files = package_files(root, target)
        filename = config["name"] + ("" if target == "generic" else "-" + target) + ".zip"
        output = root / "dist" / target / filename
        atomic_write(output, archive_bytes(config["name"], files))
        outputs.append(output)
    # 只记录本次构建的明确输出；不收集旧包或未知文件。
    sums = [hashlib.sha256(file.read_bytes()).hexdigest() + "  " + file.name for file in outputs]
    atomic_write(root / "dist" / "SHA256SUMS", ("\n".join(sums) + "\n").encode())
    return outputs


def install(destination, root=ROOT, link=False):
    config, files = package_files(root, "generic")
    destination = Path(os.path.abspath(destination))
    if destination.name != config["name"]:
        raise ValueError("目标目录名必须为 " + config["name"])
    if os.path.lexists(destination):
        raise ValueError("目标已存在；保留原安装，先比较差异再决定更新方式")
    if root.resolve() == destination.parent.resolve() or root.resolve() in destination.parent.resolve().parents:
        raise ValueError("不能安装到维护仓库内部")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if link:
        destination.symlink_to(root.resolve(), target_is_directory=True)
        return
    destination.mkdir()  # 原子占用新路径，绝不覆盖已有安装。
    try:
        for name, data in files.items():
            output = destination / name
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                stream.write(data)
    except BaseException:
        shutil.rmtree(destination)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="检查源与所有通道包的内容及引用")
    check.add_argument("--tag", help="发布标签必须与 distribution.json 的版本一致")
    build = sub.add_parser("pack", help="生成发布 ZIP 与 SHA256SUMS")
    build.add_argument("--target", choices=(*TARGETS, "all"), default="all")
    setup = sub.add_parser("install", help="显式安装到新目录，默认复制；不改宿主配置")
    setup.add_argument("--destination", required=True)
    setup.add_argument("--link", action="store_true", help="开发使用：指向维护仓库，不复制")
    args = parser.parse_args()
    try:
        if args.command == "check":
            config, *_ = load_source()
            if args.tag and args.tag != "v" + config["version"]:
                raise ValueError("发布标签与分发版本不一致")
            for target in TARGETS:
                package_files(target=target)
            print("源与 5 个通道结构检查通过；不代表宿主行为或市场审核通过。")
        elif args.command == "pack":
            for output in pack(targets=TARGETS if args.target == "all" else (args.target,)):
                print(output)
        else:
            install(args.destination, link=args.link)
            print("已安装：" + args.destination + "；请在当前宿主确认实际发现与读取。")
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
