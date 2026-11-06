#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""de-jargon: 扫描代码注释、技术文档与标识符中的 AI 式工程黑话。

用法:
    python scan.py .                       # 扫当前目录
    python scan.py doc/ src/main.cpp       # 扫指定路径
    python scan.py . --level A             # 只报 A 级
    python scan.py . --family buzz,gate    # 只看某几族
    python scan.py . --json > report.json  # 机器可读
    git diff --name-only | python scan.py --paths-from -   # 只查本次改动

退出码: 有 A 级命中返回 1（可接 CI / pre-commit），--no-fail 可关闭。
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))

PROSE_EXT = {".md", ".markdown", ".mdx", ".txt", ".rst", ".adoc", ".org"}

CODE_EXT = {
    ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx", ".ipp", ".inl",
    ".m", ".mm", ".cu",
    ".py", ".rs", ".go", ".java", ".kt", ".kts", ".scala", ".swift",
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte",
    ".cs", ".fs", ".rb", ".php", ".pl", ".lua", ".dart",
    ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd",
    ".sql", ".proto", ".thrift", ".graphql",
    ".cmake", ".gradle", ".groovy", ".toml", ".yaml", ".yml", ".ini", ".conf",
    ".qml", ".ui", ".rc", ".mc", ".iss", ".nsi", ".service", ".desktop",
    ".html", ".htm", ".xml", ".css", ".scss", ".less",
}

SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "target", "__pycache__", ".venv", "venv",
    "vendor", "third_party", "thirdparty", "deps", "engine_deps", "dist", "out",
    ".next", ".nuxt", ".cache", ".idea", ".vs", "obj", "bin",
    "build", "build_linux", "build64_RelWithDebInfo", "build32_Release", "Debug", "Release",
    "cmake-build-debug", "cmake-build-release", ".workbuddy", ".workbuddy-ai",
}

NOISE_BASENAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock", "poetry.lock"}

COMMENT_PREFIXES = {
    "clike": ["//", "/*"],
    "hash": ["#"],
    "sql": ["--"],
    "html": ["<!--"],
    "semi": [";"],
}

EXT_STYLE = {}
for _e in (".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx", ".ipp", ".inl",
           ".m", ".mm", ".cu", ".rs", ".go", ".java", ".kt", ".kts", ".scala", ".swift",
           ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte", ".cs", ".fs",
           ".dart", ".php", ".groovy", ".gradle", ".proto", ".thrift", ".css", ".scss", ".less"):
    EXT_STYLE[_e] = "clike"
for _e in (".py", ".sh", ".bash", ".zsh", ".rb", ".pl", ".yaml", ".yml", ".toml", ".conf",
           ".cmake", ".nsi", ".iss", ".service", ".desktop", ".ini"):
    EXT_STYLE[_e] = "hash"
for _e in (".sql", ".lua"):
    EXT_STYLE[_e] = "sql"
for _e in (".html", ".htm", ".xml", ".qml", ".ui", ".rc", ".mc"):
    EXT_STYLE[_e] = "html"
for _e in (".ps1", ".bat", ".cmd"):
    EXT_STYLE[_e] = "hash"

