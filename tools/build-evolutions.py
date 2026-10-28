#!/usr/bin/env python3
"""從 PokeAPI 的公開資料（GitHub: PokeAPI/api-data）整理進化關係，輸出 site/data/evolutions.json。
格式：{"2":{"from":1,"to":[3]}, ...}  只記有進化關係的寶可夢；沒有的不用寫。
用法：python3 tools/build-evolutions.py [最大編號，預設 1025]"""
import json,sys,urllib.request,concurrent.futures as cf,os
N=int(sys.argv[1]) if len(sys.argv)>1 else 1025
U="https://raw.githubusercontent.com/PokeAPI/api-data/master/data/api/v2/pokemon-species/%d/index.json"
def get(i):
    for t in range(4):
        try:
            with urllib.request.urlopen(U%i,timeout=30) as r:
                d=json.load(r);f=d.get("evolves_from_species")
                return i,(int(f["url"].rstrip("/").split("/")[-1]) if f else None)
        except Exception as e:
            err=e
    raise SystemExit(f"抓不到 #{i}: {err}")
frm={}
with cf.ThreadPoolExecutor(16) as ex:
    for i,f in ex.map(get,range(1,N+1)): frm[i]=f
out={}
for i,f in frm.items():
    if f: out.setdefault(str(i),{})["from"]=f; out.setdefault(str(f),{}).setdefault("to",[]).append(i)
for k,v in out.items():
    if "to" in v: v["to"].sort()
out={k:out[k] for k in sorted(out,key=int)}
p=os.path.join(os.path.dirname(__file__),"..","site","data","evolutions.json")
json.dump(out,open(p,"w"),ensure_ascii=False,separators=(",",":"));open(p,"a").write("\n")
print("完成：",len(out),"隻有進化關係 →",os.path.normpath(p))
