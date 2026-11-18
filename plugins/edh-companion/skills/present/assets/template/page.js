"use strict";
const $=(s,r=document)=>r.querySelector(s), el=(t,a={},...k)=>{const e=document.createElement(t);for(const[n,v]of Object.entries(a)){if(n==="class")e.className=v;else if(n==="style")e.style.cssText=v;else if(n.startsWith("on"))e.addEventListener(n.slice(2),v);else if(n.startsWith("aria-")&&typeof v==="boolean")e.setAttribute(n,String(v));else if(v!==false&&v!=null)e.setAttribute(n,v===true?"":v)}for(const c of k.flat()){if(c==null||c===false)continue;e.append(c.nodeType?c:document.createTextNode(c))}return e};
const store={get(k,d){try{const v=localStorage.getItem("mtgp:"+k);return v==null?d:JSON.parse(v)}catch(e){return d}},set(k,v){try{localStorage.setItem("mtgp:"+k,JSON.stringify(v))}catch(e){}}};
const money=v=>v==null?"—":"$"+(v<10?v.toFixed(2):v<1000?v.toFixed(0):Math.round(v).toLocaleString());
const cssv=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const cap=s=>s?s[0].toUpperCase()+s.slice(1):s;
const plural=(n,one,many)=>`${n} ${n===1?one:(many||one+"s")}`;
const slugify=s=>String(s||"").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"")||"x";
const reducedMotion=()=>matchMedia("(prefers-reduced-motion:reduce)").matches;
let D, ATL, charts=[], SHOW={}, IMG="atlas", MODE="showcase", IN_DECK=false;
const CHART_URL="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js";
const loadScript=src=>new Promise((ok,no)=>{const s=document.createElement("script");s.src=src;s.onload=ok;s.onerror=no;document.head.append(s)});

/* ---------- images from atlas ---------- */
function artStyle(key){if(IMG==="cdn"){const u=(D.image_urls||{})[key];return u?`background-image:url("${u}");background-size:cover;background-position:center`:""}
 const a=ATL&&ATL.cards[key];if(!a)return "";const[i,x,y]=a,[w,h]=ATL.cell,c=ATL.cols,r=ATL.rows;
 return `background-image:url(${ATL.base}${ATL.atlases[i]});background-size:${c*100}% ${r*100}%;background-position:${c>1?x/w/(c-1)*100:0}% ${r>1?y/h/(r-1)*100:0}%`}
// a card image; a missing image shows the card name on the placeholder instead of a blank box
function art(key,alt,name){if(IMG==="none")return null;const s=artStyle(key);return el("div",{class:"art",role:alt?"img":null,"aria-label":alt||null,style:s},s?null:el("span",{class:"artname","aria-hidden":"true"},name||alt||""))}

/* ---------- human labels (never raw enums) ---------- */
const ST_TXT={pass:"Pass",warning:"Warning",fail:"Fail",unverified:"Unverified",info:"Note"};
const ICON={pass:"✓",warning:"!",fail:"✕",unverified:"?",info:"i"};
const STATE_TXT={pass:"Pass",pass_with_warnings:"Pass with warnings",fail:"Fail",incomplete:"Incomplete","not audited":"Not audited","audit out of date":"Audit out of date"};
const STATE_ST={pass:"pass",pass_with_warnings:"warning",fail:"fail",incomplete:"unverified","not audited":"unverified","audit out of date":"warning"};
const KIND_TXT={deterministic:"Script check",sourced:"Checked against a source",judgment:"Auditor's judgment"};
const CONF_TXT={high:"High confidence",medium:"Medium confidence",low:"Low confidence"};
function statusIcon(st){return el("span",{class:"ic st-"+st,"aria-hidden":"true"},ICON[st]||"?")}
function statusTag(st,label){st=ST_TXT[st]?st:"unverified";return el("span",{class:"tag st-"+st},statusIcon(st),label||ST_TXT[st])}
function stateTag(state){return statusTag(STATE_ST[state]||"unverified",STATE_TXT[state]||cap(String(state||"Not audited")))}

/* ---------- theme pills: only exceptions and off-theme cards are marked ---------- */
const THEME_PAL=["#2a6fc9","#1f8f63","#c4532a","#5b49d0","#b8467a","#8a5f08"];  // used when a theme label has no color
function themeColor(label){const t=D.theme;if(!t)return"var(--muted)";const i=t.labels.findIndex(l=>l.label===label);return i<0?"var(--gold)":t.labels[i].color||THEME_PAL[i%THEME_PAL.length]}
const isDefaultTheme=l=>/^on[ -]?theme$/i.test(String(l||""));
function pill(label){if(!D.theme||!label)return null;return el("span",{class:"pill",style:`--c:${themeColor(label)}`},el("i"),label==="off-theme"?"Off-theme":label)}

/* ---------- tabs and routing ---------- */
function tabsList(){const t=[];
 if(D.groups.length)t.push({id:"decks",view:"decks",title:"Decks",render:renderDecks});
 D.research.forEach(r=>t.push({id:r.id,view:"research",title:r.title,render:h=>renderResearch(r,h)}));
 if(!IN_DECK)D.research_tab.filter(x=>!D.research.some(r=>(r.project||null)===(x.project||null))).forEach(x=>t.push({id:x.id,view:"research",title:x.title,render:h=>renderResearch({...x,commanders:[]},h)}));
 D.rankings.forEach(r=>t.push({id:"rank-"+r.id,view:"rankings",title:r.title,render:h=>renderRanking(r,h)}));
 if(SHOW.sources&&!IN_DECK)t.push({id:"sources",view:"sources",title:"Sources & accuracy",render:renderSources});return t}
// One page with at most four views (decks, research, rankings, sources); pages inside a view switch in place
const VIEW_TITLE={decks:"Decks",research:"Research",rankings:"Rankings",sources:"Sources & accuracy"};
// short labels for sibling pages: drop the words every title starts with ("... inclusion, Bracket 2" -> "Bracket 2")
function shortLabels(ts){if(ts.length<2)return ts;const w=ts.map(t=>String(t).split(" "));let n=0;while(w.every(x=>x.length>n+1&&x[n]===w[0][n]))n++;
 return w.map(x=>x.slice(n).join(" ").replace(/^[,:·-]\s*/,"")).map(x=>x.charAt(0).toUpperCase()+x.slice(1))}
function subSwitch(sibs,tab){const lb=shortLabels(sibs.map(x=>x.title));
 return el("div",{class:"panel subswitch"},el("div",{class:"seg",role:"group","aria-label":VIEW_TITLE[tab.view]},...sibs.map((x,i)=>el("button",{type:"button",class:"btn","aria-pressed":x===tab,onclick:()=>go(x.id)},el("b",{},lb[i])))))}
let TABS=[],secObs=null;
function go(id,push=true){hideTip();hidePop();
 if(/^build=/.test(id||"")){store.set("build",decodeURIComponent(id.slice(6)));id="decks"}  // #build=<commander>/<build> opens that build
 const tab=TABS.find(t=>t.id===id)||TABS.find(t=>t.id===anchorTab(id))||TABS[0];
 document.querySelectorAll("#tabs button").forEach(b=>b.dataset.view===tab.view?b.setAttribute("aria-current","page"):b.removeAttribute("aria-current"));
 charts.forEach(c=>c.destroy());charts=[];if(secObs){secObs.disconnect();secObs=null}
 document.body.classList.remove("herotitle","has-secnav");placeTheme(null);
 const m=$("#main");m.replaceChildren();applyLook(D.look);
 const sibs=TABS.filter(t=>t.view===tab.view);if(sibs.length>1)m.append(subSwitch(sibs,tab));
 tab.render(m);store.set("tab",tab.id);store.set("view:"+tab.view,tab.id);
 const t=id&&id!==tab.id?document.getElementById(id):null;
 if(push)history.replaceState(null,"","#"+(t?id:tab.view==="decks"&&CUR.key?"build="+encodeURIComponent(CUR.key):tab.id));
 if(t)requestAnimationFrame(()=>jumpTo(t))}
function jumpTo(t){document.querySelectorAll(".src.hl").forEach(x=>x.classList.remove("hl"));openTo(t);t.scrollIntoView();if(t.tabIndex===-1)t.focus({preventScroll:true});if(t.classList.contains("src"))t.classList.add("hl")}
function buildTabs(){TABS=tabsList();const views=[...new Set(TABS.map(t=>t.view))];
 const open=v=>{const last=store.get("view:"+v,"");go(TABS.some(t=>t.id===last&&t.view===v)?last:TABS.find(t=>t.view===v).id);scrollTo(0,0)};
 $("#tabs").replaceChildren(...views.map(v=>el("li",{},el("button",{type:"button","data-view":v,onclick:()=>open(v)},VIEW_TITLE[v]))));
 $("#tabsNav").hidden=views.length<2}
// the theme button sits in the sticky section nav when there is one, else in the masthead
function placeTheme(host){const b=$("#themeBtn");if(b)(host||$("#mast")).append(b)}

/* ---------- report look: palette roles per commander (or a saved theme), neutral where several commanders show ---------- */
const ROLES=["bg","surface","surface2","border","text","muted","accent","accent2","on_accent","focus","art_wash","gold","hero_muted"];
function applyLook(L){L=L||D.look;const r=document.documentElement.style,P=(L||{}).palette;
 for(const m of["l","d"])ROLES.forEach(k=>{r.removeProperty(`--${m}-${k}`);if(P&&P[m]&&P[m][k])r.setProperty(`--${m}-${k}`,P[m][k])});
 document.body.dataset.look=(L&&L.style)||"";document.body.dataset.lookSource=(P&&P.source)||""}
/* ---------- legality status: upcoming (with release date), banned, not legal ---------- */
const ST_LABEL={upcoming:"Upcoming",banned:"Banned",not_legal:"Not legal"};
function statusPill(c){if(!c||!ST_LABEL[c.status])return null;return el("span",{class:"pill lp-"+c.status},ST_LABEL[c.status]+(c.status==="upcoming"&&c.releases?", releases "+c.releases:""))}
function roleText(c){const e=Object.entries(c.roles||{});return e.length?e.map(([r,why])=>`${r} (${why.join(", ")})`).join("; "):"no role rule matched"}
function evidenceLinks(ev){return ev&&ev.length?el("p",{class:"note"},"Evidence: ",...ev.flatMap((x,i)=>[i?", ":"",ext(x.url,`${x.title} (opens in a new tab)`,"",x.title)])):null}

/* ---------- card types: one mapping for groups, filters and the type chart ---------- */
const TYPE_ORDER=["Creature","Planeswalker","Battle","Artifact","Enchantment","Instant","Sorcery","Land"];  // display order: lands last
const GROUP_ORDER=["Commander",...TYPE_ORDER,"Other"];
const TYPE_PL={Commander:"commander",Creature:"creatures",Planeswalker:"planeswalkers",Battle:"battles",Artifact:"artifacts",Enchantment:"enchantments",Instant:"instants",Sorcery:"sorceries",Land:"lands",Other:"other cards"};
const TYPE_COLOR={Commander:"var(--text)",Creature:"var(--s1)",Planeswalker:"var(--s2)",Battle:"var(--s3)",Artifact:"var(--s4)",Enchantment:"var(--s5)",Instant:"var(--s6)",Sorcery:"var(--s7)",Land:"var(--s8)",Other:"var(--unv)"};
function typeInfo(c){const types=(c.types||[]).filter(t=>TYPE_ORDER.includes(t));return{group:TYPE_ORDER.includes(c.type_group)?c.type_group:"Other",types:types.length?types:["Other"],mdfc:!!c.mdfc_land}}
const mainType=c=>typeInfo(c).group;
const displayGroup=c=>c.commander?"Commander":mainType(c);
// "36 lands + 2 MDFC": spell//land cards are grouped by their front face and counted separately
function landLabel(cards){const n=cards.filter(c=>!c.commander&&mainType(c)==="Land").reduce((a,c)=>a+c.qty,0),m=cards.filter(c=>typeInfo(c).mdfc&&mainType(c)!=="Land").reduce((a,c)=>a+c.qty,0);
 return {n,m,text:plural(n,"land")+(m?` + ${m} MDFC`:"")}}
/* ---------- charts (Chart.js): each with a title, a one-line takeaway and a data table ---------- */
function baseOpts(extra={}){const tx=cssv("--muted"),gr=cssv("--border");return Object.assign({responsive:true,maintainAspectRatio:false,animation:MODE==="showcase"&&!reducedMotion()?{duration:400}:false,
 plugins:{legend:{labels:{color:tx,boxWidth:10,font:{size:12}}},tooltip:{intersect:false,mode:"index"}},
 scales:{x:{ticks:{color:tx,font:{size:11}},grid:{display:false},border:{color:gr}},y:{beginAtZero:true,ticks:{color:tx,font:{size:11},precision:0},grid:{color:gr},border:{display:false}}}},extra)}
function dataTable(caption,head,rows){return el("details",{class:"dt"},el("summary",{},"Data table"),el("div",{class:"strip"},el("table",{},el("caption",{class:"sr-only"},caption),
 el("thead",{},el("tr",{},...head.map((h,i)=>el("th",{scope:"col",class:i?"n":""},h)))),el("tbody",{},...rows.map(r=>el("tr",{},...r.map((c,i)=>i?el("td",{class:"n"},c):el("th",{scope:"row"},c))))))))}
function chartBlock(host,title,take,cfg,table){const cv=el("canvas",{role:"img","aria-label":`${title}. ${take}`});
 const fig=el("figure",{class:"chartbox"},el("h3",{},title),el("p",{class:"take"},take),el("div",{class:"chart"},cv),table);host.append(fig);
 if(!window.Chart){fig.querySelector(".chart").replaceWith(el("p",{class:"note"},"Chart not drawn: Chart.js did not load (offline?). The data table below has the same numbers."));if(table)table.open=true;return}
 charts.push(new Chart(cv,cfg))}
function bars(labels,data,opts={}){return{type:"bar",data:{labels,datasets:data.map((d,i)=>({label:d.label,data:d.values,backgroundColor:d.color||cssv("--s"+(i+1)),borderRadius:4,borderSkipped:"start",maxBarThickness:28,
 borderColor:cssv("--bg"),borderWidth:{top:0,right:2,left:2,bottom:0},...(d.extra||{})}))},options:baseOpts(opts)}}

/* ---------- tier tabs ---------- */
const TIERS=["S","A","B","C","D"];
function noMatch(clear){return el("div",{class:"empty"},el("p",{},el("b",{},"No cards match.")),el("p",{},"The search or filters exclude every card. ",el("button",{type:"button",class:"chipclr",onclick:clear},"Clear search and filters")))}
// card tile: caption=false gives the image-only deck grid (name in the accessible label and the viewer)
function cardTile(c,ctx,badges,corner,opt={}){const capOn=opt.caption!==false;const a=art(c.img,"",c.name);
 const lab=`${c.rank?"Rank "+c.rank+", ":""}${c.qty>1?c.qty+" ":""}${c.name}${opt.extra?", "+opt.extra:""}`;
 return el(VIEW()?"button":"div",{class:"tile",...(VIEW()?{type:"button",onclick:e=>openViewer(c,ctx,e.currentTarget),"aria-label":lab+", open card"}:{"aria-label":capOn?null:lab,role:capOn?null:"img"})},a,
  corner||(c.qty>1?el("span",{class:"qty","aria-hidden":"true"},"×"+c.qty):null),badges&&badges.length?el("span",{class:"badges","aria-hidden":"true"},...badges):null,
  opt.foot&&opt.foot.length?el("span",{class:"foot","aria-hidden":"true"},...opt.foot):null,
  capOn?el("div",{class:"nm"},(c.rank&&!VIEW()?"#"+c.rank+" ":"")+c.name):null,
  capOn?el("div",{class:"meta"},c.pct!=null?el("span",{class:"num"},popText(c)):null,SHOW.prices&&c.price!=null?el("span",{class:"num"},money(c.price)):null,tag(c.theme),statusPill(c)):null,
  capOn&&c.why&&c.rank?el("div",{class:"why"},c.why):null)}
