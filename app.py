"""
Kalon AI Chat - Render.com Deploy
"""
import os, json, httpx, random, string, time
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, Response, stream_with_context

app = Flask(__name__)

# Credentials
CLERK_SESSION = os.environ.get("CLERK_SESSION", "sess_37aDGAhkwiEnEyRIHNqYeLVMdJM")
CLERK_TOKEN = os.environ.get("CLERK_TOKEN", "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImNsaWVudF8zN2FEMmwyY0RxN3JucmtaTEFZMkMyczNPZWQiLCJyb3RhdGluZ190b2tlbiI6ImpzYmdwbGc4ZGJkMnRheDRoYjN5cnp3czhsdDIwZXVrMmowOG1wczgifQ.e3eh4OOpU1mnkpGKDs8dtP7Bv5FnV0HNTZt3pMJ1JscNetl9zAcr111upFyyhUlO0N3j6l39ez_X8KYbmTQxuVz7u4wXzEYk0Rm8yokmrWv2Wb8Ut-PvCt67sVK0QqUsuBigwK5sn44mtpyqbRPIpGYSKLZkD0C3uFU7RXqNy0oTangRW-O4JRjxEmAlfxEn2DIz0E7zBn_AkM_4Ucp724l4M7VSdQok9vZVK1WHcB-awe8Jg4R651fjjlkTBxwfMbbB7BHMyi5Nqj6d7sifUGZ3-HurUfk4dV9FVN5t8PJprEN-yEv-jBUAagvKccsZUU6dYMkNfdzyHHCxkBM2tw")

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
            r = c.post(
                f"https://clerk.kalon.ai/v1/client/sessions/{CLERK_SESSION}/tokens",
                params={"__clerk_api_version": "2025-11-10"},
                data={"organization_id": ""},
                headers={"Origin": "https://www.kalon.ai", "Cookie": f"__client={CLERK_TOKEN}"}
            )
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
            "sessionId": sid,
            "character": {"name": name},
            "conversationStyle": "immersive",
            "memory": "",
            "hornyLevel": "medium",
            "responseLength": "balanced",
            "model": "xai/grok-4-fast-non-reasoning"
        }
        
        full = []
        try:
            with httpx.Client(timeout=httpx.Timeout(60, read=300), http2=True) as c:
                with c.stream("POST", "https://www.kalon.ai/api/chat", json=payload, headers={
                    "Authorization": f"Bearer {token}",
                    "Origin": "https://www.kalon.ai",
                    "Accept": "text/event-stream",
                    "Content-Type": "application/json"
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


HTML = '''<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<meta name="theme-color" content="#0f0f1a">
<title>Kalon AI</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
:root{--bg:#0f0f1a;--card:#1a1a2e;--input:#252540;--text:#fff;--text2:#9ca3af;--border:#2a2a45;--pri:#8b5cf6}
body{font-family:system-ui,sans-serif;background:var(--bg);color:var(--text);height:100vh;height:100dvh;display:flex;flex-direction:column;font-size:14px}
.hdr{padding:10px 12px;background:var(--card);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px}
.menu{width:36px;height:36px;background:none;border:none;color:var(--text);font-size:20px;cursor:pointer}
.av{width:36px;height:36px;background:linear-gradient(135deg,#8b5cf6,#a855f7);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:600}
.info{flex:1}.info h2{font-size:14px}.info p{font-size:10px;color:var(--text2)}
.sb{position:fixed;left:0;top:0;width:80%;max-width:280px;height:100%;background:var(--card);z-index:100;transform:translateX(-100%);transition:transform .3s;display:flex;flex-direction:column}
.sb.open{transform:translateX(0)}
.ov{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:99;opacity:0;visibility:hidden;transition:all .3s}
.ov.show{opacity:1;visibility:visible}
.sb-h{padding:16px;border-bottom:1px solid var(--border);font-size:18px;font-weight:700;background:linear-gradient(135deg,#8b5cf6,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.chars{flex:1;overflow-y:auto;padding:12px}
.char{padding:12px;background:var(--input);border:1px solid var(--border);border-radius:12px;margin-bottom:10px;cursor:pointer}
.char.active{border-color:var(--pri);background:rgba(139,92,246,.15)}
.char h3{font-size:13px}.char p{font-size:11px;color:var(--text2)}
.msgs{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px}
.msg{display:flex;gap:8px;max-width:85%;animation:fadeIn .25s}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1}}
.msg.u{align-self:flex-end;flex-direction:row-reverse}
.msg-av{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;background:linear-gradient(135deg,#8b5cf6,#a855f7)}
.msg.u .msg-av{background:var(--input);border:1px solid var(--border)}
.bub{padding:10px 12px;border-radius:16px;font-size:13px;line-height:1.4;background:var(--card);border:1px solid var(--border)}
.msg.u .bub{background:linear-gradient(135deg,#8b5cf6,#a855f7);border:none}
.inp-area{padding:10px 12px 14px;background:var(--card);border-top:1px solid var(--border)}
.typing{display:none;padding:5px 0;color:var(--text2);font-size:10px}
.typing.show{display:block}
.form{display:flex;gap:8px}
input{flex:1;padding:10px 14px;background:var(--input);border:2px solid var(--border);border-radius:20px;color:var(--text);font-size:14px;outline:none}
input:focus{border-color:var(--pri)}
.send{width:40px;height:40px;background:linear-gradient(135deg,#8b5cf6,#a855f7);border:none;border-radius:50%;color:#fff;font-size:16px;cursor:pointer}
.send:disabled{opacity:.5}
.welcome{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:20px}
.welcome h2{font-size:18px;margin-bottom:8px}
.welcome p{color:var(--text2);font-size:13px}
</style>
</head>
<body>
<div class="sb" id="sb"><div class="sb-h">🤖 Kalon AI</div><div class="chars" id="chars"></div></div>
<div class="ov" id="ov"></div>
<div class="hdr"><button class="menu" id="menuBtn">☰</button><div class="av" id="av">?</div><div class="info"><h2 id="name">Select Character</h2><p>● Online</p></div></div>
<div class="msgs" id="msgs"><div class="welcome"><h2>👋 Welcome!</h2><p>Tap menu to select a character</p></div></div>
<div class="inp-area"><div class="typing" id="typing">Typing...</div><form class="form" id="form"><input id="inp" placeholder="Message..." disabled><button class="send" id="btn" disabled>➤</button></form></div>
<script>
let ch=null,busy=0,did=localStorage.getItem('did')||Math.random().toString(36).slice(2);
localStorage.setItem('did',did);
const $=i=>document.getElementById(i);

$('menuBtn').onclick=()=>{$('sb').classList.add('open');$('ov').classList.add('show')};
$('ov').onclick=()=>{$('sb').classList.remove('open');$('ov').classList.remove('show')};

function esc(s){return s.replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\*([^*]+)\\*/g,'<i style="color:#a78bfa">*$1*</i>').replace(/\\n/g,'<br>')}

function addMsg(r,txt,anim=true){
  $('msgs').querySelector('.welcome')?.remove();
  let d=document.createElement('div');
  d.className='msg '+(r=='u'?'u':'');
  if(!anim)d.style.animation='none';
  d.innerHTML=`<div class="msg-av">${r=='u'?'👤':ch.name[0]}</div><div class="bub">${esc(txt)}</div>`;
  $('msgs').appendChild(d);
  $('msgs').scrollTop=$('msgs').scrollHeight;
  return d;
}

async function loadHist(){
  if(!ch)return;
  let r=await fetch(`/api/history/${did}/${ch.sid}`);
  let h=await r.json();
  $('msgs').innerHTML=h.length?'':'<div class="welcome"><h2>Chat with '+ch.name+'</h2><p>Say hi!</p></div>';
  h.forEach(m=>addMsg(m.role=='user'?'u':'a',m.msg,false));
}

function selectChar(c){
  ch=c;
  document.querySelectorAll('.char').forEach((el,i)=>el.classList.toggle('active',i==CHARS.indexOf(c)));
  $('name').textContent=c.name;
  $('av').textContent=c.name[0];
  $('inp').disabled=0;$('btn').disabled=0;
  $('sb').classList.remove('open');$('ov').classList.remove('show');
  loadHist();
}

let CHARS=[];
fetch('/api/chars').then(r=>r.json()).then(d=>{
  CHARS=d;
  d.forEach(c=>{
    let el=document.createElement('div');
    el.className='char';
    el.innerHTML=`<h3>${c.name}</h3><p>${c.desc}</p>`;
    el.onclick=()=>selectChar(c);
    $('chars').appendChild(el);
  });
});

async function send(){
  if(busy||!ch)return;
  let msg=$('inp').value.trim();
  if(!msg)return;
  $('inp').value='';busy=1;
  addMsg('u',msg);
  $('typing').classList.add('show');
  let a=addMsg('a',''),bub=a.querySelector('.bub'),full='';
  
  try{
    let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({msg,sid:ch.sid,name:ch.name,did})});
    let rd=r.body.getReader(),dc=new TextDecoder();
    while(1){
      let{done,value}=await rd.read();
      if(done)break;
      for(let l of dc.decode(value).split('\\n')){
        if(!l.startsWith('data:'))continue;
        try{let j=JSON.parse(l.slice(5));if(j.d){full+=j.d;bub.innerHTML=esc(full)}}catch{}
      }
      $('msgs').scrollTop=$('msgs').scrollHeight;
    }
  }catch(e){bub.innerHTML='Error'}
  busy=0;$('typing').classList.remove('show');
}

$('form').onsubmit=e=>{e.preventDefault();send()};
$('inp').onkeydown=e=>{if(e.key=='Enter'&&!e.shiftKey){e.preventDefault();send()}};
</script>
</body></html>'''

@app.route('/')
def index():
    return render_template_string(HTML)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
