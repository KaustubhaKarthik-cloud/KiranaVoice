const $=s=>document.querySelector(s);const P=new URLSearchParams(location.search);
if(P.get('layout')==='vertical')document.body.classList.add('vertical');if(P.get('layout')==='wide')document.body.classList.add('wide');
let ws,cfg,t0,tick,audioCtx,micStream;const U={kg:'kg',L:'L',pcs:'',packet:'packet'};
fetch('/api/config').then(r=>r.json()).then(c=>{cfg=c;$('#mode').textContent=c.mode==='mock'?'MOCK mode · 0 credits':'LIVE Gnani';$('#footmode').textContent='WhatsApp sender: '+c.sender;if(c.mode==='live')$('#mic').classList.remove('hidden');if(P.get('autoplay'))answer().then(()=>setTimeout(playScript,600));});
function add(role,text){const d=document.createElement('div');d.className='msg '+role;d.innerHTML='<b>'+(role==='agent'?'🤖 Agent':'🧑 Customer')+'</b>';d.append(text);$('#transcript').append(d);$('#transcript').scrollTop=1e9}
function play(b64){if(P.get('mute'))return;try{new Audio('data:audio/wav;base64,'+b64).play().catch(()=>{})}catch(e){}}
let prev={};function items(list,state){$('#state').textContent=state;const ul=$('#items');ul.innerHTML='';if(!list.length){ul.innerHTML='<li class="muted">No items yet</li>';return}
 list.forEach(i=>{const li=document.createElement('li');const q=i.qty==null?'?':(+i.qty);li.innerHTML='<span></span><strong></strong>';li.children[0].textContent=i.name;li.children[1].textContent=q+' '+(U[i.unit]??i.unit);if(prev[i.name]!==q)li.classList.add('flash');prev[i.name]=q;ul.append(li)})}
function order(ev){const w=$('#wa');w.innerHTML='';const b=document.createElement('div');b.className='bubble';b.textContent=ev.summary;w.append(b);
 if(ev.send&&ev.send.wa_me){const a=document.createElement('a');a.href=ev.send.wa_me;a.target='_blank';a.rel='noopener';a.textContent='Open in WhatsApp (wa.me)';const p=document.createElement('div');p.style.marginTop='8px';p.append(a,' · sent via '+ev.send.sender+(ev.send.ok?'':' (FAILED)'));w.append(p)}}
function answer(){return new Promise(res=>{ws=new WebSocket((location.protocol==='https:'?'wss':'ws')+'://'+location.host+'/ws');
 ws.onopen=()=>{ws.send(JSON.stringify({type:'answer'}));$('#incoming').classList.add('hidden');$('#incall').classList.remove('hidden');t0=Date.now();tick=setInterval(()=>{const s=((Date.now()-t0)/1000)|0;$('#timer').textContent=String(s/60|0).padStart(2,'0')+':'+String(s%60).padStart(2,'0')},500);res()};
 ws.onmessage=e=>{const ev=JSON.parse(e.data);chain=chain.then(()=>handle(ev))}})}
// demo pacing: customer bubble -> wait reply_delay -> agent bubble -> then card update
const RD=+(P.get('reply_delay')??(P.get('autoplay')?1500:0));let chain=Promise.resolve(),pendingItems=null;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function handle(ev){if(ev.type==='transcript'){add(ev.role,ev.text);if(ev.audio)play(ev.audio);
  if(ev.role==='customer'&&RD)await sleep(RD);
  if(ev.role==='agent'&&pendingItems){items(...pendingItems);pendingItems=null}}
 else if(ev.type==='items')pendingItems=[ev.items,ev.state];else if(ev.type==='order')order(ev);else if(ev.type==='error')add('agent','[⚠ '+ev.where+' error: '+ev.message+']')}
$('#answer').onclick=answer;
$('#sayform').onsubmit=e=>{e.preventDefault();const v=$('#say').value.trim();if(v&&ws){ws.send(JSON.stringify({type:'say',text:v}));$('#say').value=''}};
async function playScript(){for(const line of cfg.demo_script){await new Promise(r=>setTimeout(r,+(P.get('gap')||1800)));ws.send(JSON.stringify({type:'say',text:line}))}}
$('#script').onclick=playScript;
$('#hangup').onclick=()=>{if(ws){ws.send(JSON.stringify({type:'hangup'}));ws.close()}clearInterval(tick);if(micStream)micStream.getTracks().forEach(t=>t.stop());$('#calltop')};
let proc=null;
$('#mic').onclick=async()=>{ // live: browser mic -> 16 kHz 16-bit PCM -> server -> Gnani Prisma realtime
 if(proc){ws.send(JSON.stringify({type:'mic_stop'}));proc.disconnect();proc=null;micStream.getTracks().forEach(t=>t.stop());$('#mic').classList.remove('on');$('#mic').textContent='🎙 Mic (live)';return}
 try{audioCtx=audioCtx||new AudioContext({sampleRate:16000});micStream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true}})}catch(e){add('agent','[mic unavailable: '+e.name+']');return}
 ws.send(JSON.stringify({type:'mic_start',sample_rate:audioCtx.sampleRate}));
 const src=audioCtx.createMediaStreamSource(micStream);proc=audioCtx.createScriptProcessor(512,1,1);src.connect(proc);proc.connect(audioCtx.destination);
 proc.onaudioprocess=e=>{const f=e.inputBuffer.getChannelData(0);const i16=new Int16Array(f.length);for(let k=0;k<f.length;k++)i16[k]=Math.max(-1,Math.min(1,f[k]))*32767;if(ws&&ws.readyState===1)ws.send(i16.buffer)};
 $('#mic').classList.add('on');$('#mic').textContent='⏹ Stop mic'};