function popText(c){return `${c.pct}% of decks`+(c.decks!=null&&c.n?` (${c.decks.toLocaleString()} of ${c.n.toLocaleString()})`:c.n?` (n=${c.n.toLocaleString()})`:"")}

/* ---------- rankings (research.json rankings): order, tiers and numbers only from the data ---------- */
function renderRanking(R,host){const key="rank:"+R.id,st=store.get(key,{sort:"rank",q:""}),sel=st.f&&typeof st.f==="object"?st.f:{};
 const hasPct=R.cards.some(c=>c.pct!=null),tiers=[...new Set(R.cards.map(c=>c.tier).filter(Boolean))];
 host.append(el("section",{class:"panel"},el("h2",{},R.title),R.project?el("p",{class:"note"},"Project: "+R.project):null,R.scope?el("p",{},R.scope):null,
  el("p",{},el("b",{},"How it was ranked: "),R.method,R.as_of?`, as of ${R.as_of}`:""),
  el("p",{class:"note"},hasPct?"Inclusion % is popularity: the share of decks that play the card, with the number of decks behind it. It is not a strength rating.":"Ranked by the method above; no usage numbers were recorded.",
   tiers.length?" Tiers come from the research file's method, not from this page.":"")));
 const q=el("input",{type:"search",placeholder:"Search cards",value:st.q||"","aria-label":"Search"});
 const sortSel=el("select",{"aria-label":"Sort"},...[["rank","Rank"],hasPct?["pct","Inclusion (high first)"]:null,["name","Name"]].filter(Boolean).map(([v,t])=>el("option",{value:v,selected:st.sort===v},t)));
 const count=el("p",{class:"count",role:"status"});
 const groups=[tiers.length?{id:"tier",label:"Tier",get:c=>c.tier,opts:tiers.map(t=>({v:t,label:t}))}:null,
  {id:"status",label:"Status",min:1,get:c=>c.status,opts:Object.keys(ST_LABEL).map(k=>({v:k,label:ST_LABEL[k]}))}].filter(Boolean);
 const chips=chipBar(groups,R.cards,sel,draw),list=el("div");[sortSel,q].forEach(i=>i.addEventListener("input",draw));
 host.append(el("section",{class:"panel"},el("div",{class:"ctrl"},q,sortSel,count),chips,list));
 const tile=(c,ctx)=>cardTile(c,ctx,null,el("span",{class:"rk","aria-hidden":"true"},"#"+c.rank));
 function draw(){const s={sort:sortSel.value,q:q.value,f:sel};store.set(key,s);const base=c=>textHit(c,s.q);chips.sync(base);
  let cs=R.cards.filter(c=>base(c)&&chipMatch(chips.groups,sel,c));count.textContent=`Showing ${cs.length} of ${R.cards.length}`;
  cs.sort(s.sort==="name"?(a,b)=>a.name.localeCompare(b.name):s.sort==="pct"?(a,b)=>(b.pct??-1)-(a.pct??-1):(a,b)=>a.rank-b.rank);
  if(!cs.length){list.replaceChildren(noMatch(()=>{q.value="";Object.keys(sel).forEach(k=>delete sel[k]);draw()}));return}
  if(!tiers.length||s.sort!=="rank"){list.replaceChildren(el("div",{class:"grid"},...cs.map(c=>tile(c,cs))));return}
  const rows=[...tiers,null].map(t=>{const inT=cs.filter(c=>(c.tier||null)===t);if(!inT.length)return null;const std=TIERS.includes(t);
   return el("div",{class:"tier"},el("div",{class:"lt"+(t==="C"||t==="D"?" dk":""),style:`background:var(--t-${std?t:"B"})`,role:"img","aria-label":t?"Tier "+t:"No tier"},t||"–"),el("div",{class:"grid"},...inT.map(c=>tile(c,cs))))});
  list.replaceChildren(...rows.filter(Boolean))}
 draw()}
function commanderRows(rows){const box=el("div");rows.forEach(c=>box.append(el("div",{class:"rc"},
  IMG!=="none"&&c.img&&VIEW()?el("button",{type:"button","aria-label":`${c.name}, open card`,"data-img":c.img,onclick:e=>openViewer(c,rows.filter(x=>x.img),e.currentTarget)},art(c.img,"",c.name)):(IMG!=="none"&&c.img?art(c.img,c.name):el("span")),
  el("div",{},el("div",{class:"row"},el("h3",{class:"nm",style:"margin:0"},c.name),c.built?el("span",{class:"pill"},"Built in this report"):null,c.project&&D.multi?el("span",{class:"note"},c.project):null),
   el("p",{},c.strategy),
   el("div",{class:"two"},c.advantages.length?el("div",{},el("h4",{},"Advantages"),el("ul",{},...c.advantages.map(x=>el("li",{},x)))):null,
    c.disadvantages.length?el("div",{},el("h4",{},"Disadvantages"),el("ul",{},...c.disadvantages.map(x=>el("li",{},x)))):null),
   c.theme_fit?el("p",{},el("b",{},"Theme fit: "),c.theme_fit):null,
   el("p",{class:"note"},c.legal_check?"Eligibility checked: "+c.legal_check:"Eligibility check not recorded in the research."),evidenceLinks(c.evidence)))));return box}
function renderResearch(R,host){const proj=R.project||null,T=researchTabFor(proj)||(R.candidates?R:null);
 host.append(noticesNode(null,proj)||"",el("section",{class:"panel"},el("h2",{},R.title),el("p",{},R.question),
  T&&T.version?el("p",{class:"note"},`Research version ${T.version}${T.created?", "+niceDate(T.created):""}.`):null,
  feasibility(T&&T.feasibility)));
 if((R.commanders||[]).length)host.append(el("section",{class:"panel"},el("h2",{},"Commanders compared"),el("p",{class:"note"},"From the research file: each commander's strategy, advantages and disadvantages as recorded, with the sources behind them."),commanderRows(R.commanders)));
 const rb=researchBlock(null,t=>(t.project||null)===proj,T);
 if(rb)host.append(el("section",{class:"panel",id:"sec-research"},el("div",{class:"sec-head"},el("h2",{},"Findings"),rb.expand,el("p",{class:"lede"},rb.lede)),rb.node));
 const n=D.rankings.filter(r=>(r.project||null)===proj);
 if(n.length)host.append(el("section",{class:"panel"},el("h2",{},"Rankings"),el("div",{class:"row"},...n.map(r=>el("button",{class:"btn",type:"button",onclick:()=>{go("rank-"+r.id);scrollTo(0,0)}},"Open "+r.title)))))}
const researchTabFor=proj=>D.research_tab.find(x=>(x.project||null)===(proj||null))||null;
// a project's findings live in its research tab when it has one; otherwise in the deck page (one-project reports) or the sources tab
const hasHome=proj=>D.research.some(r=>(r.project||null)===(proj||null))||(!IN_DECK&&!!researchTabFor(proj));
function feasibility(F){if(!F||typeof F!=="object")return null;const rest=Object.entries(F).filter(([k,v])=>!["question","verdict"].includes(k)&&typeof v==="string");
 return el("div",{class:"empty",style:"margin-top:var(--sp-3)"},el("p",{},el("b",{},"Feasibility: "),F.verdict||""),F.question?el("p",{class:"note"},F.question):null,...rest.map(([k,v])=>el("p",{class:"note"},cap(k.replace(/_/g," "))+": "+v)))}
/* ---------- deck tabs ---------- */
const BR={1:"Exhibition",2:"Core",3:"Upgraded",4:"Optimized",5:"cEDH"};
const PIP_NM={W:"white",U:"blue",B:"black",R:"red",G:"green",C:"colorless",S:"snow",P:"Phyrexian"};
function pips(cost){const syms=[...String(cost||"").matchAll(/\{([^}]+)\}/g)].map(m=>m[1]);if(!syms.length)return el("span",{class:"pips"});
 return el("span",{class:"pips"},el("span",{class:"sr-only"},"Mana cost: "+syms.map(s=>s.split("/").map(x=>PIP_NM[x]||x).join(" or ")).join(", ")),
  el("span",{"aria-hidden":"true"},...syms.map(s=>el("span",{class:"pip "+(/^[WUBRG]$/.test(s)?s:""),title:s},s.replace("/","")))))}
