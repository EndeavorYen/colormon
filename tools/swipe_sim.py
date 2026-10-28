# 用法：python3 tools/swipe_sim.py [每組次數] ；環境變數 SWIPE_CFG='{ringNeed:5}' 可覆寫 swipe 設定，SITE_DIR 指向別的網站資料夾做比較
# 合成畫面測試：把「手」畫在假的相機畫面上，餵給真正的 LiteMotion 和 motionActions，統計誤觸與漏判
import asyncio,time,subprocess,sys,json
from playwright.async_api import async_playwright
PORT=8780
srv=subprocess.Popen(['python3','-m','http.server',str(PORT)],cwd=__import__('os').environ.get('SITE_DIR',str(__import__('pathlib').Path(__file__).resolve().parent.parent/'site')),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
JS=r"""
window.SIM=(()=>{
  const FW=192,FH=144;
  const cv=document.createElement('canvas');cv.width=FW;cv.height=FH;const ctx=cv.getContext('2d');
  let seed=1;const rnd=()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};
  const R=(a,b)=>a+(b-a)*rnd();
  function bgCanvas(kind){
    const b=document.createElement('canvas');b.width=FW+8;b.height=FH+8;const c=b.getContext('2d');
    const base=kind==='wood'?[165,128,100]:kind==='flat'?[205,200,190]:[112,104,96];
    c.fillStyle=`rgb(${base})`;c.fillRect(0,0,b.width,b.height);
    const amp=kind==='wood'?16:kind==='flat'?2:34;
    for(let i=0;i<500;i++){const g=R(-amp,amp);c.fillStyle=`rgb(${base[0]+g},${base[1]+g},${base[2]+g})`;c.fillRect(R(0,b.width),R(0,b.height),R(2,12),R(2,10));}
    return b;
  }
  function geom(){
    const v=document.getElementById('arVideo'),s=document.getElementById('scene').getBoundingClientRect();
    const vw=v.videoWidth,vh=v.videoHeight,k=Math.max(s.width/vw,s.height/vh),dw=vw*k,dh=vh*k;
    const m=document.getElementById('mon').getBoundingClientRect(),h=document.getElementById('hand').getBoundingClientRect();
    return {s,dw,dh,mon:{x:m.left-s.left+m.width/2,y:m.top-s.top+m.height/2},ball:{x:h.left-s.left+h.width/2,y:h.top-s.top+h.height/2},
      toC:(x,y)=>[((x+(dw-s.width)/2)/dw)*FW,((y+(dh-s.height)/2)/dh)*FH],px:(p)=>p/dw*FW};
  }
  function drawHand(g,x,y,w){
    const [cx,cy]=g.toC(x,y),rw=g.px(w)/2,rh=rw*1.3;
    ctx.save();ctx.translate(cx,cy);
    const gr=ctx.createRadialGradient(-rw*.2,-rh*.2,rw*.1,0,0,rw*1.1);gr.addColorStop(0,'rgb(224,170,140)');gr.addColorStop(1,'rgb(176,124,98)');
    ctx.fillStyle=gr;ctx.beginPath();ctx.ellipse(0,0,rw,rh,0,0,7);ctx.fill();
    ctx.strokeStyle='rgb(140,92,72)';ctx.lineWidth=Math.max(1,rw*.06);
    for(const [a,b,c2,d] of [[-.5,-.2,.5,-.1],[-.4,.1,.45,.2],[-.2,.45,.3,.4],[-.1,-.7,-.05,-.1]]){ctx.beginPath();ctx.moveTo(a*rw,b*rh);ctx.lineTo(c2*rw,d*rh);ctx.stroke();}
    ctx.restore();
  }
  /* 背景光影：flicker 整體忽明忽暗（日光燈、自動曝光）、shadow 軟邊的陰影掃過、dapple 樹葉縫隙的光斑亂跑、drift 曝光慢慢變、mixed 小閃爍加光斑 */
  function makeLight(kind){
    const L={kind,i:0,spots:[]};
    if(kind==='dapple'||kind==='mixed')for(let k=0;k<7;k++)L.spots.push({x:R(0,FW),y:R(0,FH),r:R(9,16)});
    return L;
  }
  function lightField(L){
    const mul=new Float32Array(FW).fill(1),add=new Float32Array(FW*FH);let gain=1;
    if(!L)return {mul,add,gain};
    const i=L.i++;
    if(L.kind==='flicker')gain=1+R(-.12,.12);
    if(L.kind==='mixed')gain=1+R(-.06,.06);
    if(L.kind==='drift')gain=1+0.006*i;
    if(L.kind==='shadow'){const cx=((i*8+L.ph0)%(FW+120))-60;for(let x=0;x<FW;x++){const d=Math.abs(x-cx),a=d<22?1:d<48?1-(d-22)/26:0;mul[x]=1-.38*a;}}
    if(L.kind==='dapple'||L.kind==='mixed'){
      for(const sp of L.spots){sp.x+=R(-9,9);sp.y+=R(-9,9);sp.x=(sp.x+FW)%FW;sp.y=(sp.y+FH)%FH;
        const x0=Math.max(0,Math.floor(sp.x-sp.r*2)),x1=Math.min(FW-1,Math.ceil(sp.x+sp.r*2)),y0=Math.max(0,Math.floor(sp.y-sp.r*2)),y1=Math.min(FH-1,Math.ceil(sp.y+sp.r*2));
        for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){const q=((x-sp.x)**2+(y-sp.y)**2)/(sp.r*sp.r);add[y*FW+x]+=45*Math.exp(-q);}}
    }
    return {mul,add,gain};
  }
  function frame(bg,jit,hands,g,L){
    const [dx,dy]=jit;ctx.drawImage(bg,-4+dx,-4+dy);
    for(const h of hands) drawHand(g,h.x,h.y,h.w);
    const id=ctx.getImageData(0,0,FW,FH),d=id.data,lf=lightField(L);
    for(let y=0;y<FH;y++)for(let x=0;x<FW;x++){const i=(y*FW+x)*4,m=lf.gain*lf.mul[x],a=lf.add[y*FW+x],n=(rnd()-.5)*8;   // 光影＋感光元件雜訊
      d[i]=d[i]*m+a+n;d[i+1]=d[i+1]*m+a+n;d[i+2]=d[i+2]*m+a+n;}
    ctx.putImageData(id,0,0);return cv;
  }
  const lerp=(a,b,t)=>a+(b-a)*t, clamp=(t)=>Math.max(0,Math.min(1,t));
  /* 各種手的路徑：回傳 (第 i 格, 共 n 格) → 手的位置 */
  const PATHS={
    waveMon:(p,g)=>{const A=R(70,130),ph=R(0,6.28),y0=g.mon.y+R(-30,30),w=p.w;return {n:20,at:i=>({x:g.mon.x+A*Math.sin(i*.1/.6*6.283+ph),y:y0+15*Math.sin(i*.7),w})};},
    waveLow:(p,g)=>{const A=R(70,130),ph=R(0,6.28),y0=g.mon.y+p.drop,w=p.w;return {n:20,at:i=>({x:g.mon.x+A*Math.sin(i*.1/.6*6.283+ph),y:y0+15*Math.sin(i*.7),w})};},
    sideUp:(p,g)=>{const w=p.w,side=rnd()<.5?-1:1,ph=R(0,6.28),off=w/2+p.gap;return {n:20,at:i=>({x:g.ball.x+side*off,y:g.ball.y-50+90*Math.sin(i*.1/.7*6.283+ph),w})};},
    edgeSweep:(p,g)=>{const w=p.w,dir=rnd()<.5?1:-1,yy=g.ball.y-(w*1.3/2+p.gap),A=170;return {n:16,at:i=>({x:g.ball.x+dir*(-A+2*A*i/15),y:yy+R(-4,4),w})};},
    idle:(p,g)=>({n:p.n||30,at:i=>null}),
    throwTrue:(p,g)=>{ // 手從球下方或旁邊進來，蓋住球、停一下，再往上甩
      const w=p.w,sx=g.ball.x+R(-60,60),sy=g.ball.y+(p.side?R(10,40):95),ex=p.side?g.ball.x+(rnd()<.5?-150:150):sx;
      const ap=p.approach,hold=p.hold,fl=p.flick,tx=g.ball.x+R(-8,8),ty=g.ball.y+R(-6,6);
      return {n:ap+hold+fl+6,at:i=>{
        let x,y;
        if(i<ap){const t=(i+1)/ap;x=lerp(p.side?ex:sx,tx,t);y=lerp(p.side?g.ball.y:sy,ty,t);}
        else if(i<ap+hold){x=tx+R(-2.5,2.5);y=ty+R(-2.5,2.5);}
        else{const t=(i-ap-hold+1)/fl;x=tx+R(-6,6);y=ty-190*Math.min(1.4,t);}
        return {x,y,w};}};}
  };
  async function runTrial(kind,p,bgKind,sd){
    seed=sd;const g=geom(),bg=bgCanvas(bgKind),path=PATHS[kind](p,g),L=p.light?makeLight(p.light):null;if(L)L.ph0=R(0,200);
    const M=new LiteMotion(96,72);let throws=0,hits=0,throwFrame=-1,shieldFrames=0,maxN=0,runs=0,runMax=0;const mc=sceneToVideo(g.mon.x,g.mon.y);
    window.__thr=()=>{throws++;if(throwFrame<0)throwFrame=cur;};window.__hit=()=>{hits++;};
    if(typeof resetSwipe==='function')resetSwipe();else{SWIPE.hist=[];SWIPE.touchT=0;SWIPE.cool=0;document.getElementById('hand').classList.remove('touched');}
    let cur=0;
    for(let i=0;i<path.n+4;i++){
      cur=i;const jit=rnd()<.3?[Math.round(R(-1,1)),Math.round(R(-1,1))]:[0,0];
      const hand=i<path.n?path.at(i):null;
      M.grab(frame(bg,jit,hand?[hand]:[],g,L));
      motionActions(1000+i*100,M);
      const rn=M.region(mc.x,mc.y,.2,.24).n;maxN=Math.max(maxN,rn);
    }
    return {throws,hits,throwFrame,maxN};
  }
  return {runTrial};
})();
0
"""
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(args=["--use-fake-ui-for-media-stream","--use-fake-device-for-media-stream"])
        ctx=await b.new_context(permissions=["camera"],viewport={"width":390,"height":844}); pg=await ctx.new_page(); errs=[]
        pg.on("pageerror",lambda e:errs.append(str(e)))
        await pg.goto(f"http://localhost:{PORT}/"); await pg.wait_for_timeout(700)
        await pg.evaluate("localStorage.setItem('colormon-ball-mode','0')"); await pg.reload(); await pg.wait_for_timeout(700)
        await pg.click("[data-s=night]"); await pg.wait_for_selector("#throwBtn:not([disabled])",timeout=15000); await pg.wait_for_timeout(1500)
        # 不開真的相機（假相機的畫面會自己動）；用假的影片尺寸和鏡頭模式版面，只吃合成畫面
        await pg.evaluate("Object.defineProperty($('arVideo'),'videoWidth',{get:()=>640});Object.defineProperty($('arVideo'),'videoHeight',{get:()=>480});$('scene').classList.add('ar');SHIELD.hp=3;0")
        await pg.evaluate(JS)
        await pg.evaluate("window.onBallThrown=()=>{window.__thr&&window.__thr()};window.onBallLanded=()=>{};window.hitShield=()=>{window.__hit&&window.__hit()};0")
        import os
        extra=os.environ.get('SWIPE_CFG')
        if extra: await pg.evaluate(f"CFG.swipe={{...(CFG.swipe||{{}}),...{extra}}};0"); print('swipe 設定覆寫',extra)
        if os.environ.get('SIM_JS'): await pg.evaluate(os.environ['SIM_JS']+';0'); print('SIM_JS',os.environ['SIM_JS'])
        N=int(sys.argv[1]) if len(sys.argv)>1 else 10
        info=await pg.evaluate("(()=>{const g=document.getElementById('scene').getBoundingClientRect(),m=document.getElementById('mon').getBoundingClientRect(),h=document.getElementById('hand').getBoundingClientRect();return {scene:[g.width,g.height],mon:[m.width,m.height,m.top-g.top],ball:[h.width,h.top-g.top]}})()")
        print("場景尺寸",info)
        async def many(label,kind,params,bg='contrast'):
            r=await pg.evaluate("async ([kind,params,bg,N])=>{let tt=0,th=0,tot=0,fr=[],mx=[];for(const p of params)for(let k=0;k<N;k++){const r=await SIM.runTrial(kind,p,bg,1000*tot+k*7+13);tot++;if(r.throws)tt++;if(r.hits)th++;if(r.throwFrame>=0)fr.push(r.throwFrame);mx.push(r.maxN);}mx.sort((a,b)=>a-b);return {tot,tt,th,fr,mx:[mx[0],mx[mx.length>>2],mx[mx.length>>1],mx[(mx.length*3)>>2],mx[mx.length-1]]}}",[kind,params,bg,N])
            avg=(sum(r['fr'])/len(r['fr'])*0.1) if r['fr'] else None
            print(f"{label:34} 試驗{r['tot']:3}  丟出{r['tt']:3}（{r['tt']/r['tot']*100:4.0f}%）  打到護盾{r['th']:3}（{r['th']/r['tot']*100:4.0f}%）"+(f"  平均第{avg:.1f}秒丟出" if avg else "")+f"  護盾區最大變化量(最小/25%/中位/75%/最大)={r['mx']}")
            return r
        W=[90,130,170]
        res={}
        res['idle']=await many("沒人（只有手持晃動）","idle",[{}])
        res['waveMon']=await many("在寶可夢上揮手（打護盾）","waveMon",[{'w':w} for w in W])
        if os.environ.get('DETAIL'):
            for w in W:
                for d in (90,140,190): await many(f'   waveLow w={w} drop={d}','waveLow',[{'w':w,'drop':d}])
        res['waveLow']=await many("揮手位置偏低（離球 60~180px）","waveLow",[{'w':w,'drop':d} for w in W for d in (90,140,190)])
        res['sideUp']=await many("手在球旁邊上下揮（邊緣擦過）","sideUp",[{'w':w,'gap':g} for w in W for g in (10,30,50)])
        res['edge']=await many("手橫掃過球的上緣","edgeSweep",[{'w':w,'gap':g} for w in W for g in (10,30,50)])
        tp=[{'w':w,'approach':a,'hold':h,'flick':f,'side':s} for w in W for a in (2,4) for h in (0,3) for f in (3,4) for s in (False,True)]
        res['true']=await many("真的把手放在球上再往上甩","throwTrue",tp)
        res['trueWood']=await many("同上，但背景和膚色接近（木桌）","throwTrue",tp,bg='wood')
        if os.environ.get('NOLIGHT')!='1':
            print('--- 背景光影亂（畫面裡沒有手）---')
            for lab,lk in [("整體忽明忽暗（±12%）","flicker"),("軟邊陰影掃過","shadow"),("樹葉光斑亂跑","dapple"),("曝光慢慢變亮 12%","drift"),("小閃爍＋光斑","mixed")]:
                res['L_'+lk]=await many(f"  {lab}","idle",[{'n':30,'light':lk}])
            print('--- 背景光影亂＋手（要仍然判得出來）---')
            res['L_wave']=await many("  光斑＋閃爍中，在寶可夢上揮手","waveMon",[{'w':w,'light':'mixed'} for w in W])
            res['L_true']=await many("  光斑＋閃爍中，放在球上再往上甩","throwTrue",[{'w':w,'approach':a,'hold':h,'flick':f,'side':s,'light':'mixed'} for w in W for a in (2,4) for h in (0,3) for f in (3,4) for s in (False,True)])
            res['L_true_sh']=await many("  軟邊陰影掃過時，放在球上再往上甩","throwTrue",[{'w':w,'approach':a,'hold':h,'flick':f,'side':s,'light':'shadow'} for w in W for a in (2,4) for h in (0,3) for f in (3,4) for s in (False,True)])
        res['trueFlat']=await many("同上，但背景是平坦的白牆","throwTrue",tp,bg='flat')
        print("errors",errs)
        pass
        await b.close()
try: asyncio.run(main())
finally: srv.kill()
