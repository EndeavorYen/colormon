#!/usr/bin/env python3
"""由 site/data/changelog.json（遊戲裡 ⓘ 顯示的內容）產生根目錄的 CHANGELOG.md。
改版時只要編輯 changelog.json，再執行：python3 tools/build-changelog.py"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data = json.load(open(os.path.join(ROOT, "site", "data", "changelog.json"), encoding="utf-8"))
lines = ["# 更新紀錄", "", "遊戲裡右上角的 ⓘ 也看得到。這個檔案由 `site/data/changelog.json` 產生（`python3 tools/build-changelog.py`）。", ""]
for v in data["versions"]:
    lines += [f"## v{v['version']}（{v['date']}）{v['title']}", ""] + [f"- {i}" for i in v["items"]] + [""]
open(os.path.join(ROOT, "CHANGELOG.md"), "w", encoding="utf-8").write("\n".join(lines))
print("CHANGELOG.md:", len(data["versions"]), "個版本")
