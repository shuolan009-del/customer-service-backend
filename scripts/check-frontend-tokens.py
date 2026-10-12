"""核对前端使用的 CSS 变量是否都有定义。

用正则从所有 .vue/.css 里抽出 var(--xxx) 的引用，再与 design-tokens.css 里
定义的变量集合比对，列出「被引用但未定义」的变量 —— 这类变量在浏览器里会静默
失效（继承上级颜色），属于最难发现的样式 bug。
"""

import re
from pathlib import Path

ROOT = Path(r"F:\customer-service-backend\external\customer-service-frontend\src")

DEF_RE = re.compile(r"^\s*(--[a-zA-Z0-9-]+)\s*:", re.MULTILINE)
USE_RE = re.compile(r"var\(\s*(--[a-zA-Z0-9-]+)")

defined = set()
used = {}

for path in ROOT.rglob("*"):
    if path.suffix not in {".css", ".vue", ".js"}:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    if path.name == "design-tokens.css":
        defined |= set(DEF_RE.findall(text))
    for name in USE_RE.findall(text):
        used.setdefault(name, []).append(str(path.relative_to(ROOT)))

missing = sorted(name for name in used if name not in defined)
print(f"定义变量: {len(defined)}  引用变量: {len(used)}")
print("\n=== 被引用但未定义（会静默失效） ===")
if not missing:
    print("无")
for name in missing:
    files = sorted(set(used[name]))
    print(f"{name}  <-  {', '.join(files)}")

unused = sorted(name for name in defined if name not in used)
print(f"\n=== 已定义但未被引用: {len(unused)} 个 ===")
print(", ".join(unused) if unused else "无")
