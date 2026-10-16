#!/usr/bin/env python3
"""通过 GitHub Git Data API 把本地 git 仓库内容推送到远端。

适用场景：本环境网络代理允许 api.github.com，但阻断 github.com:443
（git push/fetch 报 502 CONNECT tunnel failed 或 schannel 中断），
且代理延迟极高（单请求 ~6s）、Python urllib 经代理易挂死。

策略：
  - HTTP 层用 curl 子进程（实测比 urllib 稳定；大 body 写临时文件，避开 Windows 命令行长度限制）；
  - blob 上传 8 路并发（内容寻址、幂等，可安全并行）；
  - tree/commit/ref 顺序执行，完整保留提交历史（信息/作者/时间）；
  - 增量推送：远端已有的提交自动跳过（对象内容寻址，commit 在远端则整树都在）；
    远端有本地没有的提交时拒绝强推，防止误覆盖。
  - 空仓库先用 Contents API 放占位 README 初始化（否则建 blob 报 409
    "Git Repository is empty"），随后把自己的提交 force 到分支上，
    占位提交成为不可达对象，不出现在分支历史里。

用法：
    GH_TOKEN=<pat> python gh_api_push.py <repo名> <本地仓库路径> [分支名]

依赖：Python 标准库 + 系统 curl。代理读取环境变量 http_proxy/https_proxy。
实测：日期用 ISO 8601（带时区偏移）序列化可字节级还原，远端 commit SHA 与本地一致；
      推送后本地与远端自然同步，无需 reset。
"""

import base64
import datetime
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

TOKEN = os.environ.get("GH_TOKEN", "")
OWNER = os.environ.get("GH_OWNER", "shuolan009-del")
API = "https://api.github.com"
BLOB_WORKERS = 8