const enc=encodeURIComponent;
function cardLinks(c){const n=c.card||c.name,front=n.split(" // ")[0];
 const slug=front.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/['’,.!?:"]/g,"").replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");
 return {scryfall:c.set&&c.cn?`https://scryfall.com/card/${c.set}/${enc(c.cn)}`:`https://scryfall.com/search?q=${enc('!"'+n+'"')}`,edhrec:`https://edhrec.com/cards/${slug}`,
  tcgplayer:c.tcg||`https://www.tcgplayer.com/search/magic/product?productLineName=magic&q=${enc(front)}`,cardmarket:c.cm||`https://www.cardmarket.com/en/Magic/Products/Search?searchString=${enc(front)}`}}
function ext(href,label,cls,...kids){return el("a",{href,target:"_blank",rel:"noopener",class:cls||"","aria-label":label||null,title:label||null},...kids)}
function linkRow(c){const L=cardLinks(c);return el("div",{class:"links"},ext(L.scryfall,"Open on Scryfall","","Scryfall ↗"),ext(L.edhrec,"Open on EDHREC","","EDHREC ↗"),ext(L.tcgplayer,"Buy on TCGplayer","","TCGplayer ↗"),ext(L.cardmarket,"Buy on Cardmarket","","Cardmarket ↗"))}
// text color with 4.5:1 on a theme color: dark ink on light colors, white on dark ones
function inkFor(c){const v=/^var\((--[\w-]+)\)$/.exec(String(c).trim());if(v)c=cssv(v[1]);const m=/^#?([0-9a-f]{6})$/i.exec(String(c).trim());if(!m)return{ink:"#fff"};const n=parseInt(m[1],16),lin=x=>{x/=255;return x<=.03928?x/12.92:((x+.055)/1.055)**2.4};
 const L=.2126*lin(n>>16)+.7152*lin(n>>8&255)+.0722*lin(n&255),dark=(L+.05)/.056,white=1.05/(L+.05);
 return dark>=4.5&&dark>=white?{ink:"#0d111a"}:white>=4.5?{ink:"#fff"}:{ink:"#fff",bg:`color-mix(in srgb,${c} 72%,#000)`}}  // mid tones: darken the tag until white text reaches 4.5:1
function tag(label){if(!D.theme||!label)return null;const c=themeColor(label),k=c==="var(--gold)"?{ink:"var(--gold-ink)"}:inkFor(c);return label==="off-theme"?el("span",{class:"tp off"},"Off-theme"):el("span",{class:"tp",style:`--c:${k.bg||c};--ink:${k.ink}`},label)}
const mark=label=>label&&!isDefaultTheme(label)?tag(label):null;
// "32 of 35 themed cards on theme; 64 exempt (lands, utility) unmarked" from theme_stats; null without it
function themeLine(d){const t=d.theme_stats;if(!t)return null;const n=(t.on||0)+(t.exception||0)+(t.off||0);
 return `${t.on||0} of ${n} themed cards on theme`+(t.exception?`, ${plural(t.exception,"exception")}`:"")+(t.off?`, ${t.off} off-theme`:"")+(t.exempt?`; ${t.exempt} exempt (lands, utility) unmarked`:"")+((d.theme&&d.theme.tiers||[]).length?" ("+d.theme.tiers.map(x=>`${x.label} ${x.count}`).join(", ")+")":"")}  // "On theme" on 89 of 100 cards is noise; the theme filter still has it
const did=d=>d.id||"b"+d.bracket;  // a deck is a build variant (b3, b4-budget...)
const norm=s=>String(s||"").toLowerCase().replace(/[^a-z0-9]+/g,"");
// Every build of every group and commander behind one build bar; picking one redraws in place (no reload, no tabs).
function renderDecks(host){
 const E=D.groups.flatMap(G=>G.commanders.flatMap(c=>c.decks.map(d=>({G,c,d,key:c.slug+"/"+did(d)}))));
 const many=new Set(E.map(x=>x.c.slug)).size>1,defB=D.default_bracket;
 let cur=E.find(x=>x.key===store.get("build"))||E.find(x=>x.d.bracket===defB)||E[0];
 const body=el("div");host.append(body);
 const pick=x=>{cur=x;store.set("build",x.key);history.replaceState(null,"","#build="+encodeURIComponent(x.key));
  const y=scrollY;draw();scrollTo(0,y);const f=body.querySelector('#bsel');if(f)f.focus({preventScroll:true})};
 function draw(){charts.forEach(c=>c.destroy());charts=[];if(secObs){secObs.disconnect();secObs=null}hidePop();placeTheme(null);body.replaceChildren();
  const {G,c,d:deck}=cur;applyLook(c.look);
  const flat=orderedCards(deck);CUR={G,slug:c.slug,b:did(deck),deck,key:cur.key};
  const asTitle=heroOwnsTitle();  // one h1: the hero carries the page title
  document.body.classList.toggle("herotitle",asTitle);document.body.classList.add("has-secnav");
  const other=E.find(x=>x.key===store.get("cmp:"+cur.key)&&x!==cur);
  const secs=[["sec-overview","Overview"]],parts=[];
  const add=(id,label,node)=>{if(node){secs.push([id,label]);parts.push(node)}};
  if(other)add("sec-diff","Differences",diffSection(deck,other));
  add("sec-cards","Cards",deckList(deck));
  add("sec-stats","Stats",statsSection(deck));
  add("sec-plan","Plan",planSection(deck));
  add("sec-changes","Changes",changesSection(G,c,deck));
  if(IN_DECK)add("sec-research","Research",researchSection(deck));
  add("sec-audit","Audit",auditSection(deck));
  if((G.alts||[]).length)add("sec-alts","Alternatives",el("section",{class:"sec",id:"sec-alts","aria-labelledby":"h-alts"},el("div",{class:"sec-head"},el("h2",{id:"h-alts"},"Commanders compared"),el("p",{class:"lede"},"Alternatives from the research file, as recorded there; built ones are marked.")),commanderRows(G.alts)));
  if(IN_DECK&&SHOW.sources)add("sec-sources","Sources",sourcesSection());
  const nav=secNav(secs);
  body.append(...[E.length>1?buildBar(E,cur,pick,many):null,hero(c,deck,flat,asTitle),nav,noticesNode(deck),...parts].filter(Boolean));
  placeTheme(nav.querySelector(".in"));watchSections(nav)}
 draw()}
// the build picker: "Bracket 3 · Upgraded" (text everywhere a plain name is needed), and the styled picker below
function buildRest(x,many){return (many&&x.G.commanders.length>1?x.c.name+": ":"")+(String(x.d.label||"").replace(new RegExp("^B"+x.d.bracket+"\\b\\s*"),"").trim()||BR[x.d.bracket]||"")}
function buildName(x,many){const r=buildRest(x,many);return `Bracket ${x.d.bracket}`+(r?` · ${r}`:"")}
// A dropdown whose options carry tags: a button that opens a listbox (ARIA listbox pattern). Keyboard: arrows, Home/End,
// Enter/Space to choose, Escape to close; a click outside closes it. items: [{key, group?, bracket?, name, sub?, state?}]
function picker(id,label,items,curKey,onPick){const cur=items.find(x=>x.key===curKey)||items[0];
 const row=x=>[x.bracket?el("span",{class:"bchip b"+x.bracket,title:`Bracket ${x.bracket}${BR[x.bracket]?" ("+BR[x.bracket]+")":""}`},"B"+x.bracket):null,
  el("span",{class:"pk-name"},el("b",{},x.name),x.sub?el("small",{},x.sub):null),x.state?stateTag(x.state):null];
 const btn=el("button",{type:"button",class:"pk-btn",id,"aria-haspopup":"listbox","aria-expanded":"false","aria-controls":id+"-lb","aria-labelledby":`${id}-l ${id}`},...row(cur),el("span",{class:"pk-caret","aria-hidden":"true"},"▾"));
 const list=el("div",{class:"pk-list",role:"listbox",id:id+"-lb",tabindex:"-1","aria-labelledby":id+"-l",hidden:true}),opts=[];
 let g0,a=items.indexOf(cur);
 items.forEach((x,i)=>{if(x.group&&x.group!==g0){g0=x.group;list.append(el("div",{class:"pk-g",role:"presentation"},x.group))}
  const o=el("div",{class:"pk-opt",role:"option",id:`${id}-o${i}`,"aria-selected":x===cur,onclick:()=>choose(i),onpointermove:()=>act(i)},...row(x),x===cur?el("span",{class:"pk-check","aria-hidden":"true"},"✓"):null);
  opts.push(o);list.append(o)});
 const act=i=>{a=Math.max(0,Math.min(items.length-1,i));opts.forEach((o,j)=>o.classList.toggle("on",j===a));list.setAttribute("aria-activedescendant",opts[a].id);opts[a].scrollIntoView({block:"nearest"})};
 const outside=e=>{if(!wrap.contains(e.target))close(false)};
 const open=()=>{list.hidden=false;btn.setAttribute("aria-expanded","true");act(items.indexOf(cur));list.focus({preventScroll:true});document.addEventListener("pointerdown",outside,true)};
 const close=(focus=true)=>{list.hidden=true;btn.setAttribute("aria-expanded","false");document.removeEventListener("pointerdown",outside,true);if(focus)btn.focus({preventScroll:true})};
 const choose=i=>{close();if(items[i]!==cur)onPick(items[i].key)};
 btn.onclick=()=>list.hidden?open():close();
 btn.onkeydown=e=>{if(e.key==="ArrowDown"||e.key==="ArrowUp"){e.preventDefault();open()}};
 list.onkeydown=e=>{const k=e.key,stop=()=>e.preventDefault();
  if(k==="ArrowDown"){stop();act(a+1)}else if(k==="ArrowUp"){stop();act(a-1)}else if(k==="Home"){stop();act(0)}else if(k==="End"){stop();act(items.length-1)}
  else if(k==="Enter"||k===" "){stop();choose(a)}else if(k==="Escape"){stop();close()}else if(k==="Tab")close(false)};
 const wrap=el("div",{class:"bgrp pk"},el("span",{class:"bgl",id:id+"-l"},label),btn,list);return wrap}
function buildBar(E,cur,pick,many){const grouped=new Set(E.map(x=>x.G)).size>1,byKey=k=>E.find(x=>x.key===k);
 const item=x=>{const rest=buildRest(x,many);return {key:x.key,group:grouped?x.G.title:null,bracket:x.d.bracket,name:rest||`Bracket ${x.d.bracket}`,
  sub:[rest===BR[x.d.bracket]?"":BR[x.d.bracket],SHOW.prices&&(x.d.stats||{}).price!=null?money(x.d.stats.price):""].filter(Boolean).join(" · "),state:(x.d.audit_view||{}).verdict}};
 const ck="cmp:"+cur.key;
 const build=picker("bsel","Build",E.map(item),cur.key,k=>pick(byKey(k)));
 const cmp=picker("cmpsel","Compare with",[{key:"",name:"Nothing",sub:"show this build only"},...E.filter(x=>x!==cur).map(item)],store.get(ck)||"",k=>{store.set(ck,k);pick(cur)});
 cmp.classList.add("bcmp");
 return el("nav",{class:"buildbar","aria-label":"Builds"},el("div",{class:"in"},build,cmp))}
// what changes between two builds: cards only in one of them, and copies that differ (basics)
function diffSection(deck,o){const m=d=>new Map(d.cards.filter(c=>!c.commander).map(c=>[c.name,c])),A=m(deck),B=m(o.d),lab=buildName(o,false);
 const only=[...A.values()].filter(c=>!B.has(c.name)),theirs=[...B.values()].filter(c=>!A.has(c.name)),qty=[...A.values()].filter(c=>B.has(c.name)&&B.get(c.name).qty!==c.qty);
 const s=section("sec-diff","Compared with "+lab,`${plural(only.length,"card")} only in this build and ${plural(theirs.length,"card")} only in ${lab}; everything else is in both.`);
 const col=(h,cs,list)=>el("div",{},el("h3",{},h+" ",el("span",{class:"cn"},String(cs.length))),cs.length?el("div",{class:"row"},...cs.map(c=>cardChip(c,list))):el("p",{class:"note"},"None."));
 s.append(el("div",{class:"two"},col("Only in this build",only,orderedCards(deck)),col("Only in "+lab,theirs,orderedCards(o.d))));
 if(qty.length)s.append(el("p",{class:"note"},"Different counts: "+qty.map(c=>`${c.name} ${B.get(c.name).qty} → ${c.qty}`).join(", ")+"."));
 return s}
let CUR={};
// proposed recommendations that would cut this card (the decklist marks them with a swap sign)
function swapsFor(name){return ((CUR.deck||{}).recs_view||{proposed:[]}).proposed.filter(r=>r.cut===name)}
function orderedCards(d){return [...d.cards].sort((a,b)=>(b.commander-a.commander)||(GROUP_ORDER.indexOf(displayGroup(a))-GROUP_ORDER.indexOf(displayGroup(b)))||(a.mv-b.mv)||a.name.localeCompare(b.name))}
function section(id,title,lede,...extra){return el("section",{class:"sec",id,"aria-labelledby":"h-"+id},el("div",{class:"sec-head"},el("h2",{id:"h-"+id},title),...extra,lede?el("p",{class:"lede"},lede):null))}

/* ---------- section nav: sticky, highlights the section in view ---------- */
function secNav(items){return el("nav",{class:"secnav","aria-label":"Sections"},el("div",{class:"in"},el("ul",{},...items.map(([id,label])=>el("li",{},el("a",{href:"#"+id},label))))))}
function watchSections(nav){const ul=nav.querySelector("ul"),map=new Map([...nav.querySelectorAll("a")].map(a=>[a.getAttribute("href").slice(1),a]));
 secObs=new IntersectionObserver(es=>es.forEach(e=>{if(!e.isIntersecting)return;map.forEach(a=>a.removeAttribute("aria-current"));const a=map.get(e.target.id);
  if(a){a.setAttribute("aria-current","location");const l=a.offsetLeft-ul.offsetLeft;if(l<ul.scrollLeft||l+a.offsetWidth>ul.scrollLeft+ul.clientWidth)ul.scrollLeft=l-24}}),{rootMargin:"-35% 0px -60% 0px"});
 requestAnimationFrame(()=>map.forEach((a,id)=>{const s=document.getElementById(id);if(s&&secObs)secObs.observe(s)}))}

/* ---------- hero: name, meta line, verdict, status, 3-4 stats, actions ---------- */
function heroStats(deck){const s=deck.stats||{},out=[];
 if(SHOW.prices)out.push({label:"Value",value:s.price!=null?money(s.price):"—",context:s.price==null?"No price data: Scryfall had no prices for this list":(s.unpriced&&s.unpriced.length?`excludes ${plural(s.unpriced.length,"unpriced card")}`:"listed printings, Scryfall daily")});
 out.push({label:"Avg mana value",value:s.avg_mv??"—",context:s.avg_mv==null?"Not computed: deck_check gave no curve":"nonland cards"});
 const t=(s.template||{}).lands;
 out.push({label:"Lands",value:s.lands+(s.mdfc_lands?` + ${s.mdfc_lands} MDFC`:""),context:t?`typical ${t[1]}–${t[2]}`:"basic and nonbasic"});
 if(deck.theme&&deck.theme.on_theme_pct!=null){const c=deck.theme.counts||{},ex=Object.entries(c).filter(([k])=>!isDefaultTheme(k)).reduce((a,[,v])=>a+v,0);
  out.push({label:"On theme",value:deck.theme.on_theme_pct+"%",context:ex?`${ex} marked as exception or off-theme`:"every card"})}
 else{const g=s.game_changers||[];out.push({label:"Game Changers",value:g.length,context:g.length?g.join(", "):"none in this list"})}
 return out.slice(0,4)}
// one commander on the page (however many builds or projects): its hero carries the h1 and the masthead hides
const heroOwnsTitle=()=>D.groups.length>0&&new Set(D.groups.flatMap(g=>g.commanders.map(c=>c.name))).size===1;
function hero(cur,deck,flat,asTitle){const hTag=asTitle?"h1":"h2";const H=cur.hero||{},n=deck.cards.reduce((a,c)=>a+c.qty,0),AV=deck.audit_view;
 const B=deck.hero||(cur.decks.length===1?H:{});  // the selected build's facts (meta, stats, verdict); H keeps the commander's name and art
 const meta=B.meta?B.meta:[`Bracket ${deck.bracket}${BR[deck.bracket]?", "+BR[deck.bracket]:""}`,plural(n,"card"),deck.version?`Version ${deck.version}`:null,deck.project&&D.multi?deck.project:null].filter(Boolean);
 const stats=B.stats&&B.stats.length?B.stats:heroStats(deck);
 const vl=AV.verdict_label,pitch=deck.summary.pitch||null;
 const verdict=B.verdict&&!(vl&&String(B.verdict).startsWith(vl))?B.verdict:pitch;  // a verdict that only repeats the audit label + counts is already the status row
 const cmds=deck.cards.filter(c=>c.commander),cmd=cmds[0],artKey=H.art||cur.img||(cmd||{}).img,cname=cmds.length>1?cmds.map(c=>c.name).join(" + "):H.name||cur.name,name=asTitle&&D.title?D.title:cname;
 const sub=asTitle?[norm(D.title).includes(norm(cname))?null:"Commander: "+cname,D.subtitle&&!meta.some(m=>norm(D.subtitle).includes(norm(m)))?D.subtitle:null].filter(Boolean):[];
 const crop=MODE==="showcase"&&H.art_crop&&(IMG==="cdn"||!/^https?:/i.test(H.art_crop))?H.art_crop:null;  // artifact pages block outside images: a remote crop only in cdn mode
 const duo=cmds.length>1;  // partners, a background, a Doctor's companion: both cards side by side
 const artBox=IMG!=="none"&&artKey?el("div",{class:"hero-art"+(duo?" duo":"")},...(duo?cmds:[cmd]).map(cc=>VIEW()&&cc?el("button",{type:"button",class:"hero-card","aria-label":`${cc.name}, open card`,"data-img":cc.img,onclick:e=>openViewer(cc,flat,e.currentTarget)},art(duo?cc.img:artKey,"",cc.name)):art(artKey,name))):null;
 const counts=AV.groups.length?AV.counts:null;
 const status=el("div",{class:"hstatus"},el("span",{class:"lbl"},"Audit"),stateTag(AV.verdict),
  counts?el("span",{},[counts.fail?plural(counts.fail,"fail"):null,counts.warning?plural(counts.warning,"warning"):null,counts.unverified?`${counts.unverified} unverified`:null].filter(Boolean).join(", ")||"no issues"):null,
  el("a",{href:"#sec-audit"},"See the audit"));
 const copy=el("button",{type:"button",class:"btn copy",onclick:e=>copyText(deck.moxfield||deck.cards.map(x=>`${x.qty} ${x.name}${x.set?` (${x.set.toUpperCase()}) ${x.cn}`:""}`).join("\n"),e.currentTarget)},"Copy for Moxfield");
 const r0=deck.rule0_items||[];
 return el("section",{class:"hero",id:"sec-overview","aria-labelledby":"hero-name"},crop?el("div",{class:"hero-bg",style:`background-image:url("${crop.replace(/"/g,"%22")}")`}):null,
  el("div",{class:"hero-in"+(artBox?"":" noart")},artBox,
   el("div",{class:"hero-head"},el(hTag,{class:"hname",id:"hero-name"},name),...sub.map(x=>el("p",{class:"hsub"},x)),el("ul",{class:"meta"},...meta.map(m=>el("li",{},m)))),
   el("div",{class:"hero-body"},verdict?el("p",{class:"verdict"},verdict):null,status,
    el("dl",{class:"tiles"},...stats.map(x=>el("div",{class:"stat"},el("dt",{},x.label),el("dd",{class:"v"},x.value==null||x.value===""?"—":String(x.value)),x.value==null||x.value===""?el("dd",{class:"ctx"},"Not recorded"+(x.context?": "+x.context:"")):x.context?el("dd",{class:"ctx"},x.context):null))),
    el("div",{class:"hactions"},copy),
    r0.length?el("div",{class:"rule0"},el(asTitle?"h2":"h3",{class:"lbl"},"Rule 0"),el("dl",{},...r0.flatMap((x,i)=>[el("dt",{},i&&r0[i-1].label===x.label?"":x.label),el("dd",{},x.value)]))):null)))}

/* ---------- notices: research older than the deck, stale data, notes left out ---------- */
function noticesNode(deck,proj){if(proj===undefined&&deck)proj=deck.project||null;
 const N=D.notices.filter(n=>proj===undefined||!n.project||n.project===proj).map(n=>({...n,text:(proj===undefined&&n.project?n.project+": ":"")+n.text}));
 if(deck&&deck.future)N.push({level:"info",text:"Planned for release: "+[deck.future.note,(deck.future.waits_for||[]).map(w=>`${w.card}${w.releases?" ("+w.releases+")":""}`).join(", ")].filter(Boolean).join(". ")});
 if(deck&&deck.audit_view.verdict==="audit out of date"&&!N.some(n=>/audit/i.test(n.text)))N.push({level:"warn",text:"The audit on file checked another version of this list, so its results are hidden. Re-run the audit to see current results."});
 if(!N.length)return null;
 return el("div",{class:"notices",role:"region","aria-label":"Notices"},...N.map(n=>el("p",{class:"notice"+(n.level==="warn"?" warn":"")},statusIcon(n.level==="warn"?"warning":"info"),el("span",{},el("span",{class:"sr-only"},n.level==="warn"?"Warning: ":"Note: "),n.text))))}
/* ---------- plan: one readable column, key cards beside it ---------- */
const PLAN_OPEN=/^(why this commander|archetype|key synergies|known limitations)$/i;
function planSection(d){const s=d.summary;
 const block=(t,items)=>items&&items.length?[el("h3",{},t),items.length===1?el("p",{},items[0]):el("ul",{},...items.map(x=>el("li",{},x)))]:[];
 const col=el("div",{class:"prose"});
 if(s.pitch)col.append(el("p",{class:"lede"},s.pitch));
 if(s.wins)col.append(...block("How it wins",[s.wins]));
 const secs=s.sections||[],open=secs.filter(x=>PLAN_OPEN.test(x.title)),rest=secs.filter(x=>!PLAN_OPEN.test(x.title));
 open.forEach(x=>col.append(...block(x.title,x.items)));
 col.append(...block("Strengths",s.strengths),...block("Disadvantages",s.disadvantages));
 const rail=rest.length?el("div",{class:"keyrail"},el("div",{class:"morebox"},el("h3",{class:"railh"},"For reference"),
  ...rest.map(x=>el("details",{class:"more"},el("summary",{},el("h3",{},x.title),el("span",{class:"cn"},x.items.length)),x.items.length===1?el("p",{},x.items[0]):el("ul",{},...x.items.map(i=>el("li",{},i))))))):null;
 if(!col.children.length&&!rail)return null;
 const sec=section("sec-plan","Game plan",null);sec.append(el("div",{class:"plan"},col,rail));return sec}
/* ---------- stats: composition, price, charts (near the deck they describe) ---------- */
function statsSection(d){const s=d.stats||{},sec=section("sec-stats","Stats","Counts and prices come from deck_check (Scryfall data); nothing here is estimated.");
 const grid=el("div",{class:"statgrid"}),comp=el("div"),price=el("div"),side=el("div");grid.append(comp,side);sec.append(grid);  // left: roles and theme; right: price, Game Changers, rule roles
 if(s.template){const rows=Object.entries(s.template),yours=s.template_kind==="yours",word=yours?"your target":"the typical",
   rng=(lo,hi)=>hi==null?`${lo}+`:lo===hi?`${lo}`:`${lo}–${hi}`,  // targets may be open-ended ("10+") or exact ("2")
   off=rows.filter(([,[h,lo,hi]])=>h<lo||(hi!=null&&h>hi));
  comp.append(el("h3",{},yours?"Against your targets":"Against a typical deck"),el("p",{class:"take"},off.length?off.map(([r,[h,lo,hi]])=>`${cap(r)} ${h<lo?"below":"above"} ${word} ${rng(lo,hi)} (${h})`).join("; ")+"; the rest in range.":`Every role is inside ${yours?"your targets":"the typical range"}.`),
   ...rows.map(([role,[have,lo,hi]])=>{const top=hi==null?Math.max(lo*1.4,have):hi,mx=Math.max(top*1.4,have,1),cls=have<lo?"short":hi!=null&&have>hi?"over":"ok";
    return el("div",{class:"bullet"},el("span",{},cap(role)),el("div",{class:"bar",role:"img","aria-label":`${role}: ${have}, ${word} ${rng(lo,hi)}`},el("div",{class:"band",style:`left:${lo/mx*100}%;width:${Math.max(top-lo,0.3)/mx*100}%`}),el("div",{class:"val",style:`width:${have/mx*100}%`})),
     el("span",{class:"num "+cls},`${have} of ${rng(lo,hi)} `,el("span",{"aria-hidden":"true"},cls==="ok"?"✓":cls==="short"?"▼":"▲"),el("span",{class:"sr-only"},cls==="ok"?"in range":cls==="short"?"low":"above")))}),
   el("div",{class:"legend"},el("span",{},"Bar: this deck"),el("span",{},yours?"Green band: your target":"Green band: typical range"),el("span",{class:"ok"},"✓ in range"),el("span",{class:"short"},"▼ low"),el("span",{class:"over"},"▲ above (fine: one card can fill several roles)")),
   el("p",{class:"note"},s.template_source||"Starting ranges, not laws."))}
 else comp.append(el("h3",{},"Against a typical deck"),el("div",{class:"empty"},el("p",{},el("b",{},"No role counts for this build.")),el("p",{},"deck_check gave no Oracle-text roles, so ramp, draw and removal are not counted. Rebuild the page after deck_check runs on this list.")));
 if(d.theme){const c=d.theme.counts||{},TL=themeLine(d);comp.append(el("h3",{},"Theme"),el("p",{},el("b",{},TL?cap(TL):`${d.theme.on_theme_pct??"—"}% on theme`),el("span",{class:"muted"},TL?"; commander excluded.":" (commander excluded)")),
  TL?"":el("div",{class:"row note"},...Object.entries(c).map(([k,v])=>el("span",{},isDefaultTheme(k)?el("span",{class:"pill",style:`--c:${themeColor(k)}`},el("i"),k):tag(k)," ",el("b",{class:"num"},v)))))}  // label counts include exempt cards: theme_stats replaces them
 const gcs=s.game_changers||[];const byN=Object.fromEntries(d.cards.map(c=>[c.name.toLowerCase(),c]));
 if(SHOW.prices)side.append(price);side.append(el("h3",{},"Game Changers"),gcs.length?el("div",{class:"cardrow"},...gcs.map(g=>cardChip(byN[g.toLowerCase()]||{name:g},orderedCards(d)))):el("p",{class:"note"},"None in this list."));
 const R=Object.entries(s.roles||{}).filter(([r])=>r!=="land");
 if(R.length)side.append(el("p",{class:"note"},el("b",{},"Roles from Oracle-text rules: "),R.sort((a,b)=>b[1]-a[1]).map(([r,n])=>`${r} ${n}`).join(", "),". A card can count in several roles; open a card to see the rule that matched."));
 if((s.label_diff||[]).length)side.append(el("details",{class:"more"},el("summary",{},`${s.label_diff.length} builder's label${s.label_diff.length>1?"s differ":" differs"} from the rule-based roles`),
  el("ul",{class:"note"},...s.label_diff.map(x=>el("li",{},`${x.name}: builder's label "${x.label}"; rules: ${x.rules.length?x.rules.join(", "):"none matched"}`)))));
 if(SHOW.prices){price.append(el("h3",{},"Price"));const L=s.price_ladder,tl=[];
  tl.push(["Listed printings",money(s.price),s.price==null?"No price data from Scryfall":s.unpriced&&s.unpriced.length?`excludes ${plural(s.unpriced.length,"unpriced card")}`:"the printings in this list"]);
  if(L){tl.push(["Cheapest printings",money(L.affordable_usd),"same cards, cheapest copies"]);tl.push(["Premium printings",money(L.premium_usd),"same cards, priciest copies"])}
  price.append(el("dl",{class:"tiles three",style:"margin-top:var(--sp-2)"},...tl.map(([k,v,c])=>el("div",{class:"stat price"},el("dt",{},k),el("dd",{class:"v"},v),el("dd",{class:"ctx"},c)))));
  if(L)price.append(el("p",{class:"note"},`${cap(L.note)}. As of ${L.as_of}. Open a card to see its cheapest and priciest printing.`));
  else price.append(el("p",{class:"note"},"Price ladder not available: deck_check found no cheapest-printing data. Prices above are the listed printings only."));
  if(s.unpriced&&s.unpriced.length)price.append(el("p",{class:"flag"},`Price excludes ${plural(s.unpriced.length,"unpriced card")}: ${s.unpriced.join(", ")}`));
  if(s.price_note)price.append(el("p",{class:"note"},s.price_note))}
 if(SHOW.charts)sec.append(deckCharts(d));
 return sec}
function cardChip(c,list){return c.img&&VIEW()?el("button",{type:"button",class:"cardchip","data-img":c.img,onclick:e=>openViewer(c,list,e.currentTarget)},c.name):el("span",{class:"cardchip"},c.name)}
function deckCharts(d){const s=d.stats||{},ch=el("div",{class:"charts"});const M=s.mana||{},pipsD=M.pips,srcD=M.sources,na=[];
 if(s.curve){const k=Object.keys(s.curve),v=Object.values(s.curve),i=v.indexOf(Math.max(...v));
  chartBlock(ch,"Mana curve",`Nonland cards peak at mana value ${k[i]} (${v[i]} cards)${s.avg_mv!=null?`; the average is ${s.avg_mv}`:""}.`,bars(k,[{label:"Nonland cards",values:v,color:cssv("--accent")}],{plugins:{legend:{display:false}}}),
   dataTable("Nonland cards per mana value",["Mana value","Cards"],k.map((x,j)=>[x,v[j]])))}else na.push("mana curve");
 const T=GROUP_ORDER.filter(g=>(s.type_counts||{})[g]).map(g=>[g,s.type_counts[g]]);
 if(T.length){const tot=T.reduce((a,[,n])=>a+n,0),top=T.filter(([g])=>g!=="Commander").sort((a,b)=>b[1]-a[1]),L={m:s.mdfc_lands||0,text:plural((s.type_counts||{}).Land||0,"land")+(s.mdfc_lands?` + ${s.mdfc_lands} MDFC`:"")};
  chartBlock(ch,"Card types",`${cap(TYPE_PL[top[0][0]])} lead with ${top[0][1]} of ${tot} cards${top[1]?`, then ${TYPE_PL[top[1][0]]} (${top[1][1]})`:""}. Grouped as in the decklist${L.m?`; ${L.text}`:""}.`,
   bars(T.map(([g])=>g),[{label:"Cards",values:T.map(([,n])=>n),color:T.map(([g])=>{const v=/var\((--[\w-]+)\)/.exec(TYPE_COLOR[g]);return v?cssv(v[1]):TYPE_COLOR[g]})}],{indexAxis:"y",plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,ticks:{color:cssv("--muted"),precision:0},grid:{color:cssv("--border")}},y:{ticks:{color:cssv("--muted")},grid:{display:false}}}}),
   dataTable("Cards per type group",["Type group","Cards"],[...T,["Total",tot]]))}
 if(pipsD&&srcD){const cols=Object.keys(pipsD).filter(k=>pipsD[k]);const MC={W:"#e9e5b8",U:"#6fa3d6",B:"#8c8079",R:"#d96b47",G:"#6f9a5e"},NM={W:"White",U:"Blue",B:"Black",R:"Red",G:"Green"};
  if(cols.length){const thin=[...cols].sort((a,b)=>(srcD[a]||0)/pipsD[a]-(srcD[b]||0)/pipsD[b])[0];
   chartBlock(ch,"Mana sources against colour needs",cols.length>1?`${NM[thin]||thin} has the thinnest support: ${srcD[thin]||0} sources for ${pipsD[thin]} pips in mana costs.`:`${NM[thin]||thin}: ${srcD[thin]||0} sources for ${pipsD[thin]} pips in mana costs.`,
    bars(cols.map(k=>NM[k]||k),[{label:"Pips in costs",values:cols.map(k=>pipsD[k]),color:cols.map(k=>MC[k])},{label:"Mana sources",values:cols.map(k=>srcD[k]||0),color:cssv("--muted")}],{plugins:{legend:{display:false}}}),
    dataTable("Pips and sources per colour",["Colour","Pips","Sources"],cols.map(k=>[NM[k]||k,pipsD[k],srcD[k]||0])));
   ch.lastChild.querySelector(".take").after(el("div",{class:"legend",style:"margin:0 0 var(--sp-2)"},el("span",{class:"row",style:"gap:6px"},...cols.map(k=>el("span",{class:"sw",style:`--c:${MC[k]}`,"aria-hidden":"true"})),"Left bar: pips in mana costs, in the mana's colour"),el("span",{class:"row",style:"gap:6px"},el("span",{class:"sw",style:"--c:var(--muted)","aria-hidden":"true"}),"Right bar: mana sources")))}}
 else na.push("mana sources against colour needs");
 const C=s.cast_by_turn;
 if(C&&C.by_turn){const t=Object.keys(C.by_turn),even=t.find(x=>C.by_turn[x]>=.5),pct=x=>Math.round(C.by_turn[x]*1000)/10;
  chartBlock(ch,`Commander cast by turn`,even?`Better than even odds to cast the commander (mana value ${C.commander_mv}) by turn ${even}: ${pct(even)}%.`:`The commander (mana value ${C.commander_mv}) is cast by turn ${t[t.length-1]} in ${pct(t[t.length-1])}% of games.`,
   bars(t.map(x=>"T"+x),[{label:"Chance to have cast the commander",values:t.map(pct),color:cssv("--accent")}],{plugins:{legend:{display:false},tooltip:{callbacks:{label:x=>`${x.raw}%`}}},scales:{x:{ticks:{color:cssv("--muted")},grid:{display:false}},y:{beginAtZero:true,max:100,ticks:{color:cssv("--muted"),callback:v=>v+"%"},grid:{color:cssv("--border")}}}}),
   dataTable("Chance to have cast the commander by turn",["Turn","Chance"],t.map(x=>["Turn "+x,pct(x)+"%"])));
  ch.lastChild.append(el("p",{class:"note"},`${C.runs.toLocaleString()} simulated games, seed ${C.seed}, ${C.on_play?"on the play":"on the draw"}. Assumptions: ${C.assumptions}.`))}
 else na.push("cast-by-turn simulation");
 if(na.length)ch.append(el("div",{class:"empty"},el("p",{},el("b",{},"Not available for this build: "+na.join(", ")+".")),el("p",{},"deck_check returned no data for these, and the page never estimates them. Rebuild after deck_check succeeds on this list.")));
 return ch}

