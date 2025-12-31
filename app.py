"""
Kalon AI Chat - Professional UI
"""
import os, json, httpx, random, string, time
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, Response, stream_with_context

app = Flask(__name__)

CLERK_SESSION = os.environ.get("CLERK_SESSION", "")
CLERK_TOKEN = os.environ.get("CLERK_TOKEN", "")

CHARS = [
    {"id": "1", "name": "Cyra", "desc": "15yo, Friendly helper", "sid": "js7ehzx166wqvyw1kdqkbyxefx7ybtmp"},
    {"id": "2", "name": "Carmen", "desc": "28yo, Sports journalist", "sid": "js79z3q9d9y1y1wjnwht6xjy6h7yajed"},
    {"id": "3", "name": "Leila", "desc": "24yo, Artist", "sid": "js7c50sstmwddc94k649531nw97y98rt"},
    {"id": "4", "name": "Yuki", "desc": "24yo, Librarian", "sid": "js78d28dkza1axa5mad6erj6ad7ya57e"},
    {"id": "5", "name": "Mei", "desc": "19yo, Photographer", "sid": "js78tdrngtf3gq9cr9gg4w1q1s7ybc1h"},
    {"id": "6", "name": "Mia", "desc": "19yo, College girl", "sid": "js7ctvyrttqshcceaf275wd0es7ya60q"}
]

token_cache = {"jwt": None, "exp": 0}
histories = {}

def get_token():
    if token_cache["jwt"] and time.time() < token_cache["exp"]:
        return token_cache["jwt"]
    try:
        with httpx.Client(timeout=30) as c:
            r = c.post(f"https://clerk.kalon.ai/v1/client/sessions/{CLERK_SESSION}/tokens",
                params={"__clerk_api_version": "2025-11-10"}, data={"organization_id": ""},
                headers={"Origin": "https://www.kalon.ai", "Cookie": f"__client={CLERK_TOKEN}"})
            if r.status_code == 200:
                token_cache["jwt"] = r.json()["jwt"]
                token_cache["exp"] = time.time() + 45
                return token_cache["jwt"]
    except: pass
    return None

def rand_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

@app.route('/api/chars')
def api_chars():
    return jsonify(CHARS)

@app.route('/api/history/<did>/<sid>')
def api_history(did, sid):
    return jsonify(histories.get(f"{did}:{sid}", []))

@app.route('/api/history/<did>/<sid>', methods=['DELETE'])
def api_clear(did, sid):
    histories[f"{did}:{sid}"] = []
    return jsonify({"ok": True})


@app.route('/api/chat', methods=['POST'])
def api_chat():
    d = request.json
    msg, sid, name, did = d.get('msg',''), d.get('sid',''), d.get('name',''), d.get('did','anon')
    key = f"{did}:{sid}"
    if key not in histories: histories[key] = []
    histories[key].append({"role": "user", "msg": msg, "ts": datetime.now().isoformat()})
    
    def gen():
        token = get_token()
        if not token:
            yield f"data: {json.dumps({'err': 'token'})}\n\n"
            return
        payload = {
            "message": {"parts": [{"type": "text", "text": msg}], "id": rand_id(), "role": "user"},
            "sessionId": sid, "character": {"name": name},
            "conversationStyle": "immersive", "memory": "", "hornyLevel": "medium",
            "responseLength": "balanced", "model": "xai/grok-4-fast-non-reasoning"
        }
        full = []
        try:
            with httpx.Client(timeout=httpx.Timeout(60, read=300), http2=True) as c:
                with c.stream("POST", "https://www.kalon.ai/api/chat", json=payload, headers={
                    "Authorization": f"Bearer {token}", "Origin": "https://www.kalon.ai",
                    "Accept": "text/event-stream", "Content-Type": "application/json"
                }) as r:
                    for line in r.iter_lines():
                        if not line or not line.startswith("data:"): continue
                        data = line[5:].strip()
                        if data == "[DONE]": break
                        try:
                            obj = json.loads(data)
                            if obj.get("type") == "text-delta":
                                delta = obj.get("delta", "")
                                if delta:
                                    full.append(delta)
                                    yield f"data: {json.dumps({'d': delta})}\n\n"
                        except: pass
            if full:
                histories[key].append({"role": "assistant", "msg": "".join(full), "ts": datetime.now().isoformat()})
        except Exception as e:
            yield f"data: {json.dumps({'err': str(e)})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    return Response(stream_with_context(gen()), mimetype='text/event-stream')

