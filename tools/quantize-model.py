#!/usr/bin/env python3
"""把 TensorFlow.js 圖模型的 float32 權重量化成 uint8（檔案變成約 1/4），tfjs 載入時會自動還原。
用法：python3 tools/quantize-model.py 來源資料夾 輸出資料夾
（物品辨識用的 COCO-SSD lite 模型原本約 17MB，量化後約 4.5MB，辨識結果幾乎一樣）"""
import json,os,sys,numpy as np
src,dst=sys.argv[1],sys.argv[2]
m=json.load(open(os.path.join(src,"model.json")))
SZ={"float32":4,"int32":4,"bool":1,"uint8":1}
out=bytearray();weights=[]
for g in m["weightsManifest"]:
    buf=b"".join(open(os.path.join(src,p),"rb").read() for p in g["paths"]);off=0
    for w in g["weights"]:
        n=int(np.prod(w["shape"])) if w["shape"] else 1;nb=n*SZ[w["dtype"]];raw=buf[off:off+nb];off+=nb
        if w["dtype"]=="float32" and "quantization" not in w and n>16:
            a=np.frombuffer(raw,dtype="<f4");lo,hi=float(a.min()),float(a.max());sc=(hi-lo)/255 or 1.0
            q=np.clip(np.round((a-lo)/sc),0,255).astype(np.uint8)
            out+=q.tobytes();weights.append({**w,"quantization":{"dtype":"uint8","min":lo,"scale":sc,"original_dtype":"float32"}})
        else:
            out+=raw;weights.append(w)
    assert off==len(buf),(off,len(buf))
os.makedirs(dst,exist_ok=True)
SH=4*1024*1024;paths=[]
for i in range(0,len(out),SH):
    name=f"group1-shard{i//SH+1}of{(len(out)+SH-1)//SH}";open(os.path.join(dst,name),"wb").write(out[i:i+SH]);paths.append(name)
m["weightsManifest"]=[{"paths":paths,"weights":weights}]
json.dump(m,open(os.path.join(dst,"model.json"),"w"),separators=(",",":"))
print("量化完成：",round(len(out)/1e6,2),"MB，",len(paths),"個檔")