/* ---------- filter chips: OR inside a group, AND across groups; counts show what each chip would leave ---------- */
function chipHas(g,c,v){const x=g.get(c);return Array.isArray(x)?x.includes(v):x===v}
function chipMatch(groups,sel,c,skip){return groups.every(g=>g.id===skip||!(sel[g.id]||[]).length||sel[g.id].some(v=>chipHas(g,c,v)))}
function chipBar(groups,cards,sel,onchange){
 const bar=el("div",{class:"chips"}),btns=[];
 const live=groups.filter(g=>g.opts.filter(o=>cards.some(c=>chipHas(g,c,o.v))).length>=(g.min??2));
 live.forEach(g=>{const opts=g.opts.filter(o=>cards.some(c=>chipHas(g,c,o.v)));
  bar.append(el("div",{class:"cg",role:"group","aria-label":g.label},el("span",{class:"cgl","aria-hidden":"true"},g.label),...opts.map(o=>{
   const b=el("button",{type:"button",class:"chip",onclick:()=>{const a=sel[g.id]=sel[g.id]||[],i=a.indexOf(o.v);i<0?a.push(o.v):a.splice(i,1);onchange()}},o.dot?el("i",{style:`--c:${o.dot}`}):null,o.label,el("span",{class:"cn"}));
   btns.push([g,o,b]);return b})))});
 const clear=el("button",{type:"button",class:"chipclr",onclick:()=>{Object.keys(sel).forEach(k=>delete sel[k]);onchange()}},"Clear filters");bar.append(clear);
 bar.groups=live;
 bar.sync=(base)=>{btns.forEach(([g,o,b])=>{const on=(sel[g.id]||[]).includes(o.v);b.setAttribute("aria-pressed",on);
   const n=cards.filter(c=>base(c)&&chipMatch(live,sel,c,g.id)&&chipHas(g,c,o.v)).reduce((a,c)=>a+(c.qty||1),0);
   b.querySelector(".cn").textContent=n;b.disabled=!n&&!on});clear.hidden=!live.some(g=>(sel[g.id]||[]).length)};
 if(!live.length)bar.hidden=true;
 return bar}