def api(method, path, body=None, retries=5, timeout=60, no_retry_codes=()):
    """调 GitHub API（curl 子进程实现，带退避重试）。返回解析后的 JSON。
    no_retry_codes 内的 HTTP 状态码立即失败（如 422 ref 已存在，重试无意义）。"""
    url = API + path
    tmp_path = None
    cmd = ["curl", "-sS", "-m", str(timeout), "-X", method, url,
           "-H", "Authorization: Bearer " + TOKEN,
           "-H", "Accept: application/vnd.github+json",
           "-w", "\n%{http_code}"]
    if body is not None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False)
            tmp_path = f.name
        cmd += ["-H", "Content-Type: application/json", "--data-binary", "@" + tmp_path]
    try:
        last = ""
        for attempt in range(retries):
            r = subprocess.run(cmd, capture_output=True)
            out = r.stdout.decode("utf-8", "replace")
            parts = out.rsplit("\n", 1)
            try:
                code = int(parts[-1].strip())
                payload = parts[0] if len(parts) > 1 else ""
            except ValueError:
                raise RuntimeError(
                    f"{method} {path} curl 输出异常: {out[:200]} | "
                    f"stderr: {r.stderr.decode('utf-8', 'replace')[:200]}")
            if 200 <= code < 300:
                return json.loads(payload) if payload.strip() else {}
            last = f"HTTP {code}: {payload[:300]}"
            if code in no_retry_codes:
                break
            wait = 10 * (attempt + 1) if code in (403, 429) else 2 * (attempt + 1)
            print(f"    [retry {attempt + 1}/{retries}] {method} {path} -> {last}；{wait}s 后重试")
            time.sleep(wait)
        raise RuntimeError(f"{method} {path} 重试 {retries} 次仍失败: {last}")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def git(workdir, *args, binary=False):
    r = subprocess.run(["git"] + list(args), cwd=workdir, capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode("utf-8")


def parse_ident(line):
    """'author 名字 <邮箱> 1699999999 +0800' -> (name, email, epoch, tzoffset)"""
    who = line.split(" ", 1)[1]
    name, rest = who.rsplit(" <", 1)
    email, tail = rest.split("> ", 1)
    epoch, tz = tail.strip().split(" ")
    return name, email, epoch, tz


def to_iso(epoch, tz):
    """git 时间戳 -> ISO 8601（带时区偏移，GitHub API 接受）"""
    sign = 1 if tz.startswith("+") else -1
    tz_sec = sign * (int(tz[1:3]) * 3600 + int(tz[3:5]) * 60)
    dt = datetime.datetime.fromtimestamp(
        int(epoch), tz=datetime.timezone(datetime.timedelta(seconds=tz_sec)))
    return dt.isoformat()


def ensure_repo_initialized(repo, branch="main"):
    """空仓库直接建 blob 会 409（Git Repository is empty）。
    先用 Contents API 放占位 README 生成初始提交，随后本脚本会把自己的提交
    force 到分支上，占位提交成为不可达对象，不出现在分支历史里。

    返回 True 表示本次调用刚创建了占位提交（调用方应忽略远端当前 HEAD）。
    """
    try:
        api("GET", f"/repos/{OWNER}/{repo}/git/refs/heads/{branch}",
            no_retry_codes=(404, 409))
        return False
    except RuntimeError as e:
        # 404 = 分支不存在；409 = Git Repository is empty。两者都表示仓库为空，需初始化
        if "404" not in str(e) and "409" not in str(e):
            raise
    except KeyError:
        # 极端情况下 ref 响应缺 object 字段，同样按空仓库处理
        pass
    readme = base64.b64encode(
        f"# {repo}\n\n(placeholder - real content follows in commit history)\n"
        .encode("utf-8")).decode("ascii")
    api("PUT", f"/repos/{OWNER}/{repo}/contents/README.md", {
        "message": "chore: initialize repository",
        "content": readme,
        "branch": branch,
    })
    print("    [init] 空仓库已用占位 README 初始化（后续被真实提交替换）")
    return True


def upload_blobs(repo, workdir, sha_content_pairs):
    """并发上传 blob。sha_content_pairs: [(git_sha, bytes), ...]"""
    total = len(sha_content_pairs)
    done = [0]
    failed = []

    def one(item):
        sha, content = item
        resp = api("POST", f"/repos/{OWNER}/{repo}/git/blobs", {
            "content": base64.b64encode(content).decode("ascii"),
            "encoding": "base64",
        })
        if resp.get("sha") != sha:
            raise RuntimeError(f"blob SHA 不一致: 本地 {sha} vs 远端 {resp.get('sha')}")
        done[0] += 1
        if done[0] % 20 == 0 or done[0] == total:
            print(f"    blob 进度: {done[0]}/{total}")

    with ThreadPoolExecutor(max_workers=BLOB_WORKERS) as ex:
        futs = {ex.submit(one, item): item[0] for item in sha_content_pairs}
        for f in as_completed(futs):
            try:
                f.result()
            except Exception as e:
                failed.append((futs[f], str(e)))
    return failed


def is_placeholder_commit(repo, sha, branch="main"):
    """判断远端 HEAD 是否为本脚本创建的占位提交。

    场景：本次调用（或上一次失败重试）刚用 Contents API 放了占位 README，
    该提交不在本地历史里，会被防强推保护误拦。此处核实它确实只是占位符
    （提交信息匹配 + 仅含 README.md + 内容为占位文本），是则可安全覆盖。
    """
    try:
        # 注意两点：① 必须用完整 40 位 SHA（短 SHA 此端点返回 404）；
        #         ② /repos/{}/{}/commits/{sha} 才带 files 字段，/git/commits/{sha} 不带
        full = api("GET", f"/repos/{OWNER}/{repo}/commits/{sha}")
        if full.get("commit", {}).get("message", "").strip() != "chore: initialize repository":
            return False
        if [f["filename"] for f in (full.get("files") or [])] != ["README.md"]:
            return False
    except RuntimeError:
        return False
    try:
        blob = api("GET", f"/repos/{OWNER}/{repo}/contents/README.md?ref={branch}")
        text = base64.b64decode(blob["content"]).decode("utf-8", "replace")
    except RuntimeError:
        return False
    return "placeholder - real content follows in commit history" in text


def push_repo(repo, workdir, branch="main"):
    print(f"==> {repo}  (workdir={workdir}, branch={branch})")
    print(f"    proxies: {urllib.request.getproxies()}")
    t0 = time.time()
    just_initialized = ensure_repo_initialized(repo, branch)

    # 远端当前 HEAD：增量推送的依据 + 防强推保护
    if just_initialized:
        # 刚放的占位提交不在本地历史里，属预期情况——按全量推送处理，
        # 末尾会把分支 force 到本地 HEAD，占位提交成为不可达对象
        print("    远端 HEAD 为本次创建的占位提交，按全量推送处理")
        remote_sha = None
    else:
        try:
            remote_sha = api("GET", f"/repos/{OWNER}/{repo}/git/refs/heads/{branch}")["object"]["sha"]
        except RuntimeError:
            remote_sha = None
        if remote_sha and is_placeholder_commit(repo, remote_sha, branch):
            print("    远端 HEAD 是占位提交（上次初始化残留），按全量推送处理")
            remote_sha = None

    commits = git(workdir, "rev-list", "--reverse", "--topo-order", branch).split()
    if remote_sha:
        if remote_sha in commits:
            idx = commits.index(remote_sha)
            if idx == len(commits) - 1:
                print("    远端已是最新，无需推送")
                return remote_sha
            print(f"    增量推送：跳过远端已有的 {idx + 1} 个提交")
            commits = commits[idx + 1:]
        else:
            raise RuntimeError(
                f"远端 {branch}（{remote_sha[:8]}）不在本地历史中——对方可能有新提交，"
                "禁止强推覆盖。请先在本地合并/拉取后再推。")
    print(f"    待推送提交数: {len(commits)}")

    # 1) 汇总所有提交的去重 blob（内容寻址，跨提交共享）
    blob_jobs = {}   # sha -> content bytes
    per_commit = []  # [(commit, [(mode, sha, path), ...]), ...]
    for c in commits:
        raw = git(workdir, "cat-file", "commit", c)
        header, _, message = raw.partition("\n\n")
        tree_raw = git(workdir, "ls-tree", "-r", "-z", c, binary=True)
        entries = []
        for item in tree_raw.split(b"\x00"):
            if not item:
                continue
            meta_part, path = item.split(b"\t", 1)
            mode, typ, sha = meta_part.decode("ascii").split()
            if typ == "commit":
                raise RuntimeError(
                    f"检测到 gitlink/submodule（mode 160000）: {path!r}，"
                    "API 方式无法推送子模块，请先移除或改用本地 git push")
            entries.append((mode, sha, path))
            if sha not in blob_jobs:
                blob_jobs[sha] = git(workdir, "cat-file", "blob", sha, binary=True)
        parents = git(workdir, "log", "-1", "--format=%P", c).split()
        per_commit.append((c, header, message, entries, parents))

    print(f"    唯一 blob 数: {len(blob_jobs)}（{BLOB_WORKERS} 路并发上传）")
    failed = upload_blobs(repo, workdir, list(blob_jobs.items()))
    if failed:
        raise RuntimeError(f"{len(failed)} 个 blob 上传失败，例如: {failed[0]}")

    # 2) 逐提交建 tree / commit（保留原作者、提交者与时间）
    parent = None
    last_tree_sha = None
    for i, (c, header, message, entries, parents_local) in enumerate(per_commit):
        an, ae, ats_e, ats_tz = parse_ident(
            next(l for l in header.splitlines() if l.startswith("author ")))
        cn, ce, cts_e, cts_tz = parse_ident(
            next(l for l in header.splitlines() if l.startswith("committer ")))
        tree = api("POST", f"/repos/{OWNER}/{repo}/git/trees", {
            "tree": [{"path": p.decode("utf-8"), "mode": m, "type": "blob", "sha": s}
                     for m, s, p in entries]
        })
        last_tree_sha = tree["sha"]
        body = {
            "message": message,
            "tree": tree["sha"],
            "author": {"name": an, "email": ae, "date": to_iso(ats_e, ats_tz)},
            "committer": {"name": cn, "email": ce, "date": to_iso(cts_e, cts_tz)},
        }
        if i == 0 and parents_local:
            # 首个待推提交的父提交已存在于远端（增量衔接；全量推时首提是根提交，无 parent）
            body["parents"] = parents_local
        elif parent:
            body["parents"] = [parent]
        commit = api("POST", f"/repos/{OWNER}/{repo}/git/commits", body)
        parent = commit["sha"]
        print(f"    {c[:8]} -> {commit['sha'][:8]}  ({len(entries)} files)  "
              f"{message.splitlines()[0][:50]}")

    # 3) 建/更新分支 ref（占位 README 提交已被 force 掉）
    ref_path = f"/repos/{OWNER}/{repo}/git/refs/heads/{branch}"
    try:
        api("POST", f"/repos/{OWNER}/{repo}/git/refs",
            {"ref": f"refs/heads/{branch}", "sha": parent}, no_retry_codes=(422,))
    except RuntimeError:
        api("PATCH", ref_path, {"sha": parent, "force": True})

    # 4) 校验：远端分支 commit 的 tree 必须等于本地最后推上去的 tree
    remote = api("GET", ref_path)
    remote_sha = remote["object"]["sha"]
    remote_commit = api("GET", f"/repos/{OWNER}/{repo}/git/commits/{remote_sha}")
    if remote_commit["tree"]["sha"] != last_tree_sha:
        raise RuntimeError("远端 tree 与本地不一致，推送结果异常")
    print(f"    ref {branch} -> {remote_sha[:8]}  tree 校验 OK")
    print(f"==> 完成（{time.time() - t0:.0f}s）: https://github.com/{OWNER}/{repo}")
    return remote_sha


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("缺少环境变量 GH_TOKEN")
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    push_repo(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "main")
