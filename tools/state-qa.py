"""狀態機 QA：在丟球、分析、出場、對戰的各個時間點離開／按返回／切到背景／重新整理，確認不會被拉回舊畫面、不會在背景多抓"""
import asyncio,time,subprocess,sys,json
from playwright.async_api import async_playwright
# 用法：python3 tools/state-qa.py [port]（需要 playwright）；SITE_DIR 可指向別的網站資料夾
import os,pathlib
PORT=int(sys.argv[1]) if len(sys.argv)>1 else 8790
SITE=os.environ.get('SITE_DIR',str(pathlib.Path(__file__).resolve().parent.parent/'site'))
srv=subprocess.Popen(['python3','-m','http.server',str(PORT)],cwd=SITE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
RES=[]
def ok(name,cond,info=""):
    RES.append((name,bool(cond),info));print(("✅" if cond else "❌"),name,info,flush=True)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch();ctx=await b.new_context(viewport={"width":390,"height":844});pg=await ctx.new_page();errs=[]
        pg.on("pageerror",lambda e:errs.append(str(e)))
        await pg.goto(f"http://localhost:{PORT}/");await pg.evaluate("localStorage.clear();localStorage.setItem('colormon-ball-mode','0')");await pg.reload();await pg.wait_for_timeout(1200)
        await pg.evaluate("window.speechSynthesis.speak=()=>{};EYE.need=999;0")
        st=lambda: pg.evaluate("({screen,busy,scanning,cur:!!current,bt:BT.on,dex:Object.keys(dex).length,hash:location.hash,illegal:GAME.illegal,thr:$('throwBtn').disabled,hand:!$('hand').hidden,ball:!$('ball').hidden,monOp:getComputedStyle($('mon')).opacity,battle:!$('battle').hidden})")
        async def enc(rar=1,test=False):
            await pg.evaluate(f"current=null;busy=false;go('camera');(()=>{{const m=MONS.filter(x=>x.rarity==={rar})[Math.floor(Math.random()*40)];startEncounter([{{rgb:[200,60,60]}}],{{mon:m,sim:80,silhouette:false,test:{str(test).lower()}}});}})();0")
            for _ in range(80):
                await pg.wait_for_timeout(100)
                if await pg.evaluate("screen==='encounter'&&!$('throwBtn').disabled&&!BT.on"):return True
            return False
        async def hide(h):
            await pg.evaluate(f"Object.defineProperty(document,'hidden',{{configurable:true,get:()=>{str(h).lower()}}});document.dispatchEvent(new Event('visibilitychange'));0")
        # ---- S1/S2/S3：丟球中離開 ----
        for how in ("back","dex","hidden"):
            for at in (200,900,1800,3200,5200,7300):
                if not await enc(): ok(f"丟球{how}@{at} 進遭遇",False);continue
                d0=await pg.evaluate("Object.keys(dex).length")
                await pg.evaluate("misses=99;$('throwBtn').click();0");await pg.wait_for_timeout(at)
                saved_before=await pg.evaluate("Object.keys(dex).length")>d0
                if how=="back":await pg.click("#backBtn")
                elif how=="dex":await pg.click("#dexBtn")
                else:await hide(True)
                await pg.wait_for_timeout(9000)
                s=await st()
                if how=="back":
                    ok(f"丟球中按返回 @{at}ms → 留在拍照、沒跳到抓到了",s["screen"]=="camera" and not s["busy"] and not s["cur"],f"{s['screen']} 已存={saved_before}")
                elif how=="dex":
                    ok(f"丟球中開圖鑑 @{at}ms → 留在圖鑑",s["screen"]=="dex" and not s["busy"],s["screen"])
                    await pg.click("#dexBack");await pg.wait_for_timeout(800);s=await st()
                    if s["cur"]:ok(f"  回去抓寶可夢 → 回到遭遇、可以再丟",s["screen"]=="encounter" and not s["thr"] and s["hand"] and not s["ball"] and float(s["monOp"])>.9,json.dumps({k:s[k] for k in ('screen','thr','hand','ball','monOp')}))
                    else:ok(f"  (已在離開前抓到) 回去 → 拍照畫面",s["screen"]=="camera",s["screen"])
                else:
                    ok(f"丟球中切到背景 @{at}ms → 球取消、沒跳畫面",s["screen"] in("encounter","camera") and s["screen"]!="result",s["screen"])
                    await hide(False);await pg.wait_for_timeout(600);s=await st()
                    if s["cur"]:ok(f"  回來 → 寶可夢還在、可以再丟",s["screen"]=="encounter" and not s["thr"] and s["hand"] and not s["ball"] and float(s["monOp"])>.9 and not s["busy"],json.dumps({k:s[k] for k in ('thr','hand','ball','monOp','busy')}))
                    await pg.evaluate("go('camera')")
                d1=await pg.evaluate("Object.keys(dex).length")
                ok(f"  背景沒有多抓",d1-d0<= (1 if saved_before else 0),f"{d0}->{d1}")
        # ---- S4/S5/S6：分析中離開 ----
        for how in ("back","hidden"):
            for at in (100,500,1200,2200,3000):
                await pg.evaluate("current=null;busy=false;go('camera');EYE.quest={color:'green',until:Date.now()+600000};questUI();0")
                await pg.click("[data-s=grass]");await pg.wait_for_timeout(at)
                was=await pg.evaluate("scanning")
                if how=="back":await pg.go_back()
                else:await hide(True)
                await pg.wait_for_timeout(5000)
                if how=="hidden":await hide(False);await pg.wait_for_timeout(300)
                s=await st();q=await pg.evaluate("!!questActive()")
                ok(f"分析中{'按返回' if how=='back' else '切到背景'} @{at}ms → 不會跳到遭遇"+("" if was else "（離開前已分析完，進遭遇是對的）"),(s["screen"] in("camera","explore") and not s["scanning"] and not s["cur"]) if was else True,s["screen"])
                await pg.evaluate("go('camera')")
        # 任務：真拍才算，範例不算；改用 real=true 中途離開
        await pg.evaluate("current=null;busy=false;go('camera');EYE.quest={color:'red',until:Date.now()+600000};window.__red=(()=>{const c=document.createElement('canvas');c.width=600;c.height=800;const g=c.getContext('2d');g.fillStyle='#d32f2f';g.fillRect(0,0,600,800);return c.toDataURL('image/jpeg')})();startScan(__red,true);0")
        await pg.wait_for_timeout(1500);await pg.go_back();await pg.wait_for_timeout(4000)
        ok("拍到任務顏色但分析中離開 → 任務還在（沒有白白用掉）",await pg.evaluate("!!questActive()"),await pg.evaluate("screen"))
        await pg.evaluate("startScan(__red,true);0");await pg.wait_for_timeout(7000)
        ok("  再拍一次完整跑完 → 任務完成、進遭遇",await pg.evaluate("!questActive()&&screen==='encounter'"),await pg.evaluate("screen"))
        # ---- S7：五星出場中離開 ----
        await pg.evaluate("[1,4,7,25].forEach(i=>dex[i]=dex[i]||{n:1,first:1,last:1});0")
        for at in (500,1500,2500):
            await pg.evaluate("current=null;busy=false;go('camera');(()=>{const m=MONS.find(x=>x.rarity===5);startEncounter([{rgb:[200,200,60]}],{mon:m,sim:80,silhouette:false,test:true});})();0")
            await pg.wait_for_timeout(at);await pg.click("#dexBtn");await pg.wait_for_timeout(4000)
            s=await st();ok(f"五星出場中開圖鑑 @{at}ms → 對戰沒有在背景跳出",s["screen"]=="dex" and not s["bt"] and not s["battle"],json.dumps({k:s[k] for k in ('screen','bt','battle')}))
            await pg.click("#dexBack");await pg.wait_for_timeout(900);s=await st()
            sh=await pg.evaluate("SHIELD.total")
            ok("  回去 → 遭遇、護盾在、可以丟",s["screen"]=="encounter" and not s["thr"] and sh==5 and float(s["monOp"])>.9,json.dumps({"screen":s["screen"],"thr":s["thr"],"shield":sh,"op":s["monOp"]}))
        # ---- S8：對戰中按返回 ----
        await pg.evaluate("current=null;busy=false;go('camera');(()=>{const m=MONS.find(x=>x.rarity===4);startEncounter([{rgb:[200,200,60]}],{mon:m,sim:80,silhouette:false,test:true});})();0")
        for _ in range(60):
            await pg.wait_for_timeout(100)
            if await pg.evaluate("BT.live"):break
        await pg.go_back();await pg.wait_for_timeout(1200);s=await st()
        ok("對戰中按返回鍵 → 跳過對戰、留在遭遇可以丟",s["screen"]=="encounter" and not s["bt"] and not s["thr"],json.dumps({k:s[k] for k in ('screen','bt','thr')}))
        # ---- S9：丟球中重新整理 ----
        await enc();d0=await pg.evaluate("Object.keys(lsGet(dexKey(PROFILES.cur),{})).length")
        await pg.evaluate("misses=99;$('throwBtn').click();0");await pg.wait_for_timeout(1500)
        await pg.reload();await pg.wait_for_timeout(9000);s=await st()
        ok("丟球中重新整理 → 回首頁、沒有接著抓",s["screen"]=="camera" and s["hash"]=="#camera" and s["dex"]==d0,json.dumps({k:s[k] for k in ('screen','hash','dex')})+f" 之前存了 {d0}")
        await pg.evaluate("window.speechSynthesis.speak=()=>{};EYE.need=999;0")
        # ---- S11：遭遇中不會跳出休息提醒、任務 ----
        await enc();await pg.evaluate("EYE.play=30*60000;EYE.last=Date.now();EYE.questPlay=99*60000;eyeTick()");await pg.wait_for_timeout(500)
        ok("遭遇中不跳出休息提醒／任務",await pg.evaluate("$('restPanel').hidden&&$('questPanel').hidden"))
        await pg.evaluate("EYE.play=0;EYE.questPlay=0;0")
        # ---- S12：連點丟球只丟一次 ----
        await enc();await pg.evaluate("window.__n=0;const o=throwBall;window.throwBall=function(...a){__n++;return o(...a)};misses=0;for(let i=0;i<5;i++)$('throwBtn').click();0")
        await pg.wait_for_timeout(300);ok("連點丟球：只有第一下有作用",await pg.evaluate("busy&&$('throwBtn').disabled"))
        await pg.wait_for_timeout(9000);await pg.evaluate("go('camera')")
        # ---- S13：逃跑 ----
        await enc();await pg.click("#runBtn");await pg.wait_for_timeout(200);await pg.click("#runBtn");await pg.wait_for_timeout(1200);s=await st()
        ok("逃跑（按兩下）→ 回拍照、遭遇結束",s["screen"]=="camera" and not s["cur"])
        # ---- S14：抓到後各種返回 ----
        await enc();await pg.evaluate("misses=99;$('throwBtn').click();0")
        for _ in range(60):
            await pg.wait_for_timeout(250)
            if await pg.evaluate("screen==='result'"):break
        await pg.go_back();await pg.wait_for_timeout(600);s=await st()
        ok("抓到了畫面按返回 → 不會回到已經抓完的遭遇",s["screen"]!="encounter",s["screen"])
        # ---- 使用者回報的情況：丟球中離開 → 任務提示跳出來 → 不能被拉回「抓到了」----
        await enc();await pg.evaluate("EYE.need=1;EYE.caught=1;misses=99;$('throwBtn').click();0");await pg.wait_for_timeout(1500)
        await pg.click("#backBtn");await pg.wait_for_timeout(1500)
        qp=await pg.evaluate("!$('questPanel').hidden")
        await pg.wait_for_timeout(8000);s=await st()
        ok("丟球中離開、任務提示跳出 → 之後不會被拉回「抓到了」",qp and s["screen"]=="camera",f"任務提示={qp} 畫面={s['screen']}")
        await pg.evaluate("$('questGo').click();EYE.need=999;0")
        # ---- 探索：找到後馬上離開 ----
        await pg.evaluate("current=null;busy=false;go('explore');0");await pg.wait_for_timeout(800)
        await pg.evaluate("foundPokemon();0");await pg.wait_for_timeout(300);await pg.evaluate("go('camera')");await pg.wait_for_timeout(3500)
        ok("探索「找到了」後馬上離開 → 不會突然開始分析",await pg.evaluate("screen==='camera'&&!scanning"),await pg.evaluate("screen"))
        # 全部：沒有不合法的切換、沒有錯誤
        s=await st()
        ok("整個測試沒有不合法的狀態切換",s["illegal"]==0,str(s["illegal"])+str(await pg.evaluate("GAME.log.filter(x=>x.illegal).map(x=>x.illegal)")))
        ok("沒有 JS 錯誤",not errs,str(errs[:3]))
        await b.close()
    n=sum(1 for r in RES if r[1]);print(f"\n通過 {n}/{len(RES)}")
    if n<len(RES):sys.exit(1)
try: asyncio.run(main())
finally: srv.kill()