@app.route('/')
def index():
    return render_template_string(HTML)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#0f0f1a" id="themeColor">
<title>Kalon AI</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
:root{--bg:#0f0f1a;--card:#1a1a2e;--input:#252540;--text:#fff;--text2:#9ca3af;--border:#2a2a45;--pri:#8b5cf6;--pri2:#a855f7;--green:#10b981;--red:#ef4444;--safe:env(safe-area-inset-bottom,0)}
[data-theme=light]{--bg:#f3f4f6;--card:#fff;--input:#e5e7eb;--text:#111827;--text2:#6b7280;--border:#d1d5db}
html,body{height:100%;overflow:hidden}
body{font-family:'Inter',-apple-system,system-ui,sans-serif;background:var(--bg);color:var(--text);font-size:14px;transition:background .3s,color .3s}
.app{display:flex;height:100%;height:100dvh}

/* Sidebar */
.sb{position:fixed;left:0;top:0;width:85%;max-width:300px;height:100%;background:var(--card);z-index:100;transform:translateX(-100%);transition:transform .3s cubic-bezier(.4,0,.2,1);display:flex;flex-direction:column;border-right:1px solid var(--border)}
.sb.open{transform:translateX(0)}
.sb-h{padding:16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px}
.sb-logo{width:36px;height:36px;background:linear-gradient(135deg,var(--pri),var(--pri2));border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px}
.sb-title{font-size:18px;font-weight:700;background:linear-gradient(135deg,var(--pri),var(--pri2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sb-chars{flex:1;overflow-y:auto;padding:12px;-webkit-overflow-scrolling:touch}
.sb-label{font-size:10px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px}
.char{padding:12px;background:var(--input);border:1px solid var(--border);border-radius:12px;margin-bottom:8px;cursor:pointer;transition:all .2s}
.char:active{transform:scale(.98)}
.char.active{border-color:var(--pri);background:rgba(139,92,246,.12)}
.char-name{font-size:13px;font-weight:600;margin-bottom:2px}
.char-desc{font-size:11px;color:var(--text2)}
.sb-footer{padding:12px;border-top:1px solid var(--border)}
.theme-toggle{width:100%;padding:10px;background:var(--input);border:1px solid var(--border);border-radius:10px;color:var(--text);font-size:12px;display:flex;align-items:center;justify-content:center;gap:8px;cursor:pointer;transition:all .2s}
.theme-toggle:active{background:var(--border)}
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:99;opacity:0;visibility:hidden;transition:all .3s}
.overlay.show{opacity:1;visibility:visible}

/* Main */
.main{flex:1;display:flex;flex-direction:column;width:100%}

/* Offline bar */
.offline{display:none;padding:6px 12px;background:var(--red);color:#fff;font-size:11px;text-align:center;align-items:center;justify-content:center;gap:6px}
.offline.show{display:flex}

/* Header */
.hdr{padding:10px 12px;padding-top:max(10px,env(safe-area-inset-top));background:var(--card);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px}
.menu-btn{width:38px;height:38px;background:none;border:none;color:var(--text);font-size:18px;cursor:pointer;border-radius:10px;display:flex;align-items:center;justify-content:center}
.menu-btn:active{background:var(--input)}
.avatar{width:38px;height:38px;background:linear-gradient(135deg,var(--pri),var(--pri2));border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:600;color:#fff}
.hdr-info{flex:1;min-width:0}
.hdr-name{font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hdr-status{display:flex;align-items:center;gap:4px;font-size:10px;color:var(--text2)}
.status-dot{width:6px;height:6px;border-radius:50%;background:var(--green)}
.status-dot.off{background:var(--red)}
.signal{display:flex;align-items:flex-end;gap:1px;height:12px;margin-left:6px}
.signal span{width:3px;background:var(--green);border-radius:1px;transition:all .3s}
.signal span:nth-child(1){height:4px}
.signal span:nth-child(2){height:7px}
.signal span:nth-child(3){height:10px}
.signal span:nth-child(4){height:12px}
.signal.weak span:nth-child(3),.signal.weak span:nth-child(4){background:var(--border)}
.signal.bad span:nth-child(2),.signal.bad span:nth-child(3),.signal.bad span:nth-child(4){background:var(--border)}
.signal.none span{background:var(--border)}
.clear-btn{width:38px;height:38px;background:none;border:none;color:var(--text2);font-size:15px;cursor:pointer;border-radius:10px;display:flex;align-items:center;justify-content:center}
.clear-btn:active{background:var(--input);color:var(--text)}

/* Messages */
.msgs{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;-webkit-overflow-scrolling:touch}
.welcome{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:20px}
.welcome-icon{width:60px;height:60px;background:linear-gradient(135deg,var(--pri),var(--pri2));border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:26px;margin-bottom:14px;animation:float 3s ease-in-out infinite}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
.welcome h2{font-size:17px;margin-bottom:6px}
.welcome p{color:var(--text2);font-size:12px}

/* Date separator */
.date-sep{display:flex;align-items:center;gap:10px;margin:6px 0}
.date-sep::before,.date-sep::after{content:'';flex:1;height:1px;background:var(--border)}
.date-sep span{font-size:10px;color:var(--text2);font-weight:500}

/* Message */
.msg{display:flex;gap:8px;max-width:85%;animation:msgIn .25s ease-out}
@keyframes msgIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.msg.u{align-self:flex-end;flex-direction:row-reverse}
.msg-av{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:600;flex-shrink:0;color:#fff;background:linear-gradient(135deg,var(--pri),var(--pri2))}
.msg.u .msg-av{background:var(--input);border:1px solid var(--border);color:var(--text)}
.msg-body{max-width:100%}
.msg-bub{padding:10px 12px;border-radius:16px;font-size:13px;line-height:1.45;word-break:break-word;background:var(--card);border:1px solid var(--border);border-bottom-left-radius:4px}
.msg.u .msg-bub{background:linear-gradient(135deg,var(--pri),var(--pri2));border:none;border-bottom-right-radius:4px;border-bottom-left-radius:16px;color:#fff}
.msg-meta{display:flex;align-items:center;gap:4px;margin-top:3px;font-size:9px;color:var(--text2)}
.msg.u .msg-meta{justify-content:flex-end}
.msg-read{color:var(--text2)}
.msg-read.read{color:#3b82f6}

/* Input */
.inp-wrap{padding:10px 12px;padding-bottom:max(10px,var(--safe));background:var(--card);border-top:1px solid var(--border)}
.typing{display:none;align-items:center;gap:4px;padding:6px 0;color:var(--text2);font-size:10px}
.typing.show{display:flex}
.typing span:not(.typing-txt){width:5px;height:5px;background:var(--pri);border-radius:50%;animation:bounce 1.4s infinite}
.typing span:nth-child(2){animation-delay:.2s}
.typing span:nth-child(3){animation-delay:.4s}
@keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-4px)}}
.inp-form{display:flex;gap:8px;align-items:flex-end}
textarea{flex:1;padding:10px 14px;background:var(--input);border:2px solid var(--border);border-radius:20px;color:var(--text);font-size:14px;font-family:inherit;resize:none;max-height:100px;transition:border .2s;outline:none}
textarea:focus{border-color:var(--pri)}
textarea:disabled{opacity:.6}
textarea::placeholder{color:var(--text2)}
.send-btn{width:42px;height:42px;background:linear-gradient(135deg,var(--pri),var(--pri2));border:none;border-radius:50%;color:#fff;font-size:17px;cursor:pointer;flex-shrink:0;transition:transform .2s,opacity .2s;display:flex;align-items:center;justify-content:center}
.send-btn:active:not(:disabled){transform:scale(.92)}
.send-btn:disabled{opacity:.5}

/* Toast */
.toast{position:fixed;bottom:80px;left:50%;transform:translateX(-50%) translateY(20px);padding:10px 16px;background:var(--card);border:1px solid var(--border);border-radius:10px;font-size:12px;z-index:200;opacity:0;transition:all .3s;pointer-events:none}
.toast.show{transform:translateX(-50%) translateY(0);opacity:1}
</style>
</head>
<body>
<div class="app">
<aside class="sb" id="sb">
<div class="sb-h"><div class="sb-logo">🤖</div><span class="sb-title">Kalon AI</span></div>
<div class="sb-chars" id="chars"><div class="sb-label">Characters</div></div>
<div class="sb-footer"><button class="theme-toggle" id="themeBtn">🌙 Dark Mode</button></div>
</aside>
<div class="overlay" id="ov"></div>
<main class="main">
<div class="offline" id="offline">📡 No connection</div>
<header class="hdr">
<button class="menu-btn" id="menuBtn">☰</button>
<div class="avatar" id="av">?</div>
<div class="hdr-info">
<div class="hdr-name" id="hdrName">Select Character</div>
<div class="hdr-status"><span class="status-dot" id="statusDot"></span><span id="statusTxt">Online</span><div class="signal" id="signal"><span></span><span></span><span></span><span></span></div></div>
</div>
<button class="clear-btn" id="clearBtn">🗑️</button>
</header>
<div class="msgs" id="msgs"><div class="welcome"><div class="welcome-icon">💬</div><h2>Welcome to Kalon AI</h2><p>Tap menu to select a character</p></div></div>
<div class="inp-wrap">
<div class="typing" id="typing"><span></span><span></span><span></span><span class="typing-txt">typing...</span></div>
<form class="inp-form" id="form">
<textarea id="inp" placeholder="Type a message..." rows="1" disabled></textarea>
<button type="submit" class="send-btn" id="sendBtn" disabled>➤</button>
</form>
</div>
</main>
</div>
<div class="toast" id="toast"></div>

<script>
const $=id=>document.getElementById(id);
let ch=null,busy=false,online=navigator.onLine,lastDate='';
let did=localStorage.getItem('did')||Math.random().toString(36).slice(2);
localStorage.setItem('did',did);

// Theme
const theme=localStorage.getItem('theme')||'dark';
document.documentElement.setAttribute('data-theme',theme);
updateTheme();
function updateTheme(){
  const dark=document.documentElement.getAttribute('data-theme')!=='light';
  $('themeBtn').innerHTML=dark?'☀️ Light Mode':'🌙 Dark Mode';
  $('themeColor').content=dark?'#0f0f1a':'#f3f4f6';
}
$('themeBtn').onclick=()=>{
  const dark=document.documentElement.getAttribute('data-theme')!=='light';
  document.documentElement.setAttribute('data-theme',dark?'light':'dark');
  localStorage.setItem('theme',dark?'light':'dark');
  updateTheme();
};

// Online status
function updateOnline(){
  online=navigator.onLine;
  $('offline').classList.toggle('show',!online);
  $('statusDot').classList.toggle('off',!online);
  $('statusTxt').textContent=online?'Online':'Offline';
  updateSignal();
}
window.addEventListener('online',()=>{updateOnline();toast('Connected')});
window.addEventListener('offline',updateOnline);
updateOnline();

// Signal strength
function updateSignal(){
  const conn=navigator.connection||navigator.mozConnection||navigator.webkitConnection;
  const sig=$('signal');
  sig.className='signal';
  if(!online){sig.classList.add('none');return}
  if(conn){
    const type=conn.effectiveType;
    if(type==='4g')sig.className='signal';
    else if(type==='3g')sig.classList.add('weak');
    else sig.classList.add('bad');
  }
}
if(navigator.connection)navigator.connection.addEventListener('change',updateSignal);
setInterval(updateSignal,5000);

// Sidebar
$('menuBtn').onclick=()=>{$('sb').classList.add('open');$('ov').classList.add('show')};
$('ov').onclick=()=>{$('sb').classList.remove('open');$('ov').classList.remove('show')};

// Toast
function toast(msg){$('toast').textContent=msg;$('toast').classList.add('show');setTimeout(()=>$('toast').classList.remove('show'),2500)}

// Format
const fmtTime=ts=>new Date(ts).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
function fmtDate(ts){
  const d=new Date(ts),t=new Date(),y=new Date(t);y.setDate(y.getDate()-1);
  if(d.toDateString()===t.toDateString())return'Today';
  if(d.toDateString()===y.toDateString())return'Yesterday';
  return d.toLocaleDateString([],{weekday:'short',month:'short',day:'numeric'});
}
function esc(s){
  let h=s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  h=h.replace(/\\*([^*]+)\\*/g,'<span style="color:#a78bfa;font-style:italic;opacity:.85">*$1*</span>');
  return h.replace(/\\n/g,'<br>');
}

// Date separator
function addDateSep(ts){
  const ds=fmtDate(ts);
  if(ds!==lastDate){
    lastDate=ds;
    const sep=document.createElement('div');
    sep.className='date-sep';
    sep.innerHTML=`<span>${ds}</span>`;
    $('msgs').appendChild(sep);
  }
}

// Add message
function addMsg(role,txt,ts=null,anim=true,read=false){
  $('msgs').querySelector('.welcome')?.remove();
  const t=ts?fmtTime(ts):fmtTime(new Date().toISOString());
  const isU=role==='u';
  const av=isU?'👤':ch.name[0];
  const readIcon=isU?`<span class="msg-read ${read?'read':''}">✓✓</span>`:'';
  const div=document.createElement('div');
  div.className=`msg ${isU?'u':''}`;
  if(!anim)div.style.animation='none';
  div.innerHTML=`<div class="msg-av">${av}</div><div class="msg-body"><div class="msg-bub">${esc(txt)}</div><div class="msg-meta"><span>${t}</span>${readIcon}</div></div>`;
  $('msgs').appendChild(div);
  $('msgs').scrollTop=$('msgs').scrollHeight;
  return div;
}

// Load chars
let CHARS=[];
fetch('/api/chars').then(r=>r.json()).then(d=>{
  CHARS=d;
  d.forEach(c=>{
    const el=document.createElement('div');
    el.className='char';
    el.innerHTML=`<div class="char-name">${c.name}</div><div class="char-desc">${c.desc}</div>`;
    el.onclick=()=>selectChar(c);
    $('chars').appendChild(el);
  });
});

// Select char
async function selectChar(c){
  ch=c;
  document.querySelectorAll('.char').forEach((el,i)=>el.classList.toggle('active',CHARS[i].id===c.id));
  $('hdrName').textContent=c.name;
  $('av').textContent=c.name[0];
  $('inp').disabled=false;
  $('sendBtn').disabled=false;
  $('inp').placeholder=`Message ${c.name}...`;
  $('sb').classList.remove('open');
  $('ov').classList.remove('show');
  await loadHist();
}

// Load history
async function loadHist(){
  if(!ch)return;
  lastDate='';
  const r=await fetch(`/api/history/${did}/${ch.sid}`);
  const h=await r.json();
  $('msgs').innerHTML='';
  if(!h.length){
    $('msgs').innerHTML=`<div class="welcome"><div class="welcome-icon">👋</div><h2>Chat with ${ch.name}</h2><p>Say hi to start!</p></div>`;
    return;
  }
  h.forEach((m,i)=>{
    addDateSep(m.ts);
    addMsg(m.role==='user'?'u':'a',m.msg,m.ts,false,i<h.length-1||m.role==='assistant');
  });
}

// Send
async function send(){
  if(busy||!ch)return;
  const msg=$('inp').value.trim();
  if(!msg)return;
  $('inp').value='';
  $('inp').style.height='auto';
  busy=true;
  
  addDateSep(new Date().toISOString());
  const uMsg=addMsg('u',msg,null,true,false);
  $('typing').classList.add('show');
  $('msgs').scrollTop=$('msgs').scrollHeight;
  
  const aMsg=addMsg('a','');
  const bub=aMsg.querySelector('.msg-bub');
  let full='';
  
  try{
    const r=await fetch('/api/chat',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({msg,sid:ch.sid,name:ch.name,did})
    });
    const rd=r.body.getReader(),dc=new TextDecoder();
    while(true){
      const{done,value}=await rd.read();
      if(done)break;
      for(const l of dc.decode(value).split('\\n')){
        if(!l.startsWith('data:'))continue;
        try{
          const j=JSON.parse(l.slice(5));
          if(j.d){full+=j.d;bub.innerHTML=esc(full);$('msgs').scrollTop=$('msgs').scrollHeight}
        }catch{}
      }
    }
    if(full){
      uMsg.querySelector('.msg-read')?.classList.add('read');
    }else{
      bub.innerHTML='<span style="opacity:.5">No response</span>';
    }
  }catch(e){
    bub.innerHTML=`<span style="color:var(--red)">Error: ${e.message}</span>`;
  }
  busy=false;
  $('typing').classList.remove('show');
}

// Form
$('form').onsubmit=e=>{e.preventDefault();if(!busy)send()};
$('inp').oninput=function(){this.style.height='auto';this.style.height=Math.min(this.scrollHeight,100)+'px'};
$('inp').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();if(!busy)send()}};

// Clear
$('clearBtn').onclick=async()=>{
  if(!ch||!confirm(`Clear chat with ${ch.name}?`))return;
  await fetch(`/api/history/${did}/${ch.sid}`,{method:'DELETE'});
  await loadHist();
  toast('Chat cleared');
};
</script>
</body></html>'''
