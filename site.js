const D=document,$=s=>D.querySelector(s),LS="sd-prefs",SDC=window.SDC||{},DAY=window.SDDAY||"";
const ACC={blue:["#2a78d6","#5b9be8"],green:["#168a52","#3fbf80"],violet:["#6b4fd8","#9a85f0"],orange:["#d9701a","#f09a4a"]};
let P={theme:"auto",accent:"blue",dense:false};try{P={...P,...JSON.parse(localStorage.getItem(LS)||"{}")}}catch(e){}
const isDark=()=>P.theme=="dark"||(P.theme=="auto"&&matchMedia("(prefers-color-scheme:dark)").matches);
const E=t=>String(t??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const SD=window.SD=Object.assign(window.SD||{cbs:[]},{enabled:!!SDC.apiKey,user:null,known:false,onUser(cb){this.cbs.push(cb);if(this.known)cb(this.user)},save:async()=>{},load:async()=>null});
const toast=t=>{const e=D.createElement("div");e.className="tst";e.textContent=t;D.body.appendChild(e);setTimeout(()=>e.remove(),2600)};SD.toast=toast;
let pushPrefs=()=>{};
function apply(){const h=D.documentElement;h.dataset.theme=P.theme;h.dataset.dense=P.dense?1:0;h.style.setProperty("--s",ACC[P.accent][isDark()?1:0]);paintIcon()}
function setP(k,v){P[k]=v;try{localStorage.setItem(LS,JSON.stringify(P))}catch(e){}apply();pushPrefs()}
const nav=$("nav"),acct=D.createElement("div");acct.id="acct";nav&&nav.appendChild(acct);
acct.innerHTML='<button class="ib" id="thb" title="Toggle dark mode (d)"></button><span id="ab"></span><div class="pm" id="pm" hidden></div>';
const paintIcon=()=>{const b=$("#thb");if(b)b.textContent=isDark()?"☀️":"🌙"};
$("#thb").onclick=()=>setP("theme",isDark()?"light":"dark");
matchMedia("(prefers-color-scheme:dark)").addEventListener?.("change",apply);
const ini=u=>(u.displayName||u.email||"?").trim()[0].toUpperCase(),av=u=>u.photoURL?`<img src="${E(u.photoURL)}" alt="" referrerpolicy="no-referrer">`:E(ini(u));
function paint(){const u=SD.user,ab=$("#ab"),pm=$("#pm");pm.hidden=true;
if(!SD.enabled){ab.innerHTML='<button class="av" id="avb" title="Menu">☰</button>'}
else if(!u)ab.innerHTML='<button class="sib" id="sib">Sign in</button>';
else ab.innerHTML=`<button class="av" id="avb" title="${E(u.email)}">${av(u)}</button>`;
pm.innerHTML=(u?`<div class="who"><b>${E(u.displayName||"Signed in")}</b><span>${E(u.email)}</span></div><button class="mi" data-a="profile">👤 Profile</button>`:`<div class="who"><b>Welcome</b><span>${SD.enabled?"Sign in to save your journal across devices.":"Account sign-in is not switched on."}</span></div>${SD.enabled?'<button class="mi" data-a="in">🔑 Sign in with Google</button>':""}`)
+'<button class="mi" data-a="set">⚙️ Settings</button><button class="mi" data-a="keys">⌨️ Keyboard shortcuts <kbd>?</kbd></button><button class="mi" data-a="about">ℹ️ About &amp; disclaimer</button>'+(u?'<button class="mi" data-a="out">↪️ Sign out</button>':"");
const s=$("#sib");if(s)s.onclick=signIn;const a=$("#avb");if(a)a.onclick=e=>{e.stopPropagation();pm.hidden=!pm.hidden}}
D.addEventListener("click",e=>{const pm=$("#pm");if(!pm)return;const m=e.target.closest(".mi");if(m){pm.hidden=true;act(m.dataset.a)}else if(!pm.contains(e.target))pm.hidden=true});
let signIn=()=>toast("Sign-in is not switched on yet"),signOutF=()=>{},delData=async()=>{};
function modal(h){let o=$("#ov");if(!o){o=D.createElement("div");o.id="ov";o.className="ov";o.onclick=e=>{if(e.target==o||e.target.dataset.x!=null)o.hidden=true};D.body.appendChild(o)}o.innerHTML=`<div class="md">${h}</div>`;o.hidden=false;return o}
const seg=(k,opts)=>`<div class="seg" data-k="${k}">${opts.map(([v,t])=>`<button data-v="${v}" class="${P[k]==v?"on":""}">${t}</button>`).join("")}</div>`;
function act(a){if(a=="in")signIn();else if(a=="out")signOutF();else if(a=="set")settings();else if(a=="keys")keys();else if(a=="about")about();else if(a=="profile")profile()}
function settings(){const o=modal(`<h3>Settings <button data-x>✕</button></h3>
<div class="row"><div><b>Theme</b><small>Auto follows your device</small></div>${seg("theme",[["auto","Auto"],["light","Light"],["dark","Dark"]])}</div>
<div class="row"><div><b>Accent colour</b></div><div class="dots">${Object.keys(ACC).map(k=>`<button data-c="${k}" class="${P.accent==k?"on":""}" style="background:${ACC[k][0]}" title="${k}"></button>`).join("")}</div></div>
<div class="row"><div><b>Compact tables</b><small>Tighter rows to fit more on screen</small></div><button class="sw ${P.dense?"on":""}" data-d></button></div>
<div class="row"><div><b>Your data</b><small>Download your journal as a backup file</small></div><button class="btn2" data-e>Export</button></div>
<div class="row"><div><b>Preferences</b><small>${SD.user?"Saved to your account and follow you across devices":"Saved in this browser. Sign in to carry them across devices"}</small></div></div>`);
o.querySelectorAll(".seg button").forEach(b=>b.onclick=()=>{setP("theme",b.dataset.v);settings()});
o.querySelectorAll(".dots button").forEach(b=>b.onclick=()=>{setP("accent",b.dataset.c);settings()});
o.querySelector("[data-d]").onclick=()=>{setP("dense",!P.dense);settings()};
o.querySelector("[data-e]").onclick=()=>{const j=localStorage.getItem("nse-journal-v1")||'{"trades":[]}',a=D.createElement("a");a.href=URL.createObjectURL(new Blob([j],{type:"application/json"}));a.download="swingdesk-journal.json";a.click();toast("Journal exported")}}
function profile(){const u=SD.user;if(!u)return;let n=0;try{n=(JSON.parse(localStorage.getItem("nse-journal-v1")||"{}").trades||[]).length}catch(e){}
const o=modal(`<h3>Profile <button data-x>✕</button></h3><div class="pf"><div class="av">${av(u)}</div><div><b style="font-size:17px">${E(u.displayName||"Trader")}</b><br><span style="color:var(--ink2);font-size:13px">${E(u.email)}</span></div></div>
<div class="row"><b>Member since</b><span>${E((u.metadata.creationTime||"").slice(5,16))}</span></div><div class="row"><b>Last sign-in</b><span>${E((u.metadata.lastSignInTime||"").slice(5,22))}</span></div>
<div class="row"><b>Trades in journal</b><span>${n}</span></div>
<div class="row"><div><b>Delete cloud data</b><small>Removes your saved journal and preferences from your account. This browser's copy stays.</small></div><button class="btn2 dng" data-del>Delete</button></div>
<div class="row"><b></b><button class="btn2" data-so>Sign out</button></div>`);
o.querySelector("[data-so]").onclick=()=>{o.hidden=true;signOutF()};
o.querySelector("[data-del]").onclick=async()=>{if(confirm("Delete your cloud journal and preferences? This cannot be undone.")){await delData();o.hidden=true}}}
function keys(){modal(`<h3>Keyboard shortcuts <button data-x>✕</button></h3>${[["g r","Regime"],["g s","Sectors"],["g u","Setups"],["g f","Fundamentals"],["g j","Journal"],["d","Toggle dark mode"],["/","Focus the search box"],["?","This list"]].map(([k,t])=>`<div class="row"><span>${t}</span><span>${k.split(" ").map(x=>`<kbd>${x}</kbd>`).join(" ")}</span></div>`).join("")}`)}
function about(){modal(`<h3>About SwingDesk <button data-x>✕</button></h3><p style="margin:0 0 10px">A daily NSE swing-trading desk: market regime, sector strength, setups, fundamentals and a trade journal. Data refreshes on weekdays after the close${DAY?` (latest close: ${E(DAY)})`:""}.</p><p style="margin:0;color:var(--ink2);font-size:13.5px">For education and personal research only. Nothing here is investment advice. Prices come from public sources and may be delayed or wrong. Check before you trade.</p>`)}
let gp=0;D.addEventListener("keydown",e=>{if(e.metaKey||e.ctrlKey||e.altKey||/INPUT|TEXTAREA|SELECT/.test(e.target.tagName))return;
if(e.key=="Escape"){const o=$("#ov");if(o)o.hidden=true;$("#pm").hidden=true;return}
if(e.key=="?"){keys();return}if(e.key=="d"){setP("theme",isDark()?"light":"dark");return}
if(e.key=="/"){const q=$("#q")||$("input[type=search]");if(q){e.preventDefault();q.focus()}return}
if(gp&&Date.now()-gp<1200){const m={r:"index",s:"sectors",u:"setups",f:"fundamentals",j:"journal"}[e.key];gp=0;if(m)location.href=m+".html";return}
if(e.key=="g")gp=Date.now()});
const ft=D.createElement("footer");ft.className="ft";ft.innerHTML=`<span>SwingDesk &middot; NSE swing desk${DAY?" &middot; close of "+E(DAY):""}</span><span><a id="fa">About</a> &middot; <a id="fk">Shortcuts</a> &middot; Not investment advice</span>`;D.querySelector("main")?.appendChild(ft);$("#fa").onclick=about;$("#fk").onclick=keys;
apply();paint();
if(SD.enabled){try{const b="https://www.gstatic.com/firebasejs/10.12.2/",[{initializeApp},{getAuth,GoogleAuthProvider,signInWithPopup,onAuthStateChanged,signOut},{getFirestore,doc,getDoc,setDoc,deleteDoc,onSnapshot}]=await Promise.all([import(b+"firebase-app.js"),import(b+"firebase-auth.js"),import(b+"firebase-firestore.js")]);
const app=initializeApp(SDC),au=getAuth(app),db=getFirestore(app);let ref=null,pt=null,unsub=null,wcb=null;const sub=()=>{unsub&&unsub();unsub=null;if(ref&&wcb)unsub=onSnapshot(ref,x=>wcb(x.exists()?x.data():null,x.metadata.hasPendingWrites),e=>wcb(undefined,false,e))};SD.watch=cb=>{wcb=cb;sub()};
signIn=()=>signInWithPopup(au,new GoogleAuthProvider()).catch(e=>{if(e.code!="auth/popup-closed-by-user"&&e.code!="auth/cancelled-popup-request")toast("Sign-in failed: "+e.code)});
signOutF=()=>signOut(au).then(()=>toast("Signed out"));
SD.signIn=signIn;SD.save=f=>ref?setDoc(ref,f,{merge:true}):Promise.resolve();SD.load=async()=>{if(!ref)return null;const s=await getDoc(ref);return s.exists()?s.data():null};
delData=async()=>{try{await deleteDoc(ref);toast("Cloud data deleted")}catch(e){toast("Could not delete: "+e.code)}};
pushPrefs=()=>{if(!ref)return;clearTimeout(pt);pt=setTimeout(()=>setDoc(ref,{p:JSON.stringify(P)},{merge:true}).catch(()=>{}),600)};
onAuthStateChanged(au,async u=>{SD.user=u;ref=u?doc(db,"users",u.uid):null;paint();sub();
if(u){try{const d=await SD.load();if(d&&d.p){P={...P,...JSON.parse(d.p)};try{localStorage.setItem(LS,JSON.stringify(P))}catch(e){}apply()}else pushPrefs()}catch(e){}}
SD.known=true;SD.cbs.forEach(cb=>cb(u))})}catch(e){SD.enabled=false;paint();SD.known=true;SD.cbs.forEach(cb=>cb(null))}}
else{SD.known=true;SD.cbs.forEach(cb=>cb(null))}
