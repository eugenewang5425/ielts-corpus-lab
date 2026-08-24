const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const fmt = (n) => new Intl.NumberFormat('zh-CN').format(n);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeUrl = (value) => /^https?:\/\//i.test(String(value || '')) ? esc(value) : '#';
const skillZh = {Listening:'听力',Speaking:'口语',Reading:'阅读',Writing:'写作'};
const groupZh = {official_public:'官方公开材料',cambridge_derived:'剑桥派生词汇',test_taker_recall:'考生回忆',public_compilation:'公开非官方汇编',user_provided:'用户提供材料',third_party_prediction:'第三方预测题'};
const confidenceZh = {high:'高',medium:'中',exploratory:'探索'};
const labelZh = {'agree-disagree/opinion':'同意/不同意（观点题）','discuss-both-views':'讨论双方观点','advantages-disadvantages/outweigh':'优缺点 / 是否利大于弊','problem-solution/causes-effects':'原因·影响·解决方案','two-part/direct questions':'双问题 / 直接问答','positive-negative development':'积极或消极发展','line/trend':'折线与趋势','bar/column':'柱状图','pie/proportion':'饼图与比例',table:'表格','map/plan':'地图与平面变化',process:'流程图','mixed/multiple visuals':'混合图','diagram/system/other':'示意图 / 系统图 / 其他',education:'教育','children-family':'儿童与家庭','work-economy':'工作与经济','government-public-policy':'政府与公共政策','society-culture':'社会与文化','technology-media':'科技与媒体','environment-energy':'环境与能源','transport-cities-housing':'交通·城市·住房',health:'健康',crime:'犯罪',other:'其他'};
let data;
let wordState = {skill:'Reading',scope:'overall',q:'',page:1};
let topicState = {part:'',current:true,q:'',page:1};

function tags(groups){return `<div class="tags">${groups.map(g=>`<span>${esc(groupZh[g]||g)}</span>`).join('')}</div>`}
function showView(){const view=(location.hash.slice(1)||'home').split('?')[0];$$('.view').forEach(el=>el.hidden=el.dataset.view!==view);scrollTo({top:0,behavior:'instant'});}
function buttonTabs(el, items, current, callback){el.innerHTML=items.map(([v,l])=>`<button class="${v===current?'active':''}" data-value="${v}">${l}</button>`).join('');el.querySelectorAll('button').forEach(b=>b.onclick=()=>callback(b.dataset.value));}
function pager(el,page,total,size,callback){const pages=Math.max(1,Math.ceil(total/size));el.innerHTML=`<button ${page===1?'disabled':''} data-d="-1">上一页</button><span>第 ${page} / ${pages} 页</span><button ${page>=pages?'disabled':''} data-d="1">下一页</button>`;el.querySelectorAll('button').forEach(b=>b.onclick=()=>callback(page+Number(b.dataset.d)));}

