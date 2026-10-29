#!/usr/bin/env python3
"""從 PokeAPI 公開資料（GitHub: PokeAPI/api-data）整理「第二屬性」，輸出 site/data/packs/type2.json。
格式和其他資料包一樣：{"name":..., "pokemon":[{"id":6,"type2":"flying"}]}，載入時會合併到同編號的寶可夢上。
主屬性（type）還是各世代資料包自己的；這個檔只補第二屬性，有不一樣的會列出來。
用法：python3 tools/build-types2.py"""
import json,os,urllib.request,glob
ROOT=os.path.join(os.path.dirname(__file__),"..","site","data")
types=json.load(open(os.path.join(ROOT,"types.json")))
def get(n):
    with urllib.request.urlopen(f"https://raw.githubusercontent.com/PokeAPI/api-data/master/data/api/v2/type/{n}/index.json",timeout=30) as r: return json.load(r)
mine={}
for f in sorted(glob.glob(os.path.join(ROOT,"packs","gen*.json"))):
    for m in json.load(open(f))["pokemon"]: mine[m["id"]]=m["type"]
slot={}
for n in range(1,19):
    d=get(n);name=d["name"]
    if name not in types: raise SystemExit(f"types.json 沒有 {name}")
    for e in d["pokemon"]:
        pid=int(e["pokemon"]["url"].rstrip("/").split("/")[-1])
        if pid in mine: slot.setdefault(pid,{})[e["slot"]]=name      # 只收一般型態（編號 ≤ 1025），不收特殊形態
out=[];diff=[]
for pid in sorted(slot):
    s=slot[pid]
    if s.get(1)!=mine[pid]: diff.append((pid,mine[pid],s.get(1)))
    real=[t for t in (s.get(1),s.get(2)) if t]
    others=[t for t in real if t!=mine[pid]]                       # 我們的主屬性以外的那個（例如波波：我們的主屬性是飛行，真正是一般／飛行 → 第二屬性＝一般）
    if others: out.append({"id":pid,"type2":others[0]})
    if mine[pid] not in real: print("  ⚠ 主屬性不在 PokeAPI 的屬性裡：",pid,mine[pid],real)
json.dump({"name":"第二屬性（PokeAPI）","pokemon":out},open(os.path.join(ROOT,"packs","type2.json"),"w"),ensure_ascii=False,separators=(",",":"));
print("雙屬性",len(out),"隻；沒資料",len(set(mine)-set(slot)),"隻；主屬性和 PokeAPI 第一屬性不同",len(diff),"隻：",[(a,b,c) for a,b,c in diff])