function themeChips(){return D.theme?{id:"theme",label:"Theme",min:1,get:c=>c.theme,opts:[...D.theme.labels.map(l=>({v:l.label,label:l.label,dot:themeColor(l.label)})),{v:"off-theme",label:"Off-theme",dot:"var(--muted)"}]}:null}
function textHit(c,q){q=q.trim().toLowerCase();return !q||[c.name||c.card,c.type,c.label,...Object.keys(c.roles||{})].some(x=>x&&x.toLowerCase().includes(q))}

/* ---------- decklist: list or card grid, the same filters, groups and counts ---------- */
function deckList(d){const key="list",st=store.get(key,{group:"type",sort:"mv",q:"",f:{}});const sel=st.f&&typeof st.f==="object"?st.f:{};
 const total=d.cards.reduce((a,c)=>a+c.qty,0),gcs=new Set(((d.stats||{}).game_changers||[]).map(x=>x.toLowerCase()));
 const sec=section("sec-cards","Decklist",null,el("span",{class:"muted num"},plural(total,"card")));sec.classList.add("decklist");
 const grp=el("select",{"aria-label":"Group by"},...[["type","Group: card type"],["mv","Group: mana value"],["theme","Group: theme"],["role","Group: role (rules)"],["none","No groups"]].filter(([v])=>v!=="theme"||D.theme).map(([v,t])=>el("option",{value:v,selected:st.group===v},t)));
 const srt=el("select",{"aria-label":"Sort"},...[["mv","Sort: mana value"],["name","Sort: name"],["price","Sort: price (high first)"]].filter(([v])=>v!=="price"||SHOW.prices).map(([v,t])=>el("option",{value:v,selected:st.sort===v},t)));
 const isGC=c=>c.gc||gcs.has(c.name.toLowerCase());
 const MVS=["0","1","2","3","4","5","6+"];
 const presentTypes=[...TYPE_ORDER,"Other"].filter(t=>d.cards.some(c=>!c.commander&&typeInfo(c).types.includes(t)));
 const groups=[{id:"type",label:"Has type",min:1,get:c=>c.commander?[]:typeInfo(c).types,opts:presentTypes.map(t=>({v:t,label:t,dot:TYPE_COLOR[t]}))},  // an Artifact Creature counts under both
  {id:"mv",label:"Mana value",get:c=>c.commander||mainType(c)==="Land"?null:MVS[Math.min(c.mv||0,6)],opts:MVS.map(v=>({v,label:v}))},
  {id:"role",label:"Role (rules)",get:c=>Object.keys(c.roles||{}),opts:[...new Set(d.cards.flatMap(c=>Object.keys(c.roles||{})))].sort().map(r=>({v:r,label:cap(r)}))},
  {id:"status",label:"Status",min:1,get:c=>c.status,opts:Object.keys(ST_LABEL).map(k=>({v:k,label:ST_LABEL[k]}))},
  themeChips(),
  {id:"set",label:"Set",get:c=>c.set||null,opts:Object.entries(d.cards.reduce((a,c)=>(c.set&&(a[c.set]=(a[c.set]||0)+c.qty),a),{})).sort((a,b)=>b[1]-a[1]).map(([v])=>{const n=(d.cards.find(c=>c.set===v)||{}).set_name;return{v,label:n?`${n} (${v.toUpperCase()})`:v.toUpperCase()}})},
  {id:"tag",label:"Tags",min:1,get:c=>[isGC(c)&&"gc",swapsFor(c.name).length&&"swap",c.flags&&c.flags.length&&"flag",typeInfo(c).mdfc&&"mdfc"].filter(Boolean),
   opts:[{v:"gc",label:"Game Changers"},{v:"swap",label:"⇄ Proposed cuts"},{v:"flag",label:"! Flagged"},{v:"mdfc",label:"MDFC land"}]}].filter(Boolean);
 const q=el("input",{type:"search",placeholder:"Search cards",title:"Matches name, type or role",value:st.q,"aria-label":"Search the decklist"});
 const count=el("p",{class:"count",role:"status"});let shown=[];
 const copyShown=el("button",{type:"button",class:"gcopy",title:"Copy every card the search and filters show, one Moxfield line each",onclick:e=>copyText(shown.map(moxLine).join("\n"),e.currentTarget)},"Copy shown");
 const chips=chipBar(groups,d.cards,sel,draw);
 const canGrid=IMG!=="none"&&VIEW();
 let view=canGrid?(st.view||(MODE==="interactive"?"list":"cards")):"list",dens=st.density||(MODE==="interactive"||innerWidth<600?"dense":"comfy");
 const tgl=(label,opts,curv,set)=>{const g=el("div",{class:"viewtog",role:"group","aria-label":label},...opts.map(([v,t])=>el("button",{type:"button","aria-pressed":curv()===v,onclick:e=>{set(v);g.querySelectorAll("button").forEach(b=>b.setAttribute("aria-pressed",b===e.currentTarget));draw()}},t)));return g};
 const tog=canGrid?tgl("View",[["list","List"],["cards","Cards"]],()=>view,v=>view=v):null;
 const den=canGrid?tgl("Card size",[["dense","Dense"],["comfy","Comfortable"]],()=>dens,v=>dens=v):null;
 sec.append(el("div",{class:"ctrl"},q,tog,den,grp,srt,count,copyShown),chips);const out=el("div",{class:"cols"});sec.append(out);
 const marked=D.theme?D.theme.labels.filter(l=>!isDefaultTheme(l.label)):[];
 const TL=themeLine(d);
 sec.append(el("div",{class:"legend"},D.theme?el("span",{},...marked.map(l=>tag(l.label)),tag("off-theme")," marked"+(TL?". "+cap(TL):"")):null,
  el("span",{},el("span",{class:"tp mdfc"},"MDFC")," spell with a land back"),el("span",{},el("abbr",{class:"gc",title:"Game Changer"},"GC")," Game Changer"),
  d.recs_view.proposed.some(r=>r.cut)?el("span",{},el("span",{class:"swp"},"⇄")," a proposed change would cut it"):null,el("span",{},VIEW()?"Hover a name to preview, click to enlarge; the price links to a shop":"The name opens Scryfall; the price links to a shop")));
 [grp,srt,q].forEach(i=>i.addEventListener("input",draw));
 function draw(){const s={group:grp.value,sort:srt.value,q:q.value,f:sel,view,density:dens};store.set(key,s);if(den)den.hidden=view!=="cards";
  const base=c=>textHit(c,s.q);chips.sync(base);
  let cs=d.cards.filter(c=>base(c)&&chipMatch(chips.groups,sel,c));
  count.textContent=`Showing ${cs.reduce((a,c)=>a+c.qty,0)} of ${total}`;copyShown.hidden=!cs.length;
  cs.sort(s.sort==="name"?(a,b)=>a.name.localeCompare(b.name):s.sort==="price"?(a,b)=>(b.price??0)-(a.price??0):(a,b)=>(a.mv-b.mv)||a.name.localeCompare(b.name));
  const gk=c=>c.commander?"Commander":s.group==="type"?mainType(c):s.group==="mv"?(mainType(c)==="Land"?"Lands":"Mana value "+Math.min(c.mv,7)+(c.mv>=7?"+":"")):s.group==="theme"?(c.theme==="off-theme"?"Off-theme":c.theme||"No theme label"):s.group==="role"?(Object.keys(c.roles||{}).sort().map(cap).join(" + ")||"No role rule matched"):"All cards";
  const G={};cs.forEach(c=>(G[gk(c)]=G[gk(c)]||[]).push(c));
  const order=Object.keys(G).sort((a,b)=>(a==="Commander"?-1:b==="Commander"?1:0)||(s.group==="type"?GROUP_ORDER.indexOf(a)-GROUP_ORDER.indexOf(b):a.localeCompare(b,undefined,{numeric:true})));
  const flat=order.flatMap(g=>G[g]);shown=flat;  // the viewer browses the list in display order
  if(!cs.length){out.className="";out.replaceChildren(noMatch(()=>{q.value="";Object.keys(sel).forEach(k=>delete sel[k]);draw()}));return}
  const head=g=>{const n=G[g].reduce((a,c)=>a+c.qty,0),lab=g==="Land"&&s.group==="type"?landLabel(G[g].concat(cs.filter(c=>typeInfo(c).mdfc&&mainType(c)!=="Land"))).text:String(n);
   return el("h3",{},s.group==="type"&&TYPE_COLOR[g]?el("span",{class:"sw",style:`--c:${TYPE_COLOR[g]}`,"aria-hidden":"true"}):null,el("span",{},g),el("span",{class:"gn"},el("span",{class:"sr-only"},", "),lab,/^\d+$/.test(lab)?el("span",{class:"sr-only"},n===1?" card":" cards"):null),
    el("button",{type:"button",class:"gcopy","aria-label":`Copy ${g} (${n} shown) for Moxfield`,title:"Copy the cards shown in this section, one Moxfield line each",onclick:e=>copyText(G[g].map(moxLine).join("\n"),e.currentTarget)},"Copy"))};
  out.className=view==="cards"?"":"cols";
  if(view==="cards"){out.replaceChildren(...order.map(g=>el("div",{class:"grp vis"},head(g),el("div",{class:"cardgrid"+(dens==="comfy"?" comfy":"")},...G[g].map(c=>{const m=c.theme&&!isDefaultTheme(c.theme)?(c.theme==="off-theme"?"Off-theme":c.theme):null;
   return cardTile(c,flat,[isGC(c)?el("span",{class:"gcb"},"GC"):null,swapsFor(c.name).length?el("span",{},"⇄"):null].filter(Boolean),null,
    {caption:false,foot:[m?el("span",{},m):null,typeInfo(c).mdfc?el("span",{},"MDFC land"):null,ST_LABEL[c.status]?el("span",{},ST_LABEL[c.status]):null].filter(Boolean),
     extra:[isGC(c)?"Game Changer":null,m,c.tier||null,typeInfo(c).mdfc?"MDFC land":null,ST_LABEL[c.status],c.price!=null&&SHOW.prices?money(c.price):null].filter(Boolean).join(", ")})}))))); return}
  out.replaceChildren(...order.map(g=>el("div",{class:"grp"},head(g),...G[g].map(c=>el("div",{class:"ln"},
   el(VIEW()?"button":"a",{class:"name"+(c.theme==="off-theme"?" off":""),"data-img":c.img,title:"Roles from Oracle-text rules: "+roleText(c)+(c.label?`. Builder's label: ${c.label}`:""),...(VIEW()?{type:"button",onclick:e=>openViewer(c,flat,e.currentTarget)}:{href:cardLinks(c).scryfall,target:"_blank",rel:"noopener"})},c.qty>1?c.qty+"× ":"",c.name,isGC(c)?el("abbr",{class:"gc",title:"Game Changer"},"GC"):"",mark(c.theme),c.tier?el("span",{class:"tp tier",title:"Theme preference"},c.tier):null,
    typeInfo(c).mdfc?el("span",{class:"tp mdfc",title:"Modal double-faced card: the back is a land"},"MDFC"):"",
    swapsFor(c.name).length?el("span",{class:"swp",title:"A proposed change would cut this card"},"⇄"):"",
    c.flags&&c.flags.length?el("span",{class:"flag",title:c.flags.join(", ")},"!"):"",statusPill(c)),
   pips(c.mana),c.price!=null?ext(cardLinks(c).tcgplayer,`Buy ${c.name} on TCGplayer`,"num pr buy",money(c.price)):el("span",{class:"num muted pr",title:"No price from Scryfall for this printing"},"—"),
   (()=>{const a=ext(cardLinks(c).scryfall,`${c.name} on Scryfall`,"ext","↗");if(VIEW())a.tabIndex=-1;return a})())))))}  // the viewer has the same links, so ↗ stays out of the Tab path
 draw();return sec}

/* ---------- changes: applied recommendations as applied, open ones as proposals ---------- */
function changesSection(G,cur,deck){if(!SHOW.swaps)return null;const RV=deck.recs_view;
 const byName=Object.fromEntries(deck.cards.map(c=>[c.name.toLowerCase(),c]));
 const norm2=r=>{const src=byName[String(r.add||"").toLowerCase()]||{};
  return{card:r.add||"",swap_out:r.cut||"",why:r.reason||"",tradeoffs:r.tradeoffs,status_label:r.status_label,id:r.id,cites:r.cites,img:r.img||src.img,price:r.price??src.price,set:r.set||src.set,cn:r.cn||src.cn,type:src.type,
   theme:r.theme==="exception"?"Exception":r.theme==="off_theme"?"off-theme":null}};
 const applied=RV.applied.map(norm2),proposed=RV.proposed.map(norm2),rejected=(RV.rejected||[]).map(norm2);
 if(!applied.length&&!proposed.length&&!rejected.length)return null;
 const all=[...applied,...proposed,...rejected];
 const sec=section("sec-changes","Changes",[applied.length?`${plural(applied.length,"recommendation")} applied in this list`:null,proposed.length?`${proposed.length} still to decide`:null,rejected.length?`${rejected.length} rejected`:null].filter(Boolean).join("; ")+".");
 const row=(r,kind)=>{const open=e=>openViewer(r,all.filter(x=>x.img),e.currentTarget);
  return el("li",{class:"rec"},IMG!=="none"&&VIEW()&&r.img?el("button",{class:"thumb",type:"button",tabindex:-1,"aria-hidden":"true",onclick:open},art(r.img,"",r.card)):el("span"),el("div",{class:"rb"},
   el("div",{class:"rh"},kind==="applied"?statusTag("pass","Applied"):kind==="rejected"?statusTag("unverified","Rejected"):statusTag("info","Proposed"),
    r.card?(VIEW()&&r.img?el("button",{type:"button",class:"name","data-img":r.img,onclick:open},r.card):el("b",{},r.card)):el("b",{},"Cut only"),mark(r.theme),
    r.swap_out?el("span",{class:"muted"},(kind==="applied"?(r.card?"replaced ":"cut "):"would replace ")+r.swap_out):el("span",{class:"muted"},"added, nothing cut"),
    SHOW.prices&&r.price!=null&&r.card?ext(cardLinks(r).tcgplayer,`Buy ${r.card} on TCGplayer`,"num pr",money(r.price)):null),
   r.why?el("p",{},r.why):null,r.tradeoffs?el("p",{class:"muted"},"Trade-off: "+r.tradeoffs):null,citeRow(r.cites),
   el("p",{class:"note"},[r.id,kind!=="applied"&&r.status_label?"status: "+r.status_label.toLowerCase():null].filter(Boolean).join(", "))))};
 if(applied.length)sec.append(el("h3",{style:"margin-top:0"},"Applied"),el("ul",{class:"recs"},...applied.map(r=>row(r,"applied"))));
 if(proposed.length)sec.append(el("h3",{},"To decide"),el("ul",{class:"recs"},...proposed.map(r=>row(r,"proposed"))));
 if(rejected.length)sec.append(el("details",{class:"more",style:"margin-top:var(--sp-5)"},el("summary",{},el("h3",{},"Rejected"),el("span",{class:"cn"},rejected.length)),el("ul",{class:"recs"},...rejected.map(r=>row(r,"rejected")))));
 return sec}
const moxLine=c=>`${c.qty||1} ${c.name}${c.set&&c.cn?` (${c.set.toUpperCase()}) ${c.cn}${{foil:" *F*",etched:" *E*"}[c.finish]||""}`:""}`;  // one Moxfield import line with its finish; filtered-out cards never reach it
function copyText(t,btn){const done=()=>{const o=btn.textContent;btn.textContent="Copied";setTimeout(()=>btn.textContent=o,1500)};
 if(navigator.clipboard)navigator.clipboard.writeText(t).then(done,()=>fallback());else fallback();
 function fallback(){const a=el("textarea",{style:"position:fixed;opacity:0"});a.value=t;document.body.append(a);a.select();try{document.execCommand("copy");done()}catch(e){}a.remove()}}

