#!/usr/bin/env python3
"""從 PokeAPI 公開資料（GitHub: PokeAPI/api-data）整理每隻寶可夢的「分類」和「圖鑑說明」（繁體中文），
輸出 site/data/dexinfo.json：{"6":{"g":"火焰寶可夢","t":"..."}}。
優先用 zh-hant（繁體）；沒有繁體的用 zh-hans（簡體，經 OpenCC 轉繁體，需要 pip install opencc-python-reimplemented）。
說明有很多遊戲版本，取最新一版。
官方沒有中文說明的（約 300 隻，大多是第 2～4、9 代），用 tools/data/dexinfo-translated.json：從英文說明翻成適合小朋友的繁體中文（會標 "tr":1）。用法：python3 tools/build-dexinfo.py"""
import json,os,re,sys,urllib.request,concurrent.futures as cf
N=1025
U="https://raw.githubusercontent.com/PokeAPI/api-data/master/data/api/v2/pokemon-species/%d/index.json"
try:
    from opencc import OpenCC; s2t=OpenCC("s2twp").convert
except Exception: s2t=None
def get(i):
    for _ in range(4):
        try:
            with urllib.request.urlopen(U%i,timeout=30) as r: return i,json.load(r)
        except Exception as e: err=e
    raise SystemExit(f"抓不到 #{i}: {err}")
def clean(t): return re.sub(r"\s+","",t.replace("­",""))      # 中文說明裡的換行、空白都拿掉
out={};stat={"hant":0,"hans":0,"none":0}
with cf.ThreadPoolExecutor(16) as ex:
    for i,d in ex.map(get,range(1,N+1)):
        g={x["language"]["name"]:x["genus"] for x in d.get("genera",[])}
        fl=[x for x in d.get("flavor_text_entries",[]) if x["language"]["name"] in ("zh-hant","zh-hans")]
        hant=[x for x in fl if x["language"]["name"]=="zh-hant"]; hans=[x for x in fl if x["language"]["name"]=="zh-hans"]
        e={}
        if g.get("zh-hant"): e["g"]=g["zh-hant"]
        elif g.get("zh-hans") and s2t: e["g"]=s2t(g["zh-hans"])
        if hant: e["t"]=clean(hant[-1]["flavor_text"]);stat["hant"]+=1
        elif hans and s2t: e["t"]=s2t(clean(hans[-1]["flavor_text"]));stat["hans"]+=1
        else: stat["none"]+=1
        if e: out[str(i)]=e
TR=json.load(open(os.path.join(os.path.dirname(__file__),"data","dexinfo-translated.json")))
for k,v in TR.items():
    e=out.setdefault(k,{})
    if "t" not in e: e["t"]=v["t"];e["tr"]=1
    if "g" not in e and v.get("g"): e["g"]=v["g"]
out={k:out[k] for k in sorted(out,key=int)}
p=os.path.join(os.path.dirname(__file__),"..","site","data","dexinfo.json")
json.dump(out,open(p,"w"),ensure_ascii=False,separators=(",",":"));open(p,"a").write("\n")
print("完成：",len(out),"隻；說明 繁體",stat["hant"],"、簡體轉繁",stat["hans"],"、用英文翻譯",sum(1 for v in out.values() if v.get("tr")),"、還是沒有",sum(1 for v in out.values() if "t" not in v),"；分類",sum(1 for v in out.values() if "g" in v))