QUOTE_RE = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|`(?:[^`\\]|\\.)*`')


def load_lexicon(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = []
    for e in data["entries"]:
        entries.append({
            "re": re.compile(e["pattern"]),
            "raw": e["pattern"],
            "level": e.get("level", "B"),
            "family": e.get("family", "misc"),
            "fix": e.get("fix", ""),
            "only_in": e.get("only_in"),
            "kind": "jargon",
        })
    idents = []
    for e in data.get("identifier_patterns", []):
        idents.append({
            "re": re.compile(e["pattern"]),
            "raw": e["pattern"],
            "level": e.get("level", "B"),
            "family": "identifier",
            "fix": e.get("fix", ""),
            "only_in": None,
            "kind": "identifier",
        })
    wl = [re.compile(p) for p in data.get("whitelist_patterns", [])]
    return entries, idents, wl, data.get("yes_terms", [])


def mask_whitelist(line, wl):
    """把白名单命中区替换成等长空格，保持列号不变。"""
    if not wl:
        return line
    buf = list(line)
    for rx in wl:
        for m in rx.finditer(line):
            for i in range(m.start(), m.end()):
                buf[i] = " "
    return "".join(buf)


def quote_spans(line):
    return [(m.start(), m.end()) for m in QUOTE_RE.finditer(line)]


def find_comment_start(line, spans, style):
    prefixes = COMMENT_PREFIXES.get(style, [])
    for p in prefixes:
        idx = 0
        while True:
            i = line.find(p, idx)
            if i < 0:
                break
            if not any(s <= i < e for s, e in spans):
                return i
            idx = i + 1
    return -1


def in_span(pos, spans):
    return any(s <= pos < e for s, e in spans)


def scan_text(path, entries, idents, wl, ext):
    hits = []
    list_lines = 0
    is_prose = ext in PROSE_EXT
    style = EXT_STYLE.get(ext, "clike")
    in_block = False

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except (OSError, UnicodeError):
        return hits, 0

    for lineno, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        text = raw[:4000]

        line = mask_whitelist(text, wl)

        spans = [] if is_prose else quote_spans(line)
        if is_prose:
            cstart = 0
        elif in_block:
            end = line.find("*/")
            cstart = 0
            if end >= 0:
                in_block = False
        else:
            cstart = find_comment_start(line, spans, style)
            opens = line.find("/*")
            if opens >= 0 and not in_span(opens, spans) and (cstart < 0 or opens <= cstart):
                if line.find("*/", opens + 2) < 0:
                    in_block = True

        def pos_of(i):
            if is_prose:
                return "prose"
            if cstart >= 0 and i >= cstart:
                return "comment"
            if in_span(i, spans):
                return "string"
            return "code"

        row = []
        for ent in entries:
            for m in ent["re"].finditer(line):
                p = pos_of(m.start())
                if ent["only_in"] and p not in ent["only_in"]:
                    continue
                row.append({
                    "file": path, "line": lineno, "col": m.start() + 1, "end": m.end(),
                    "word": m.group(0), "pattern": ent["raw"],
                    "level": ent["level"], "family": ent["family"],
                    "fix": ent["fix"], "pos": p, "kind": "jargon",
                    "context": text.strip(),
                })

        if not is_prose:
            for ent in idents:
                for m in ent["re"].finditer(line):
                    p = pos_of(m.start())
                    if p != "code":
                        continue
                    row.append({
                        "file": path, "line": lineno, "col": m.start() + 1, "end": m.end(),
                        "word": m.group(0), "pattern": ent["raw"],
                        "level": ent["level"], "family": ent["family"],
                        "fix": ent["fix"], "pos": p, "kind": "identifier",
                        "context": text.strip(),
                    })

        # 同一处被多条正则命中（如「连接槽位」同时中 连接槽 / 槽位）只留最长的一条
        row.sort(key=lambda h: (-(h["end"] - h["col"]), h["col"]))
        kept = []
        for h in row:
            s, e = h["col"] - 1, h["end"]
            if any(not (e <= k["col"] - 1 or s >= k["end"]) for k in kept):
                continue
            kept.append(h)
        kept.sort(key=lambda h: h["col"])

        # 词表行：一行里 4 个以上不同命中词且覆盖过半行，是在列举而非使用，跳过
        if len(kept) >= 4 and len({h["word"] for h in kept}) >= 4:
            covered = sum(h["end"] - h["col"] + 1 for h in kept)
            if covered / max(1, len(line.strip())) > 0.5:
                list_lines += 1
                continue

        hits.extend(kept)

    return hits, list_lines


def iter_files(targets, exclude_globs):
    seen = set()
    for t in targets:
        if os.path.isfile(t):
            yield os.path.abspath(t)
            continue
        for root, dirs, files in os.walk(t):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for fn in files:
                if fn in NOISE_BASENAMES:
                    continue
                full = os.path.join(root, fn)
                ext = os.path.splitext(fn)[1].lower()
                if ext not in PROSE_EXT and ext not in CODE_EXT:
                    continue
                if any(_glob_match(full, g) for g in exclude_globs):
                    continue
                ap = os.path.abspath(full)
                if ap in seen:
                    continue
                seen.add(ap)
                yield ap


def _glob_match(path, pattern):
    import fnmatch
    return fnmatch.fnmatch(path.replace("\\", "/"), pattern) or fnmatch.fnmatch(
        os.path.basename(path), pattern)


def main():
    ap = argparse.ArgumentParser(description="扫描 AI 式工程黑话")
    ap.add_argument("paths", nargs="*", default=["."])
    ap.add_argument("--level", default="AB", help="只报这些级别，默认 AB")
    ap.add_argument("--family", default="", help="逗号分隔，如 buzz,gate,flow")
    ap.add_argument("--exclude", action="append", default=[], help="额外排除 glob")
    ap.add_argument("--paths-from", default="", help="从文件或 - 读待扫路径")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-per-file", type=int, default=8)
    ap.add_argument("--quiet", action="store_true", help="只出汇总")
    ap.add_argument("--no-fail", action="store_true")
    args = ap.parse_args()

    entries, idents, wl, yes_terms = load_lexicon(os.path.join(HERE, "lexicon.json"))

    targets = list(args.paths)
    if args.paths_from:
        if args.paths_from == "-":
            targets = [l.strip() for l in sys.stdin if l.strip()]
        else:
            with open(args.paths_from, "r", encoding="utf-8") as f:
                targets = [l.strip() for l in f if l.strip()]

    levels = set(args.level.upper())
    fams = {x.strip() for x in args.family.split(",") if x.strip()}

    all_hits = []
    nfiles = 0
    skipped_lists = 0
    for p in iter_files(targets, args.exclude):
        ext = os.path.splitext(p)[1].lower()
        try:
            if os.path.getsize(p) > 8 * 1024 * 1024:
                continue
            with open(p, "rb") as f:
                if b"\x00" in f.read(4096):
                    continue
        except OSError:
            continue
        nfiles += 1
        file_hits, n_lists = scan_text(p, entries, idents, wl, ext)
        skipped_lists += n_lists
        for h in file_hits:
            if h["level"] not in levels:
                continue
            if fams and h["family"] not in fams:
                continue
            all_hits.append(h)

    if args.json:
        out = OrderedDict()
        out["files_scanned"] = nfiles
        out["total"] = len(all_hits)
        out["by_level"] = dict(Counter(h["level"] for h in all_hits))
        out["skipped_list_lines"] = skipped_lists
        out["hits"] = all_hits
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if args.no_fail else (1 if any(h["level"] == "A" for h in all_hits) else 0)

    cwd = os.getcwd()

    def rel(p):
        try:
            return os.path.relpath(p, cwd)
        except ValueError:
            return p

    lv = Counter(h["level"] for h in all_hits)
    print("")
    print("扫描 %d 个文件 · 命中 %d 处   [A 级 %d · B 级 %d]"
          % (nfiles, len(all_hits), lv.get("A", 0), lv.get("B", 0)))
    if skipped_lists:
        print("（跳过 %d 行词表/列举 —— 一行里 4 个以上不同命中词，按引用处理）" % skipped_lists)
    print("")

    if not all_hits:
        print("  没有命中。")
        print("")
        return 0

    if not args.quiet:
        byfile = OrderedDict()
        for h in all_hits:
            byfile.setdefault(h["file"], []).append(h)

        ranked = sorted(byfile.items(), key=lambda kv: -len(kv[1]))
        print("── 按文件 " + "─" * 56)
        for fpath, hs in ranked:
            la = sum(1 for x in hs if x["level"] == "A")
            lb = len(hs) - la
            print("")
            print("  %s  (%d 处, A%d B%d)" % (rel(fpath), len(hs), la, lb))
            for h in hs[:args.max_per_file]:
                ctx = h["context"]
                if len(ctx) > 96:
                    s = max(0, h["col"] - 40)
                    head = "…" if s > 0 else ""
                    tail = "…" if s + 96 < len(ctx) else ""
                    ctx = head + ctx[s:s + 96] + tail
                mark = "" if h["pos"] in ("comment", "prose") else "  ⟨在%s里⟩" % (
                    "字符串" if h["pos"] == "string" else "代码")
                print("    %4d:%-4d [%s][%s] %s%s"
                      % (h["line"], h["col"], h["level"], h["family"], ctx, mark))
                print("              ↑ 「%s」 %s" % (h["word"], h["fix"]))
            if len(hs) > args.max_per_file:
                print("    … 另有 %d 处" % (len(hs) - args.max_per_file))
        print("")

    print("── 高频词 " + "─" * 56)
    for w, c in Counter(h["word"] for h in all_hits).most_common(20):
        print("  %-12s %d" % (w, c))
    print("")

    print("── 高频文件 " + "─" * 54)
    for fn, c in Counter(rel(h["file"]) for h in all_hits).most_common(10):
        print("  %-56s %d" % (fn[:56], c))
    print("")

    if lv.get("A", 0):
        print("提示：A 级 %d 处按约定应直接改写（代码注释/日志/标识符）" % lv["A"])
        print("      落在 .md 文档的 A 级只出报告，等确认后再动。")
        print("")

    return 0 if args.no_fail else (1 if lv.get("A", 0) else 0)


if __name__ == "__main__":
    sys.exit(main())