/* ---------- sources: one numbering for markers and the list (sources_view, or derived from older data) ---------- */
let SRC=null;
function SRC_I(){if(SRC)return SRC;const groups=D.sources_view.map(g=>({kind:g.kind,label:g.kind_label,items:g.items})),byN={};
 groups.forEach(g=>g.items.forEach(x=>{byN[x.n]={...x,kind:g.kind,kind_label:g.label}}));
 return SRC={groups,byN,total:Object.keys(byN).length}}
function sourcesSection(){const S=SRC_I();if(!S.total&&!Object.keys(D.data_dates||{}).length)return null;
 const sec=section("sec-sources","Sources",S.total?`${plural(S.total,"source")}, numbered as in the research markers. Card facts and prices come from Scryfall's data.`:"Card facts and prices come from Scryfall's data.");
 const b=sourcesBlock();sec.append(el("div",{class:"srcwrap"},b||el("div"),el("div",{class:"acc"},...accuracyBlock())));return sec}
function sourcesBlock(){const S=SRC_I();if(!S.total)return null;const FI=findIndex();
 return el("div",{},...S.groups.map(g=>el("details",{class:"srcgroup more",id:"sg-"+slugify(g.kind)},el("summary",{},el("h3",{},g.label),el("span",{class:"cn"},plural(g.items.length,"source"))),
  el("ol",{class:"srclist"},...g.items.map(x=>el("li",{class:"src",id:srcAnchor(x),tabindex:-1},el("span",{class:"n"},x.n+"."),el("div",{},
   el("p",{},x.url?ext(x.url,`${x.title} (opens in a new tab)`,"",x.title):x.title),
   el("p",{class:"sm"},[x.creator,x.date?niceDate(x.date):null,x.sample_size?Number(x.sample_size).toLocaleString()+" decks":null,x.primary?"primary source":null,x.project&&D.multi?"project "+x.project:null].filter(Boolean).join(", ")||g.label),
   x.moments.length?el("p",{class:"moments"},el("span",{class:"lbl"},"Moments cited"),...x.moments.map(m=>ext(m.url,`${x.title} at ${m.t} (opens in a new tab)`,"ts",m.t))):null,
   x.cited_by.length?el("p",{class:"back"},el("span",{class:"lbl"},"↩ Cited in"),...x.cited_by.map((c,i)=>{const f=typeof c==="string"?FI[(x.project||"")+"|"+c]||{a:"f-"+c}:{a:c.anchor||fAnchor(c.project,c.id),h:c.headline};  // older data: finding ids
    return el("a",{href:"#"+f.a,"aria-label":`Back to finding ${i+1}${f.h?": "+f.h:""}`,title:f.h||null},String(i+1))})):null)))))))}
function accuracyBlock(){const dd=D.data_dates||{},U=D.accuracy.unverified||[],out=[];
 if(Object.keys(dd).length)out.push(el("h3",{},"Data freshness"),el("div",{class:"strip"},el("table",{style:"max-width:640px"},el("tbody",{},...Object.entries(dd).map(([k,v])=>el("tr",{},el("th",{scope:"row"},cap(k.replace(/_/g," "))),el("td",{class:"num"},v?(/^\d{4}-\d\d-\d\dT/.test(String(v))?niceDate(v):String(v)):"Not recorded")))))));
 if(U.length)out.push(el("details",{class:"more",style:"margin-top:var(--sp-5)"},el("summary",{},el("h3",{},"Still unverified"),el("span",{class:"cn"},U.length)),el("p",{class:"note"},"Gaps the research and card data could not close. They limit the conclusions above."),
  el("ul",{style:"max-width:var(--prose);display:grid;gap:var(--sp-2);padding-left:1.25em;margin:var(--sp-2) 0 var(--sp-4)"},...U.map(u=>el("li",{},u.text,u.where?el("span",{class:"muted"}," ("+u.where+")"):"")))));
 return out}
function renderSources(host){const S=SRC_I();
 const nn=noticesNode(null,undefined);if(nn)host.append(nn);
 const rb=researchBlock(null,t=>!hasHome(t.project));if(rb)host.append(el("section",{class:"panel",id:"sec-research"},el("div",{class:"sec-head"},el("h2",{},"Research"),rb.expand,el("p",{class:"lede"},rb.lede)),rb.node));
 const sec=el("section",{class:"panel"},el("div",{class:"sec-head"},el("h2",{},S.total?`Researched from ${plural(S.total,"source")}`:"Sources and accuracy"),el("p",{class:"lede"},"Findings on this page cite these sources. Card facts, prices and deck numbers come from Scryfall's data; opinions are labelled as opinions.")));
 const b=sourcesBlock();if(b)sec.append(b);host.append(sec);
 host.append(el("section",{class:"panel"},el("h2",{},"Data and accuracy"),...accuracyBlock()))}
/* ---------- research findings: headline, tag, short body, numbered markers, evidence in <details> ---------- */
const findingsView=()=>D.findings_view;
const disagreementsView=()=>D.disagreements_view;
// anchors: f-<project>-<finding id>, s-<project>-<source id> from the data (older data: f-<id>, src-<n>)
let FIND=null;
function findIndex(){if(FIND)return FIND;FIND={};D.findings_view.forEach(t=>t.items.forEach(i=>{const x={a:i.anchor||"f-"+i.id,h:i.headline,p:t.project||null};FIND[(x.p||"")+"|"+i.id]=x;FIND[x.a]=FIND[x.a]||x}));return FIND}
const fAnchor=(p,id)=>(findIndex()[(p||"")+"|"+id]||{a:"f-"+id}).a;
const srcAnchor=x=>x.anchor||"src-"+x.n;
// the tab showing an anchor: a finding's project research tab (else the deck page or the sources tab); sources: their list
function anchorTab(id){const has=t=>TABS.some(x=>x.id===t),deckTab=IN_DECK&&(TABS.find(t=>t.view==="decks")||{}).id;
 if(/^(s|src)-/.test(id))return has("sources")?"sources":deckTab||null;
 const f=/^f-/.test(id)&&findIndex()[id];if(!f)return null;
 const r=D.research.find(x=>(x.project||null)===f.p)||(!IN_DECK&&researchTabFor(f.p));return r?r.id:deckTab||(has("sources")?"sources":null)}
function citeA(c){const S=SRC_I(),t=c.title||c.label||"",label=`Source ${c.n??""}: ${t}`.trim();
 if(c.n!=null&&SHOW.sources)return el("a",{class:"cite",href:"#"+(c.anchor||(S.byN[c.n]?srcAnchor(S.byN[c.n]):"src-"+c.n)),"aria-label":label,"data-n":c.n},String(c.n));
 const u=c.url||(c.n!=null&&S.byN[c.n]?S.byN[c.n].url:null);
 return u?ext(u,`${t||"Source"} (opens in a new tab)`,"cite",c.n!=null?String(c.n):"↗"):el("span",{class:"cite"},c.n!=null?String(c.n):"?")}
function citeRow(cites){if(!cites||!cites.length)return null;
 return el("p",{class:"fsrc"},el("span",{class:"lbl"},cites.length>1?"Sources":"Source"),...cites.flatMap(c=>[citeA(c),...(c.at||[]).map(a=>ext(a.url,`${c.title||c.label}, at ${a.t}${a.note?" ("+a.note+")":""} (opens in a new tab)`,"ts",a.t))]))}
function cardsIn(names,deck){if(!names||!names.length)return null;const by=deck?Object.fromEntries(deck.cards.map(c=>[c.name.toLowerCase(),c])):{},list=deck?orderedCards(deck):[];
 return el("div",{class:"cardrow"},el("span",{class:"lbl"},"Cards"),...names.map(n=>{const c=by[String(n).toLowerCase()];return c?cardChip(c,list):el("span",{class:"cardchip"},n)}))}
const SHORT_BODY=200,OPEN_TOPICS=3;  // a body up to ~2 sentences shows under the headline; a longer one opens with the evidence
// the headline is the claim's first sentence (or its own short headline); the rest of the claim, reasoning and limits open with the evidence
function claimRest(h,b){h=String(h||"");b=String(b||"").trim();if(!b||b===h)return{rest:"",cut:false};const hh=h.replace(/…$/,"");
 if(hh&&b.startsWith(hh)){const r=b.slice(hh.length).replace(/^[\s:;,—–-]+/,"");return{rest:r,cut:h.endsWith("…")||/^[:;—–]/.test(b.slice(hh.length).trim())}}
 return{rest:b,cut:false}}
const firstSentence=s=>(/^[\s\S]*?[.!?](?=\s|$)/.exec(s)||[s])[0];
function findingNode(it,deck,sameClass){const S=SRC_I(),n=(it.cites||[]).length,{rest,cut}=claimRest(it.headline,it.body);
 const shown=rest&&!cut&&rest.length<=SHORT_BODY?rest:it.summary!==undefined?it.summary:rest?firstSentence(rest):null;  // summary: from the data when present
 const extra=[...(rest&&shown!==rest?[["Full claim",it.body]]:[]),...(it.explanation?[["Reasoning",it.explanation]]:[]),...(it.limitations?[["Limits",it.limitations]]:[])];
 const sum=[extra.length?"Details":null,n?plural(n,"source"):null,(it.cards||[]).length?plural(it.cards.length,"card"):null].filter(Boolean).join(", ");
 return el("li",{class:"finding",id:it.anchor||"f-"+it.id,tabindex:-1},
  el("div",{class:"ftags"},it.class_label&&!sameClass?el("span",{class:"ctag"},it.class_label):null,it.confidence?el("span",{class:"conf"},CONF_TXT[it.confidence]||it.confidence+" confidence"):null,it.disputed?statusTag("warning","Sources disagree"):null),
  el("h4",{},it.headline),shown?el("p",{class:"fbody"},shown):null,citeRow(it.cites),
  sum?el("details",{class:"ev"},el("summary",{},sum),
   ...extra.map(([k,v])=>el("p",{class:"fbody",style:"margin:0 0 var(--sp-3)"},el("b",{},k+". "),v)),
   n?el("ol",{class:"evlist"},...it.cites.map(c=>{const x=c.n!=null?S.byN[c.n]:null,t=c.title||(x&&x.title)||c.label||"",u=(x&&x.url)||c.url;return el("li",{},citeA(c),el("div",{},
    el("div",{},u?ext(u,`${t} (opens in a new tab)`,"",t):t),
    el("div",{class:"sm"},[x&&x.kind_label,(x&&x.creator)||(c.label!==t?c.label:null),x&&x.date?niceDate(x.date):null].filter(Boolean).join(", ")),
    (c.at||[]).length?el("div",{class:"sm"},"At ",...c.at.flatMap((a,i)=>[i?", ":"",ext(a.url,`${t}, at ${a.t} (opens in a new tab)`,"ts",a.t),a.note?" ("+a.note+")":""])):null))})):null,
   cardsIn(it.cards,deck)):null)}
function disNode(d){const FI=findIndex();return el("div",{class:"dis"},el("div",{class:"ftags"},statusTag("warning","Sources disagree")),el("h4",{},d.topic),
 el("ul",{},...(d.positions||[]).map(p=>el("li",{},el("p",{},p.text),citeRow(p.cites),(p.findings||[]).length?el("p",{class:"fsrc"},el("span",{class:"lbl"},"Findings"),...p.findings.map((id,i)=>{const f=FI[(d.project||"")+"|"+id]||{a:"f-"+id};return el("a",{href:"#"+f.a,title:f.h||null,"aria-label":`Finding ${i+1}${f.h?": "+f.h:""}`},"↓ "+(i+1))})):null))),
 d.explanation?el("p",{class:"note",style:"margin-top:var(--sp-3)"},d.explanation):null)}
function researchBlock(deck,keep,T){keep=keep||(()=>true);const FV=findingsView().filter(t=>(t.items||[]).length&&keep(t)),DV=disagreementsView().filter(keep);
 const X=researchExtras(T,deck);if(!FV.length&&!DV.length&&!X.length)return null;
 const total=FV.reduce((a,t)=>a+t.items.length,0),S=SRC_I();let box;
 const xall=el("button",{type:"button",class:"btn ghost xall","aria-expanded":"false",onclick:()=>{const open=xall.getAttribute("aria-expanded")!=="true";box.querySelectorAll("details").forEach(x=>x.open=open);xall.setAttribute("aria-expanded",String(open));xall.textContent=open?"Collapse all":"Expand all"}},"Expand all");
 const tid=t=>"t-"+slugify(t.id);
 const items=[...(DV.length?[["t-disagree","Where sources disagree",DV.length]]:[]),...FV.map(t=>[tid(t),t.title,t.items.length]),...X.map(x=>[x.id,x.title,x.n])];
 const toc=items.length>2?el("nav",{class:"ftoc","aria-label":"Research topics"},el("ul",{},...items.map(([id,t,n])=>el("li",{},el("a",{href:"#"+id},t,n!=null?el("span",{class:"cn"},n):null))))):null;
 const col=el("div",{class:"fcol"});
 if(DV.length)col.append(el("section",{class:"ftopic",id:"t-disagree","aria-labelledby":"h-t-disagree"},el("h3",{id:"h-t-disagree"},"Where sources disagree",el("span",{class:"cn"},DV.length)),...DV.map(disNode)));
 // topics come ordered by importance: the first ones open, the rest grouped behind their title and count (find-in-page and links open them)
 FV.forEach((t,i)=>{const cl=t.items[0].class_label,same=!!cl&&t.items.every(x=>x.class_label===cl),n=t.items.length;
  const what=same&&norm(cl)!==norm(t.title)?plural(n,cl.toLowerCase()):plural(n,"finding");
  col.append(el("details",{class:"ftopic more",id:tid(t),open:i<OPEN_TOPICS},el("summary",{},el("h3",{},t.title),el("span",{class:"cn"},what)),el("ol",{class:"flist"},...t.items.map(x=>findingNode(x,deck,same)))))});
 X.forEach(x=>col.append(x.node));
 box=el("div",{class:"fwrap"},toc,col);
 const parts=[total?plural(total,"finding"):null,DV.length?`${DV.length} open disagreement${DV.length===1?"":"s"}`:null].filter(Boolean).join(", ");
 return{node:box,expand:total||X.length?xall:null,lede:parts?`${parts}${S.total?`, from ${plural(S.total,"source")}`:""}. Each headline is the conclusion; numbers link to the source list and times open the video at that moment.`:"Recommendations and candidates from the research file."}}