function renderHome(){
  $('#hero-stats').innerHTML=`<span><b>${fmt(data.meta.documentCount)}</b>统计单元</span><span><b>${fmt(data.meta.filteredTokenCount)}</b>学习词 token</span><span><b>${fmt(data.meta.topicCount)}</b>口语整合主题</span>`;
  $('#home-coverage').innerHTML=data.coverage.map(r=>`<article class="metric"><strong>${fmt(r.documents)}</strong><h3>${skillZh[r.skill]}</h3><p>${fmt(r.filteredTokens)} 个学习词 token · ${r.sources} 个来源集合</p>${tags(r.sourceGroups)}</article>`).join('');
  $('#hero-search').onsubmit=e=>{e.preventDefault();wordState.q=new FormData(e.target).get('q').trim();wordState.page=1;location.hash='words';renderWords()};
}
function renderWords(){
  buttonTabs($('#skill-tabs'),Object.entries(skillZh),wordState.skill,v=>{wordState.skill=v;wordState.page=1;renderWords()});
  buttonTabs($('#scope-tabs'),[['overall','总体'],['recent_5y','近五年']],wordState.scope,v=>{wordState.scope=v;wordState.page=1;renderWords()});
  $('#word-search input').value=wordState.q;$('#word-search').onsubmit=e=>{e.preventDefault();wordState.q=e.target.querySelector('input').value.trim().toLowerCase();wordState.page=1;renderWords()};
  const all=data.words.filter(r=>r.skill===wordState.skill&&r.scope===wordState.scope&&(!wordState.q||r.lemma.includes(wordState.q)));const rows=all.slice((wordState.page-1)*50,wordState.page*50);
  $('#word-note').textContent=`共 ${fmt(all.length)} 个达到最低文档频次的学习词`;
  $('#word-body').innerHTML=rows.map(r=>`<tr><td><span class="rank">#${r.rank}</span><b>${esc(r.display)}</b></td><td>${fmt(r.occurrenceCount)}</td><td>${fmt(r.documentFrequency)} <small>(${(r.documentCoverage*100).toFixed(1)}%)</small></td><td>${r.normalizedPer10k.toFixed(2)}</td><td>${r.sourceCount}</td><td><span class="badge ${esc(r.confidence)}">${esc(confidenceZh[r.confidence])}</span></td></tr>`).join('')||'<tr><td colspan="6">没有匹配的词。</td></tr>';
  pager($('#word-pages'),wordState.page,all.length,50,p=>{wordState.page=p;renderWords()});
}
function renderTopics(){
  buttonTabs($('#part-tabs'),[['','全部 Part'],['Part 1','Part 1'],['Part 2','Part 2'],['Part 3','Part 3']],topicState.part,v=>{topicState.part=v;topicState.page=1;renderTopics()});
  $('#current-only').checked=topicState.current;$('#current-only').onchange=e=>{topicState.current=e.target.checked;topicState.page=1;renderTopics()};$('#topic-search input').value=topicState.q;$('#topic-search').onsubmit=e=>{e.preventDefault();topicState.q=e.target.querySelector('input').value.trim().toLowerCase();topicState.page=1;renderTopics()};
  const all=data.topics.filter(r=>(!topicState.current||r.current)&&(!topicState.part||r.partStructure.includes(topicState.part))&&(!topicState.q||r.title.toLowerCase().includes(topicState.q)||r.primaryTheme.toLowerCase().includes(topicState.q)));const rows=all.slice((topicState.page-1)*36,topicState.page*36);
  $('#topic-note').textContent=`匹配 ${fmt(all.length)} 个整合主题；公开镜像只展示主题索引，不复制第三方完整题面。`;
  $('#topic-grid').innerHTML=rows.map(r=>`<article class="topic"><div class="topic-meta"><span>${esc(r.period||'时间未标注')}</span><span>${esc(r.region)}</span></div><h2>${esc(r.title)}</h2><p>${esc(r.partStructure)} · ${r.questionCount} 个题目索引</p>${tags([r.primaryTheme,groupZh[r.sourceGroup]||r.sourceGroup])}${r.sourceUrl?`<a href="${safeUrl(r.sourceUrl)}" target="_blank" rel="noreferrer">查看原始来源 ↗</a>`:'<span class="muted-link">本地材料，仅统计</span>'}</article>`).join('')||'<p>没有匹配主题。</p>';
  pager($('#topic-pages'),topicState.page,all.length,36,p=>{topicState.page=p;renderTopics()});
}
function facet(task,type,scope,limit=10){return `<div class="facet">${data.writingFacets.filter(r=>r.task===task&&r.facetType===type&&r.scope===scope).slice(0,limit).map(r=>`<div><span>${esc(labelZh[r.label]||r.label)}</span><strong>${fmt(r.count)}</strong><small>${r.sourceCount} 个来源集合</small></div>`).join('')}</div>`}
function renderWriting(){const block=(title,scope,type)=>`<section class="writing-section"><div class="section-head"><div><p class="eyebrow">${scope==='recent_3y'?'Recent 3 years':'Corpus categories'}</p><h2>${title}</h2></div></div><div class="panel-grid"><article class="panel"><h3>Task 1</h3>${facet('Task 1',type,scope)}</article><article class="panel"><h3>Task 2</h3>${facet('Task 2',type,scope)}</article></div></section>`;$('#writing-content').innerHTML=block('大小作文题型','overall','task_type')+block('总体常见主题','overall','theme')+block('2024–2026 常见主题','recent_3y','theme')}
function renderCoverage(){const rows=data.coverage.filter(r=>['Listening','Reading'].includes(r.skill));$('#lr-coverage').innerHTML=rows.map(r=>`<article class="metric"><p class="eyebrow">${r.skill}</p><strong>${fmt(r.documents)}</strong><h3>${skillZh[r.skill]}去重统计单元</h3><p>${fmt(r.filteredTokens)} 个学习词 token · ${r.sources} 个来源集合</p>${tags(r.sourceGroups)}</article>`).join('')}
function renderSources(){const sources=[...data.sources].sort((a,b)=>b.reliabilityWeight-a.reliabilityWeight||b.documentCount-a.documentCount);$('#source-list').innerHTML=sources.map(s=>`<article class="source"><div><span class="grade">${Math.round(s.reliabilityWeight*100)}%</span></div><div><p class="eyebrow">${esc(groupZh[s.sourceGroup]||s.sourceGroup)}</p><h2>${esc(s.name)}</h2><p>${esc(s.notes)}</p>${tags([s.skill,s.period||'时期未标注',s.publicDisplay])}</div><div class="numbers"><b>${fmt(s.documentCount)}</b><small>统计单元</small><b>${fmt(s.wordCount)}</b><small>学习词 token</small>${s.url?`<a href="${safeUrl(s.url)}" target="_blank" rel="noreferrer">原始来源 ↗</a>`:''}</div></article>`).join('')}
async function boot(){try{const res=await fetch('data/corpus.json');if(!res.ok)throw new Error('data');data=await res.json();renderHome();renderWords();renderTopics();renderWriting();renderCoverage();renderSources();showView();addEventListener('hashchange',showView);$('#loading').classList.add('done')}catch(e){$('#loading').textContent='数据载入失败，请刷新页面。'}}
boot();