// research_tab extras: recommendations, card candidates, alternatives, next steps, open questions (gaps show under "Still unverified")
const FIT={on_theme:"On theme",exception:"Exception",off_theme:"Off-theme"};
function researchExtras(T,deck){if(!T)return[];const out=[],add=(id,title,n,...kids)=>out.push({id,title,n,node:el("details",{class:"ftopic more",id},el("summary",{},el("h3",{},title),n!=null?el("span",{class:"cn"},n):null),...kids)});
 const recs=T.recommendations||[];if(recs.length)add("t-recs","Research recommendations",recs.length,el("ol",{class:"flist"},...recs.map(r=>el("li",{class:"finding"},el("h4",{},r.text||""),r.why?el("p",{class:"fbody"},r.why):null,citeRow(r.cites)))));
 const C=T.candidates||[];if(C.length){const view=C.map(c=>({...c,why:[c.relevance,c.synergy?"Synergy: "+c.synergy:null].filter(Boolean).join(" "),evidence:(c.cites||[]).map(x=>({title:x.title||x.label,url:x.url}))}));
  const row=c=>el("li",{class:"rec"},IMG!=="none"&&VIEW()&&c.img?el("button",{class:"thumb",type:"button",tabindex:-1,"aria-hidden":"true",onclick:e=>openViewer(c,view.filter(x=>x.img),e.currentTarget)},art(c.img,"",c.name)):el("span"),el("div",{class:"rb"},
   el("div",{class:"rh"},VIEW()&&c.img?el("button",{type:"button",class:"name","data-img":c.img,onclick:e=>openViewer(c,view.filter(x=>x.img),e.currentTarget)},c.name):el("b",{},c.name),c.in_deck?statusTag("pass","In the deck"):null,
    c.theme_fit&&FIT[c.theme_fit]&&c.theme_fit!=="on_theme"?el("span",{class:"ctag"},FIT[c.theme_fit]):null,c.role?el("span",{class:"muted"},c.role):null),
   c.relevance?el("p",{},c.relevance):null,c.synergy?el("p",{class:"muted"},"Synergy: "+c.synergy):null,citeRow(c.cites)));
  const inD=view.filter(c=>c.in_deck),outD=view.filter(c=>!c.in_deck);
  add("t-cands","Card candidates",C.length,outD.length?el("h4",{style:"margin:var(--sp-2) 0"},`Not in the deck (${outD.length})`):null,outD.length?el("ul",{class:"recs"},...outD.map(row)):null,
   inD.length?el("h4",{style:"margin:var(--sp-4) 0 var(--sp-2)"},`Already in the deck (${inD.length})`):null,inD.length?el("ul",{class:"recs"},...inD.map(row)):null)}
 const A=T.alternatives||[];if(A.length)add("t-alts","Alternatives considered",A.length,el("ul",{class:"flist"},...A.map(a=>el("li",{class:"finding"},el("h4",{},a.option||a.text||""),a.why?el("p",{class:"fbody"},a.why):null,citeRow(a.cites)))));
 const N=T.next_steps||[];if(N.length)add("t-next","Next steps",N.length,el("ul",{style:"display:grid;gap:var(--sp-2);padding-left:1.25em;max-width:var(--prose)"},...N.map(x=>el("li",{},typeof x==="string"?x:x.text||""))));
 const Q=T.follow_up_questions||[];if(Q.length)add("t-questions","Open questions",Q.length,el("ul",{class:"flist"},...Q.map(q=>el("li",{class:"finding"},el("h4",{},q.question),q.why?el("p",{class:"fbody"},q.why):null,
  (q.options||[]).length?el("ul",{style:"margin:var(--sp-2) 0 0;padding-left:1.25em"},...q.options.map(o=>el("li",{},o,o===q.recommended?el("span",{class:"muted"}," (recommended)"):null))):null))));
 return out}
function researchSection(deck){const rb=researchBlock(deck,null,researchTabFor(deck.project));if(!rb)return null;
 const sec=section("sec-research","Research",rb.lede,rb.expand);sec.append(rb.node);return sec}
/* ---------- audit: verdict, counts, fails and warnings open, passes collapsed, shared method once ---------- */
function auditSection(deck){const AV=deck.audit_view,sec=section("sec-audit","Audit",null);
 const meta=[AV.audited?"Audited "+niceDate(AV.audited):null,AV.independent?"by an independent auditor":null].filter(Boolean).join(" ");
 if(!AV.groups.length){const st=AV.verdict,note=AV.note;
  sec.append(el("div",{class:"empty"},el("p",{},stateTag(st)),
   st==="not audited"?[el("p",{},el("b",{},"This build has not been audited.")),el("p",{},"No audit file exists for it, so legality, bracket and theme are unchecked. Run the audit skill on this build, then rebuild the page.")]:
   st==="audit out of date"?[el("p",{},el("b",{},"The audit results are hidden because they describe another list.")),note?el("p",{},cap(note)+"."):null,el("p",{},"Re-run the audit on this version, then rebuild the page.")]:
   [el("p",{},note||"No check details were recorded with this audit."),meta?el("p",{class:"note"},meta):null]));return sec}
 const c=AV.counts||{},byN=Object.fromEntries(deck.cards.map(x=>[x.name.toLowerCase(),x])),list=orderedCards(deck);
 const chip=n=>byN[String(n).toLowerCase()]?cardChip(byN[String(n).toLowerCase()],list):el("span",{class:"cardchip"},n);
 sec.append(el("div",{class:"vrow"},el("div",{class:"row"},stateTag(AV.verdict),meta?el("span",{class:"note"},meta):null),AV.summary&&AV.summary.lead?el("p",{class:"lead"},AV.summary.lead):null,
  AV.summary&&AV.summary.more?el("details",{class:"more"},el("summary",{},"Full verdict"),el("p",{},AV.summary.more)):null));
 sec.append(el("ul",{class:"counts","aria-label":"Checks by result"},...[["fail","Failed"],["warning","Warnings"],["unverified","Unverified"],["pass","Passed"]].map(([k,l])=>el("li",{},statusIcon(k),el("b",{},c[k]||0),el("span",{},l)))));
 if((AV.required_fixes||[]).length)sec.append(el("div",{class:"fixes"},el("h3",{},statusIcon("fail")," Required fixes"),el("ul",{},...AV.required_fixes.map(x=>el("li",{},typeof x==="string"?x:[x.title?el("b",{},x.title+": "):null,x.fix||x.text||""])))));
 (AV.groups||[]).forEach(g=>sec.append(el("details",{class:"agroup",open:!!g.open},el("summary",{},statusIcon(g.status),el("h3",{},g.label)),
  el("ol",{class:"checks"},...g.checks.map(x=>el("li",{class:"check",id:x.id?"chk-"+slugify(x.id):null},el("div",{class:"ch"},el("h4",{},x.title),statusTag(x.status,x.status_label||ST_TXT[x.status]),x.kind?el("span",{class:"note"},KIND_TXT[x.kind]||x.kind):null),
   x.result?el("p",{},x.result):null,x.method?el("details",{},el("summary",{},"How it was checked"),el("p",{class:"note"},x.method)):null,
   (x.cards||[]).length?el("div",{class:"cardrow"},...x.cards.map(chip)):null))))));
 if((AV.limitations||[]).length)sec.append(el("div",{class:"fixes"},el("h3",{},"Limits of this audit"),el("ul",{},...AV.limitations.map(x=>el("li",{},x)))));
 if((AV.next_steps||[]).length)sec.append(el("div",{class:"fixes"},el("h3",{},"Next steps"),el("ul",{},...AV.next_steps.map(x=>el("li",{},typeof x==="string"?x:x.text||"")))));
 if(AV.method_common)sec.append(el("p",{class:"method"},el("b",{},"How the checks were run. "),"Unless a check says otherwise: ",AV.method_common.replace(/\.?$/,".")));
 if(AV.groups.some(g=>g.checks.some(x=>x.kind)))sec.append(el("p",{class:"note"},"Script check = a deterministic script result. Checked against a source = compared with a cited source. Auditor's judgment = an opinion, not proof."));
 return sec}
/* ---------- citation preview: hover or focus a marker (200 ms), Esc closes; the link label carries the same text ---------- */
let pop=null,popT=0,popA=null;
function hidePop(){clearTimeout(popT);popA=null;if(pop)pop.hidden=true}
function initPop(){pop=el("div",{class:"srcpop","aria-hidden":"true",hidden:true});document.body.append(pop);
 const show=a=>{const x=SRC_I().byN[a.dataset.n];if(!x)return;pop.replaceChildren(el("b",{},`${x.n}. ${x.title}`),el("span",{class:"muted"},[x.kind_label,x.creator,x.date?niceDate(x.date):null].filter(Boolean).join(", ")));
  popA=a;place()};
 const place=()=>{const r=popA.getBoundingClientRect();pop.hidden=r.bottom<0||r.top>innerHeight;if(pop.hidden)return;const w=pop.offsetWidth,h=pop.offsetHeight;
  pop.style.left=Math.max(8,Math.min(r.left,innerWidth-w-8))+"px";pop.style.top=(r.bottom+8+h>innerHeight?r.top-h-8:r.bottom+8)+"px"};
 const on=e=>{const a=e.target.closest&&e.target.closest("a.cite[data-n]");if(!a)return;clearTimeout(popT);popT=setTimeout(()=>show(a),200)};
 const off=e=>{if(e.target.closest&&e.target.closest("a.cite[data-n]"))hidePop()};
 document.addEventListener("pointerover",on);document.addEventListener("focusin",on);document.addEventListener("pointerout",off);document.addEventListener("focusout",off);
 addEventListener("keydown",e=>{if(e.key==="Escape")hidePop()});addEventListener("scroll",()=>{if(popA)place()},{passive:true})}  // the preview follows its marker while the page scrolls

/* ---------- viewer: CSS 3D, drag to rotate, flip, sheen ---------- */
let V={list:[],i:0,opener:null,ry:0,rx:0,hx:0,hy:0,flipped:false};
const VIEW=()=>SHOW.viewer&&IMG!=="none";
function openViewer(c,list,opener){if(!VIEW())return;hideTip();hidePop();V.list=list&&list.length?list:[c];V.i=Math.max(0,V.list.indexOf(c));V.opener=opener;showCard();const dlg=$("#viewer");if(!dlg.open)dlg.showModal();$("#vFlip").focus()}
function cardOf(x){return x.card?{...x,name:x.card}:x}
function showCard(){const c=cardOf(V.list[V.i]);V.flipped=false;V.rx=V.ry=V.hx=V.hy=0;apply();
 $("#vFront").setAttribute("style",artStyle(c.img));$("#vFront").setAttribute("aria-label",c.name);$("#viewer").setAttribute("aria-label",`${c.name}, card ${V.i+1} of ${V.list.length}`);
 $("#vBack").setAttribute("style",artStyle(c.back||D.default_back));
 if(V3.on)V3.show(c.img,c.back||D.default_back);
 const side=$("#vSide");side.replaceChildren(el("h3",{},c.name),c.artist?el("p",{class:"note"},"Illustrated by "+c.artist):null,c.owned?el("p",{class:"note"},{owned:"In your collection",other_printing:"In your collection (another printing)",missing:"Not in your collection"}[c.owned]):null,linkRow(c),el("p",{},el("button",{type:"button",class:"gcopy",title:moxLine(c),onclick:e=>copyText(moxLine(c),e.currentTarget)},"Copy for Moxfield")),el("p",{},pill(c.theme)," ",statusPill(c)," ",c.rank?el("b",{},`Rank ${c.rank}${c.tier?", tier "+c.tier:""} `):"",c.pct!=null?el("span",{class:"num"},"Popularity: "+popText(c)):""));
 if(c.type)side.append(el("p",{class:"muted"},c.type+(c.mdfc_land?" (modal double-faced: the back is a land)":"")));
 if(c.why)side.append(el("p",{},c.why));
 if(c.tradeoffs)side.append(el("p",{class:"muted"},"Trade-off: "+c.tradeoffs));
 if(c.evidence&&c.evidence.length)side.append(el("p",{},"Evidence: ",...c.evidence.flatMap((x,i)=>[i?", ":"",ext(x.url,`${x.title} (opens in a new tab)`,"",x.title)])));
 if(c.strategy)side.append(el("p",{},c.strategy));
 if(c.roles){const e=Object.entries(c.roles);side.append(el("h3",{},"Roles (from Oracle-text rules)"),e.length?el("ul",{},...e.map(([r,why])=>el("li",{},el("b",{},r),": "+why.join(", ")))):el("p",{class:"muted"},"No role rule matched."));
  if(c.label&&!(c.label in c.roles))side.append(el("p",{class:"muted"},`Builder's label: ${c.label}`))}
 if(SHOW.prices&&c.cheapest){const p=c.cheapest;side.append(el("h3",{},"Printings and prices"),el("table",{},el("tbody",{},
   el("tr",{},el("td",{},"Cheapest"),el("td",{},`${(p.set||"").toUpperCase()} #${p.collector_number||""}`),el("td",{class:"n num"},money(p.usd))),
   el("tr",{},el("td",{},"Priciest"),el("td",{},`${(p.max_set||"").toUpperCase()} #${p.max_collector_number||""}`),el("td",{class:"n num"},money(p.max_usd))),
   c.price!=null?el("tr",{},el("td",{},"This list"),el("td",{},`${c.set_name?c.set_name+", ":""}${(c.set||"").toUpperCase()} #${c.cn||""}`),el("td",{class:"n num"},money(c.price))):null)),
  el("p",{class:"muted"},"Scryfall daily prices"+(D.data_dates&&D.data_dates["card data and prices (Scryfall)"]?", as of "+D.data_dates["card data and prices (Scryfall)"]:"")+"."))}
 if(!c.card){const sw=swapsFor(c.name);if(sw.length)side.append(el("div",{class:"alt"},el("h4",{},"Proposed changes"),...sw.map(x=>el("p",{},x.add?[el("b",{},x.add)," would replace it"]:"Cut it",x.reason?". "+x.reason:"",x.id?el("span",{class:"muted"}," ("+x.id+")"):""))))}
 if(c.reason)side.append(el("p",{},el("b",{},"Off-theme because: "),c.reason));
 side.append(el("p",{class:"muted"},`${V.i+1} of ${V.list.length}. Arrow keys browse, F or a click flips, drag to spin (it snaps back), Esc closes.`))}
function apply(){if(V3.on){V3.kick();return}$("#card3d").style.transform=`rotateX(${V.rx+V.hx}deg) rotateY(${V.ry+V.hy+(V.flipped?180:0)}deg)`}
function flip(){V.flipped=!V.flipped;apply()}
function step(n){V.i=(V.i+n+V.list.length)%V.list.length;showCard()}
function closeViewer(){$("#viewer").close()}
function initViewer(){const dlg=$("#viewer"),stage=$("#stage"),card=$("#card3d");
 $("#vFlip").onclick=flip;$("#vPrev").onclick=()=>step(-1);$("#vNext").onclick=()=>step(1);$("#vClose").onclick=closeViewer;
 dlg.addEventListener("close",()=>{if(V.opener)setTimeout(()=>V.opener.focus(),0)});
 dlg.addEventListener("click",e=>{if(e.target===dlg||e.target.classList.contains("vw"))closeViewer()});
 dlg.addEventListener("keydown",e=>{if(e.key==="ArrowRight")step(1);else if(e.key==="ArrowLeft")step(-1);else if(e.key.toLowerCase()==="f"&&!e.ctrlKey&&!e.metaKey)flip();
  else if(e.key==="Tab"){const f=[...dlg.querySelectorAll("button,a[href]")].filter(x=>x.offsetParent!==null);if(!f.length)return;const i=f.indexOf(document.activeElement);  // keep Tab inside the viewer
   if(e.shiftKey&&i<=0){e.preventDefault();f[f.length-1].focus()}else if(!e.shiftKey&&i===f.length-1){e.preventDefault();f[0].focus()}}});
 const reduced=reducedMotion();let drag=null,moved=false;
 stage.addEventListener("pointerdown",e=>{if(e.button)return;V.hx=V.hy=0;drag={x:e.clientX,y:e.clientY,rx:V.rx,ry:V.ry};moved=false;card.classList.add("dragging");stage.classList.add("grabbing");stage.setPointerCapture(e.pointerId)});
 stage.addEventListener("pointerleave",()=>{if(drag)return;V.hx=V.hy=0;apply()});
 stage.addEventListener("pointermove",e=>{const r=stage.getBoundingClientRect();stage.querySelectorAll(".sheen").forEach(s=>{s.style.setProperty("--mx",(e.clientX-r.left)/r.width*100+"%");s.style.setProperty("--my",(e.clientY-r.top)/r.height*100+"%")});
  if(V3.on)V3.pointer((e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height);
  if(!drag){if(!reduced&&MODE==="showcase"&&e.pointerType==="mouse"){V.hy=((e.clientX-r.left)/r.width-.5)*16;V.hx=(.5-(e.clientY-r.top)/r.height)*12;apply()}return}  // hover: the card leans toward the pointer
  const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>4)moved=true;if(reduced)return;
  if(V3.on){V.ry=drag.ry+dx/2;V.rx=Math.max(-60,Math.min(60,drag.rx-dy/3));apply();return}  // 3D: spin freely
  V.ry=Math.max(-35,Math.min(35,drag.ry+dx/4));V.rx=Math.max(-25,Math.min(25,drag.rx-dy/4));apply()});
 const end=e=>{if(!drag)return;const dx=e.clientX-drag.x;card.classList.remove("dragging");
  stage.classList.remove("grabbing");
  if(!moved)flip();
  else if(!V3.on&&Math.abs(dx)>120&&e.pointerType==="touch")step(dx<0?1:-1);
  else{const t=Math.round((V.ry+(V.flipped?180:0))/180)*180;V.flipped=Math.abs(t/180)%2===1;V.ry=t-(V.flipped?180:0);V.rx=0;apply()}  // snap back to whichever face is nearest
  drag=null};
 stage.addEventListener("pointerup",end);stage.addEventListener("pointercancel",end)}

/* ---------- optional 3D viewer (three.js), only when the page data asks for it ---------- */
let threeP=null;const loadThree=()=>window.THREE?Promise.resolve():(threeP=threeP||loadScript(THREE_URL));
const THREE_URL="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js";
const V3={on:false,want:null,img:{},tex:{},
 async init(){
  if(D.viewer!=="three"||!VIEW())return;
  try{
   await loadThree();
   const T=window.THREE,cv=document.createElement("canvas");
   this.r=new T.WebGLRenderer({canvas:cv,alpha:true,antialias:true});  // throws without WebGL: we keep the simple viewer
   this.r.outputEncoding=T.sRGBEncoding;this.r.setPixelRatio(Math.min(devicePixelRatio,2));
   this.s=new T.Scene();this.cam=new T.PerspectiveCamera(32,488/680,.1,100);this.cam.position.z=7;
   this.s.add(new T.AmbientLight(0xffffff,.8));this.light=new T.PointLight(0xffffff,.7);this.light.position.set(0,0,4);this.s.add(this.light);
   const geo=new T.PlaneGeometry(2.44,3.4),mat=()=>new T.MeshStandardMaterial({transparent:true,roughness:.45,metalness:.15});
   this.front=new T.Mesh(geo,mat());this.back=new T.Mesh(geo,mat());this.back.rotation.y=Math.PI;
   this.g=new T.Group();this.g.add(this.front,this.back);this.s.add(this.g);
   $("#stage").prepend(cv);$("#stage").classList.add("v3");this.cv=cv;this.on=true;
   this.reduced=reducedMotion();
  }catch(e){console.warn("3D viewer unavailable, using the simple viewer");this.on=false}},
 loadImg(src){return this.img[src]||(this.img[src]=new Promise((ok,no)=>{const i=new Image();if(IMG==="cdn")i.crossOrigin="anonymous";i.onload=()=>ok(i);i.onerror=no;i.src=src}))},
 async texture(key){
  if(this.tex[key])return this.tex[key];let im,x=0,y=0,w=488,h=680,sw=null,sh=null;
  if(IMG==="cdn"){const u=(D.image_urls||{})[key];if(!u)return null;im=await this.loadImg(u);sw=im.naturalWidth;sh=im.naturalHeight}  // Scryfall allows any origin
  else{const a=ATL&&ATL.cards[key];if(!a)return null;[w,h]=ATL.cell;x=a[1];y=a[2];im=await this.loadImg(ATL.base+ATL.atlases[a[0]])}
  const c=document.createElement("canvas");c.width=w;c.height=h;const g=c.getContext("2d"),rad=w*.0475;
  g.beginPath();g.moveTo(rad,0);g.arcTo(w,0,w,h,rad);g.arcTo(w,h,0,h,rad);g.arcTo(0,h,0,0,rad);g.arcTo(0,0,w,0,rad);g.closePath();g.clip();
  g.drawImage(im,x,y,sw||w,sh||h,0,0,w,h);
  try{g.getImageData(0,0,1,1)}catch(e){this.off("3D viewer needs the page served over http(s) (opened from disk, the browser blocks card textures); using the simple viewer");return null}
  const t=new THREE.CanvasTexture(c);t.encoding=THREE.sRGBEncoding;return this.tex[key]=t},
 off(why){if(!this.on)return;this.on=false;this.cv.remove();$("#stage").classList.remove("v3");console.warn(why);apply()},
 async show(fk,bk){
  this.want=fk;let f,b;try{[f,b]=await Promise.all([this.texture(fk),this.texture(bk)])}catch(e){this.off("3D viewer couldn't load card images; using the simple viewer");return}
  if(this.want!==fk||!this.on)return;
  this.front.material.map=f;this.back.material.map=b;this.front.material.needsUpdate=this.back.material.needsUpdate=true;
  this.g.rotation.set(V.rx*Math.PI/180,(V.ry+(V.flipped?180:0))*Math.PI/180,0);  // a new card appears face-on, no spin
  this.size();this.r.render(this.s,this.cam);this.kick()},
 size(){const w=this.cv.clientWidth||420;this.r.setSize(w,w*680/488,false)},
 pointer(px,py){this.light.position.set((px-.5)*6,(.5-py)*6,4);this.kick()},
 kick(){if(!this.loop){this.loop=true;requestAnimationFrame(()=>this.frame())}},
 frame(){const ty=(V.ry+V.hy+(V.flipped?180:0))*Math.PI/180,tx=(V.rx+V.hx)*Math.PI/180,k=this.reduced?1:.18;
  this.g.rotation.y+=(ty-this.g.rotation.y)*k;this.g.rotation.x+=(tx-this.g.rotation.x)*k;this.r.render(this.s,this.cam);
  const busy=Math.abs(ty-this.g.rotation.y)+Math.abs(tx-this.g.rotation.x)>.001;
  if(busy&&$("#viewer").open)requestAnimationFrame(()=>this.frame());else this.loop=false}};

/* ---------- hover preview (desktop) ---------- */
let hideTip=()=>{};
function initTip(){const tip=el("div",{class:"tip art",hidden:true});document.body.append(tip);hideTip=()=>{tip.hidden=true};
 ["click","keydown"].forEach(t=>addEventListener(t,hideTip,{capture:true,passive:true}));
 document.addEventListener("pointerover",e=>{const t=e.target.closest&&e.target.closest("[data-img]");if(!t||IMG==="none"||e.pointerType==="touch"||t.classList.contains("hero-card")){tip.hidden=true;return}
  tip.setAttribute("style",artStyle(t.dataset.img));tip.hidden=false});
 document.addEventListener("pointermove",e=>{if(tip.hidden)return;const x=e.clientX+20+244<innerWidth?e.clientX+20:e.clientX-264,y=Math.max(8,Math.min(e.clientY-60,innerHeight-352));tip.style.left=x+"px";tip.style.top=y+"px"},{passive:true});
 document.addEventListener("pointerout",e=>{if(e.target.closest&&e.target.closest("[data-img]"))tip.hidden=true})}

/* ---------- masthead: page title, 3D card fan (three.js) or CSS fan ---------- */
async function mastFan(keys){const box=$("#fanbox"),cv=$("#mastfx");if(!keys.length||IMG==="none"){box.remove();return}
 const fan=$("#fan");keys.forEach((k,i)=>{const a=art(k,"");const m=(keys.length-1)/2;a.style.setProperty("--r",(i-m)*6+"deg");a.style.setProperty("--y",Math.abs(i-m)*6+"px");fan.append(a)});
 if(!(SHOW.viewer&&D.viewer==="three")||reducedMotion())return;  // CSS fan stays
 try{await loadThree()}catch(e){return}
 const T=window.THREE;let r;try{r=new T.WebGLRenderer({canvas:cv,alpha:true,antialias:true,powerPreference:"low-power"})}catch(e){return}
 r.outputEncoding=T.sRGBEncoding;r.setPixelRatio(Math.min(devicePixelRatio,1.75));
 const scene=new T.Scene(),cam=new T.PerspectiveCamera(30,1,.1,100),geo=new T.PlaneGeometry(2.44,3.4);
 scene.add(new T.AmbientLight(0xffffff,1));
 const cards=[];for(const k of keys){let tx;try{tx=await V3.texture(k)}catch(e){tx=null}if(!tx){r.dispose();return}  // e.g. opened from disk: keep the CSS fan
  const m=new T.Mesh(geo,new T.MeshBasicMaterial({map:tx,transparent:true}));scene.add(m);cards.push(m)}
 box.classList.add("on3d");let px=0,py=0,raf=0;
 const layout=()=>{const w=cv.clientWidth,h=cv.clientHeight;if(!w||!h)return;r.setSize(w,h,false);cam.aspect=w/h;const n=cards.length,gap=1.45;
  cards.forEach((m,i)=>{const a=i-(n-1)/2;m.userData={a,x:a*gap,y:-Math.abs(a)*.14,z:-Math.abs(a)*.3,ry:-a*.13,rz:-a*.055}});
  const fanW=(n-1)*gap+3.1,fanH=4,tan=Math.tan(T.MathUtils.degToRad(15));cam.position.z=Math.max(fanH/(2*tan),fanW/(2*tan*cam.aspect))+.4;cam.updateProjectionMatrix()};
 const draw=()=>{cards.forEach((m,i)=>{const u=m.userData;m.position.set(u.x,u.y,u.z);m.rotation.set(py*.08,u.ry+px*.16,u.rz)});
  cam.position.x+=(px*.25-cam.position.x)*.06;cam.lookAt(0,0,0);r.render(scene,cam)};
 const tick=()=>{raf=0;draw();if(Math.abs(px*.25-cam.position.x)>.002)raf=requestAnimationFrame(tick)};  // moves only with the pointer: nothing loops on its own
 addEventListener("pointermove",e=>{px=e.clientX/innerWidth-.5;py=e.clientY/innerHeight-.5;if(!raf)raf=requestAnimationFrame(tick)},{passive:true});
 new ResizeObserver(()=>{layout();draw()}).observe(cv);
 layout()}
function niceDate(v){if(!/^\d{4}-\d\d(-\d\d)?/.test(String(v)))return String(v);const d=new Date(String(v).length===10?v+"T12:00:00":v);return isNaN(d)?String(v):d.toLocaleDateString(undefined,{year:"numeric",month:"short",day:"numeric"})}
// open every closed disclosure around (and at) a link target so the jump lands on something visible
function openTo(t){if(t.tagName==="DETAILS")t.open=true;for(let d=t.closest("details:not([open])");d;d=d.closest("details:not([open])"))d.open=true}
/* ---------- boot ---------- */
function setThemeLabel(){const b=$("#themeBtn"),cur=document.documentElement.dataset.theme||(matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light");b.setAttribute("aria-label",cur==="dark"?"Switch to light theme":"Switch to dark theme")}
async function boot(){D=window.SITE_DATA;if(!D){try{D=await (await fetch("site-data.json")).json()}catch(e){$("#main").replaceChildren(el("div",{class:"panel"},el("div",{class:"empty"},el("p",{},el("b",{},"Could not load site-data.json.")),el("p",{},"This page keeps its data in a separate file. Serve the folder over http(s) or rebuild without --separate-data."))));return}}
 ATL=D.atlas?{...D.atlas,base:D.atlas.base??"img/"}:null;
 const P=D.page||{};  // basic / fancy / custom: which sections exist and where images come from
 SHOW=Object.assign({charts:true,swaps:true,sources:true,fan:true,prices:true,viewer:true},P.show||{});
 IMG=P.images||(ATL?"atlas":D.image_urls?"cdn":"none");
 MODE=P.mode==="interactive"?"interactive":"showcase";
 IN_DECK=!D.multi&&D.groups.length>0;  // one project with decks: research and sources live in the deck page
 document.body.classList.add("mode-"+MODE);if(MODE==="showcase")document.documentElement.classList.add("smooth");
 document.body.classList.toggle("noimg",IMG==="none");applyLook(D.look);document.body.classList.toggle("noprice",!SHOW.prices);
 if(SHOW.charts)await loadScript(CHART_URL).catch(()=>{});  // charts degrade to their data tables when offline
 document.title=D.title||document.title;$("#title").textContent=D.title||"";$("#subtitle").textContent=D.subtitle||"";if(!D.subtitle)$("#subtitle").remove();
 const heroTitle=heroOwnsTitle();
 mastFan(SHOW.fan&&!heroTitle?fanKeys():[]);initTip();initPop();
 $("#foot").textContent="Card data and images from Scryfall; popularity numbers from EDHREC and combos from Commander Spellbook where cited. Magic card names and art © Wizards of the Coast. Unofficial Fan Content permitted under the Fan Content Policy; not approved or endorsed by Wizards.";
 const t=store.get("theme",null);if(t)document.documentElement.dataset.theme=t;setThemeLabel();
 const rerender=()=>{const y=scrollY;go(store.get("tab"),false);scrollTo(0,y)};
 $("#themeBtn").onclick=()=>{const cur=document.documentElement.dataset.theme||(matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light");const n=cur==="dark"?"light":"dark";document.documentElement.dataset.theme=n;store.set("theme",n);setThemeLabel();rerender();$("#themeBtn").focus()};
 matchMedia("(prefers-color-scheme:dark)").addEventListener("change",()=>{setThemeLabel();rerender()});
 // a link to something on another page of the report (a source marker in a research tab) opens that page first
 document.addEventListener("click",e=>{const a=e.target.closest&&e.target.closest('a[href^="#"]');if(!a)return;const id=decodeURIComponent(a.getAttribute("href").slice(1));if(!id)return;
  const t=document.getElementById(id);if(t&&!/^(f|s|src)-/.test(id)){openTo(t);return}  // section links: the browser scrolls
  if(!t&&!anchorTab(id))return;
  e.preventDefault();if(!t){go(id);return}history.replaceState(null,"","#"+id);jumpTo(t)});
 addEventListener("hashchange",()=>{const id=decodeURIComponent(location.hash.slice(1));if(id&&!document.getElementById(id))go(id)});  // typed or back/forward hashes route too
 addEventListener("beforeprint",()=>document.querySelectorAll("details:not([open])").forEach(d=>{d.open=true;d.dataset.printOpened="1"}));
 addEventListener("afterprint",()=>document.querySelectorAll("details[data-print-opened]").forEach(d=>{d.open=false;delete d.dataset.printOpened}));
 buildTabs();initViewer();V3.init();go(location.hash.slice(1)||store.get("tab",""),true)}
const fanKeys=()=>(D.fan||[]).filter(Boolean).slice(0,7);
boot();
