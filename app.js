const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const fmt = (n) => new Intl.NumberFormat('zh-CN').format(n);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeUrl = (value) => /^https?:\/\//i.test(String(value || '')) ? esc(value) : '#';
const skillZh = {Listening:'听力',Speaking:'口语',Reading:'阅读',Writing:'写作'};
const groupZh = {official_public:'官方公开材料',cambridge_derived:'剑桥派生词汇',test_taker_recall:'考生回忆',public_compilation:'公开非官方汇编',user_provided:'用户提供材料',third_party_prediction:'第三方预测题'};
const confidenceZh = {high:'高',medium:'中',exploratory:'探索'};
const labelZh = {'agree-disagree/opinion':'同意/不同意（观点题）','discuss-both-views':'讨论双方观点','advantages-disadvantages/outweigh':'优缺点 / 是否利大于弊','problem-solution/causes-effects':'原因·影响·解决方案','two-part/direct questions':'双问题 / 直接问答','positive-negative development':'积极或消极发展','line/trend':'折线与趋势','bar/column':'柱状图','pie/proportion':'饼图与比例',table:'表格','map/plan':'地图与平面变化',process:'流程图','mixed/multiple visuals':'混合图','diagram/system/other':'示意图 / 系统图 / 其他',education:'教育','children-family':'儿童与家庭','work-economy':'工作与经济','government-public-policy':'政府与公共政策','society-culture':'社会与文化','technology-media':'科技与媒体','environment-energy':'环境与能源','transport-cities-housing':'交通·城市·住房',health:'健康',crime:'犯罪',other:'其他'};
const speakingThemeZh = {'person/family/friends':'人物·家庭·朋友','object/technology':'物品·科技','travel-transport':'旅行·交通',place:'地点','home/hometown/accommodation':'家·家乡·居住','event/experience':'事件·经历',food:'食物·饮食','activity/hobby':'活动·爱好','society-government':'社会·公共事务','work-study':'学习·工作',culture:'文化·传统',other:'日常·综合'};
let data;
let speakingData;
let questionBank;
let manifest;
let activeTopicId='';
let expandedTopicId='';
let dialogMode='practice';
let sourceViewState={part:'',current:false,q:'',limit:40};
let wordState = {skill:'Reading',scope:'overall',q:'',page:1};
let topicState = {part:'',current:true,q:'',page:1};

function tags(groups){return `<div class="tags">${groups.map(g=>`<span>${esc(groupZh[g]||g)}</span>`).join('')}</div>`}
function showView(){const view=(location.hash.slice(1)||'home').split('?')[0];$$('.view').forEach(el=>el.hidden=el.dataset.view!==view);scrollTo({top:0,behavior:'instant'});}
function buttonTabs(el, items, current, callback){el.innerHTML=items.map(([v,l])=>`<button class="${v===current?'active':''}" data-value="${v}">${l}</button>`).join('');el.querySelectorAll('button').forEach(b=>b.onclick=()=>callback(b.dataset.value));}
function pager(el,page,total,size,callback){const pages=Math.max(1,Math.ceil(total/size));el.innerHTML=`<button ${page===1?'disabled':''} data-d="-1">上一页</button><span>第 ${page} / ${pages} 页</span><button ${page>=pages?'disabled':''} data-d="1">下一页</button>`;el.querySelectorAll('button').forEach(b=>b.onclick=()=>callback(page+Number(b.dataset.d)));}

function renderHome(){
  $('#hero-stats').innerHTML=`<span><b>${fmt(data.meta.documentCount)}</b>统计单元</span><span><b>${fmt(data.meta.filteredTokenCount)}</b>学习词 token</span><span><b>${fmt(speakingData.meta.mergedTopicCount)}</b>口语合并主题</span><span><b>${fmt(questionBank.meta.practiceQuestionCount)}</b>准备好的练习问答</span>`;
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
function clearTopicHover(){
  const grid=$('#topic-grid');if(!grid)return;grid.querySelectorAll('.topic.hover-main,.topic.hover-peer').forEach(card=>{card.classList.remove('hover-main','hover-peer');card.style.removeProperty('flex-basis')});
}
function setupTopicHover(){
  const grid=$('#topic-grid');if(!grid||!matchMedia('(hover: hover) and (pointer: fine)').matches)return;
  grid.onpointerleave=clearTopicHover;
  grid.querySelectorAll('.topic').forEach(card=>card.onpointerenter=()=>{
    if(expandedTopicId)return;clearTopicHover();
    const top=card.getBoundingClientRect().top;const row=[...grid.querySelectorAll('.topic')].filter(item=>Math.abs(item.getBoundingClientRect().top-top)<3);if(row.length<2)return;
    const gap=parseFloat(getComputedStyle(grid).columnGap)||14;const available=grid.clientWidth-gap*(row.length-1)-4;const mainRatio=row.length>=3?.46:.62;const mainWidth=available*mainRatio;const peerWidth=(available-mainWidth)/(row.length-1);
    row.forEach(item=>{const main=item===card;item.classList.add(main?'hover-main':'hover-peer');item.style.flexBasis=`${main?mainWidth:peerWidth}px`});
  });
}
function renderTopics(){
  buttonTabs($('#part-tabs'),[['','全部 Part'],['Part 1','Part 1'],['Part 2','Part 2'],['Part 3','Part 3']],topicState.part,v=>{expandedTopicId='';activeTopicId='';topicState.part=v;topicState.page=1;renderTopics()});
  $('#current-only').checked=topicState.current;$('#current-only').onchange=e=>{expandedTopicId='';activeTopicId='';topicState.current=e.target.checked;topicState.page=1;renderTopics()};$('#topic-search input').value=topicState.q;$('#topic-search').onsubmit=e=>{e.preventDefault();expandedTopicId='';activeTopicId='';topicState.q=e.target.querySelector('input').value.trim().toLowerCase();topicState.page=1;renderTopics()};
  const all=speakingData.topics.filter(r=>(!topicState.part||r.parts.includes(topicState.part))&&(!topicState.current||(topicState.part?r.questions.some(question=>question.part===topicState.part&&question.current):r.current))&&(!topicState.q||r.title.toLowerCase().includes(topicState.q)||r.titleZh.includes(topicState.q)||r.aliases.some(alias=>alias.toLowerCase().includes(topicState.q))));const rows=all.slice((topicState.page-1)*36,topicState.page*36);
  $('#topic-note').textContent=`匹配 ${fmt(all.length)} 个合并主题；${topicState.part||'全部 Part'} 只展示对应的准备题，来源材料放在展开后的参考区。`;
  $('#topic-grid').innerHTML=rows.map(r=>{const practice=questionBank.topics[r.id];const prepared=(practice?.questions||[]).filter(question=>!topicState.part||question.part===topicState.part);const aliasText=r.aliases.slice(0,3).join(' · ');const partLabel=topicState.part||r.partStructure;return `<article class="topic" data-topic-id="${esc(r.id)}"><div class="topic-meta"><span>${esc(r.titleZh)}</span><span>${esc(partLabel)}</span></div><h2>${esc(r.title)}</h2><p>${fmt(prepared.length)} 道准备题 · 含回答思路、模板与示范</p>${aliasText?`<p class="topic-aliases">合并：${esc(aliasText)}${r.aliases.length>3?` 等 ${r.aliases.length} 个标题`:''}</p>`:''}${tags([speakingThemeZh[r.primaryTheme]||r.primaryTheme,'练习优先'])}<button class="topic-open" data-topic-id="${esc(r.id)}" aria-expanded="false">展开练习 <span aria-hidden="true">＋</span></button></article>`}).join('')||'<p>没有匹配主题。</p>';
  $('#topic-grid').querySelectorAll('.topic-open').forEach(button=>button.onclick=()=>toggleInlineTopic(button.dataset.topicId,button));
  setupTopicHover();
  pager($('#topic-pages'),topicState.page,all.length,36,p=>{expandedTopicId='';activeTopicId='';topicState.page=p;renderTopics()});
}
function animateTopicLayout(update){
  const before=new Map($$('.topic').map(card=>[card.dataset.topicId,card.getBoundingClientRect()]));update();
  $$('.topic').forEach(card=>{const first=before.get(card.dataset.topicId);if(!first)return;const last=card.getBoundingClientRect();const dx=first.left-last.left;const dy=first.top-last.top;const sx=last.width?first.width/last.width:1;if(Math.abs(dx)<1&&Math.abs(dy)<1&&Math.abs(sx-1)<.01)return;card.style.transformOrigin='top left';card.style.transition='none';card.style.transform=`translate(${dx}px,${dy}px) scaleX(${sx})`;requestAnimationFrame(()=>{card.style.transition='transform 420ms cubic-bezier(.22,1,.36,1), border-color 180ms ease, box-shadow 180ms ease';card.style.transform='';setTimeout(()=>{card.style.removeProperty('transform-origin');card.style.removeProperty('transition');card.style.removeProperty('transform')},440)})});
}
function toggleInlineTopic(topicId,trigger){
  const topic=speakingData.topics.find(item=>item.id===topicId);if(!topic)return;
  const update=()=>{
    clearTopicHover();
    const previous=$('.topic.expanded');if(previous){previous.classList.remove('expanded');const previousButton=previous.querySelector('.topic-open');if(previousButton){previousButton.setAttribute('aria-expanded','false');previousButton.innerHTML='展开练习 <span aria-hidden="true">＋</span>'}previous.querySelector('.topic-inline-detail')?.remove()}
    if(expandedTopicId===topicId){expandedTopicId='';activeTopicId='';return}
    expandedTopicId=topicId;activeTopicId=topicId;dialogMode='practice';sourceViewState={part:topicState.part,current:topicState.current,q:'',limit:30};
    const card=trigger.closest('.topic');card.classList.add('expanded');trigger.setAttribute('aria-expanded','true');trigger.innerHTML='收起练习 <span aria-hidden="true">−</span>';
    card.insertAdjacentHTML('beforeend',`<section class="topic-inline-detail" aria-label="${esc(topic.title)} 学习内容"><div class="topic-inline-inner"><div class="inline-intro"><div><p class="eyebrow">Prepared practice first</p><h3>${esc(topicState.part||'全部 Part')} · ${esc(topic.titleZh)}</h3><p>先练习我们准备的问题与答案；需要核对题目出处时再打开“来源参考”。</p></div></div><div id="topic-dialog-mode" class="dialog-mode" aria-label="题目内容类型"></div><div id="question-list" class="question-list"></div></div></section>`);
    renderDialogMode();requestAnimationFrame(()=>card.querySelector('.topic-inline-detail')?.classList.add('ready'));setTimeout(()=>card.scrollIntoView({behavior:'smooth',block:'start'}),460);
  };
  animateTopicLayout(update);
}
function sourceGuide(part){
  if(part==='Part 1')return {ideas:['第一句直接回答，不要复述题目','补充一个真实的小例子或习惯','用 because 解释原因，控制在 2–4 句'],template:'I’d say ___. For example, ___. I feel this way mainly because ___.'};
  if(part==='Part 2')return {ideas:['按题卡提示覆盖人物、时间、地点和经过','用 before–during–after 形成清楚时间线','加入一个感官细节和一个转折','结尾解释它为何重要或难忘'],template:'I’d like to talk about ___. It happened when ___. At first, ___. Then ___. What I remember most is ___. Looking back, ___.'};
  return {ideas:['先给清楚立场或核心原因','解释因果，不只罗列观点','加入具体例子或群体比较','承认例外后给出平衡结论'],template:'I think the main reason is ___. This is because ___. A good example is ___. Admittedly, ___. Even so, ___.'};
}
function bindQuestionToggles(){
  $('#question-list').querySelectorAll('.question-toggle').forEach(button=>button.onclick=()=>{const panel=$(`#${CSS.escape(button.getAttribute('aria-controls'))}`);const expanded=button.getAttribute('aria-expanded')==='true';button.setAttribute('aria-expanded',String(!expanded));button.querySelector('.toggle-mark').textContent=expanded?'＋':'−';panel.hidden=expanded;});
}
function renderSourceQuestions(){
  const topic=speakingData.topics.find(item=>item.id===activeTopicId);if(!topic)return;
  const filtered=topic.questions.filter(question=>(!sourceViewState.part||question.part===sourceViewState.part)&&(!sourceViewState.current||question.current)&&(!sourceViewState.q||question.text.toLowerCase().includes(sourceViewState.q)||question.sourceRefs.some(ref=>{const source=speakingData.sources[ref];return source.name.toLowerCase().includes(sourceViewState.q)||source.region.toLowerCase().includes(sourceViewState.q)})));const rows=filtered.slice(0,sourceViewState.limit);
  const partControl=topicState.part?`<span class="part-lock">当前只看 ${esc(topicState.part)}</span>`:`<div id="source-part-tabs" class="tabs small">${[['','全部 Part'],['Part 1','Part 1'],['Part 2','Part 2'],['Part 3','Part 3']].map(([value,label])=>`<button class="${sourceViewState.part===value?'active':''}" data-value="${value}">${label}</button>`).join('')}</div>`;
  const controls=`<div class="source-controls">${partControl}<label class="check"><input id="source-current-only" type="checkbox" ${sourceViewState.current?'checked':''}> 只看 2026</label><form id="source-question-search" class="inline-search"><input value="${esc(sourceViewState.q)}" placeholder="搜索题目、来源或地区" aria-label="搜索来源题目"><button>搜索</button></form></div><p class="source-result-note">来源材料仅作核对参考；同文题目的多个来源已合并到同一条。</p>`;
  const list=rows.map((question,index)=>{const answerId=`source-answer-${esc(question.id)}`;const refs=question.sourceRefs.map(ref=>speakingData.sources[ref]);const guide=sourceGuide(question.part);return `<article class="question-item source-question"><button class="question-toggle" aria-expanded="false" aria-controls="${answerId}"><span class="question-number">${String(index+1).padStart(2,'0')}</span><span><small>${esc(question.part)}${question.current?' · 含 2026 来源':''}</small><b>${esc(question.text)}</b><em>${esc(refs[0]?.name||'来源未标注')}${refs.length>1?` ＋${refs.length-1} 个来源`:''}</em></span><span class="toggle-mark" aria-hidden="true">＋</span></button><div class="question-answer" id="${answerId}" hidden><section><h3>原始来源</h3><div class="source-citations">${refs.map(source=>`<div><span>${esc(groupZh[source.sourceGroup]||source.sourceGroup)}</span><p><b>${esc(source.name)}</b><small>${esc(source.period)} · ${esc(source.region)}</small></p>${source.url?`<a href="${safeUrl(source.url)}" target="_blank" rel="noreferrer">来源页 ↗</a>`:''}</div>`).join('')}</div></section><section><h3>回答思路</h3><ol>${guide.ideas.map(idea=>`<li>${esc(idea)}</li>`).join('')}</ol></section><section><h3>适用框架</h3><p class="answer-template">${esc(guide.template)}</p></section></div></article>`}).join('');
  const more=filtered.length>rows.length?`<button id="source-load-more" class="load-more">显示更多来源题</button>`:'';
  $('#question-list').innerHTML=controls+list+more||'<p>没有匹配的来源题目。</p>';
  $('#source-part-tabs')?.querySelectorAll('button').forEach(button=>button.onclick=()=>{sourceViewState.part=button.dataset.value;sourceViewState.limit=30;renderSourceQuestions()});
  $('#source-current-only').onchange=event=>{sourceViewState.current=event.target.checked;sourceViewState.limit=40;renderSourceQuestions()};
  $('#source-question-search').onsubmit=event=>{event.preventDefault();sourceViewState.q=event.target.querySelector('input').value.trim().toLowerCase();sourceViewState.limit=40;renderSourceQuestions()};
  $('#source-load-more')?.addEventListener('click',()=>{sourceViewState.limit+=40;renderSourceQuestions()});bindQuestionToggles();
}
function renderPracticeQuestions(){
  const practice=questionBank.topics[activeTopicId];if(!practice){$('#question-list').innerHTML='<p>该主题暂无本站练习。</p>';return}
  const prepared=practice.questions.filter(question=>!topicState.part||question.part===topicState.part);
  $('#question-list').innerHTML=`<p class="practice-note"><b>${esc(topicState.part||'全部 Part')} · ${esc(practice.contentLabel)}</b>　先练这些准备好的问题；每题都有思路、模板、示范回答和常用词。</p>`+prepared.map((question,index)=>{const answerId=`answer-${esc(question.id)}`;return `<article class="question-item"><button class="question-toggle" aria-expanded="false" aria-controls="${answerId}"><span class="question-number">${String(index+1).padStart(2,'0')}</span><span><small>${esc(question.part)}</small><b>${esc(question.question)}</b></span><span class="toggle-mark" aria-hidden="true">＋</span></button><div class="question-answer" id="${answerId}" hidden><section><h3>回答思路</h3><ol>${question.ideasZh.map(idea=>`<li>${esc(idea)}</li>`).join('')}</ol></section><section><h3>可替换模板</h3><p class="answer-template">${esc(question.templateEn)}</p></section><section><h3>示范回答</h3><p class="sample-answer" lang="en">${esc(question.sampleAnswerEn)}</p></section><section><h3>本题常用词</h3><div class="vocab-list">${question.vocabulary.map(item=>`<span><b>${esc(item.word)}</b>${esc(item.meaningZh)}</span>`).join('')}</div></section></div></article>`}).join('');bindQuestionToggles();
}
function renderDialogMode(){
  const topic=speakingData.topics.find(item=>item.id===activeTopicId);const practice=questionBank.topics[activeTopicId];
  const prepared=(practice?.questions||[]).filter(question=>!topicState.part||question.part===topicState.part);
  $('#topic-dialog-mode').innerHTML=`<button class="${dialogMode==='practice'?'active':''}" data-mode="practice">准备的问题与示范 <b>${fmt(prepared.length)}</b></button><button class="${dialogMode==='source'?'active':''}" data-mode="source">来源参考</button>`;
  $('#topic-dialog-mode').querySelectorAll('button').forEach(button=>button.onclick=()=>{dialogMode=button.dataset.mode;renderDialogMode()});
  if(dialogMode==='source')renderSourceQuestions();else renderPracticeQuestions();
}
function facet(task,type,scope,limit=10){return `<div class="facet">${data.writingFacets.filter(r=>r.task===task&&r.facetType===type&&r.scope===scope).slice(0,limit).map(r=>`<div><span>${esc(labelZh[r.label]||r.label)}</span><strong>${fmt(r.count)}</strong><small>${r.sourceCount} 个来源集合</small></div>`).join('')}</div>`}
function renderWriting(){const block=(title,scope,type)=>`<section class="writing-section"><div class="section-head"><div><p class="eyebrow">${scope==='recent_3y'?'Recent 3 years':'Corpus categories'}</p><h2>${title}</h2></div></div><div class="panel-grid"><article class="panel"><h3>Task 1</h3>${facet('Task 1',type,scope)}</article><article class="panel"><h3>Task 2</h3>${facet('Task 2',type,scope)}</article></div></section>`;$('#writing-content').innerHTML=block('大小作文题型','overall','task_type')+block('总体常见主题','overall','theme')+block('2024–2026 常见主题','recent_3y','theme')}
function renderCoverage(){const rows=data.coverage.filter(r=>['Listening','Reading'].includes(r.skill));$('#lr-coverage').innerHTML=rows.map(r=>`<article class="metric"><p class="eyebrow">${r.skill}</p><strong>${fmt(r.documents)}</strong><h3>${skillZh[r.skill]}去重统计单元</h3><p>${fmt(r.filteredTokens)} 个学习词 token · ${r.sources} 个来源集合</p>${tags(r.sourceGroups)}</article>`).join('')}
function renderSources(){const sources=[...data.sources].sort((a,b)=>b.reliabilityWeight-a.reliabilityWeight||b.documentCount-a.documentCount);$('#source-list').innerHTML=sources.map(s=>`<article class="source"><div><span class="grade">${Math.round(s.reliabilityWeight*100)}%</span></div><div><p class="eyebrow">${esc(groupZh[s.sourceGroup]||s.sourceGroup)}</p><h2>${esc(s.name)}</h2><p>${esc(s.notes)}</p>${tags([s.skill,s.period||'时期未标注',s.publicDisplay])}</div><div class="numbers"><b>${fmt(s.documentCount)}</b><small>统计单元</small><b>${fmt(s.wordCount)}</b><small>学习词 token</small>${s.url?`<a href="${safeUrl(s.url)}" target="_blank" rel="noreferrer">原始来源 ↗</a>`:''}</div></article>`).join('')}
async function boot(){try{const manifestRes=await fetch(`data/manifest.json?t=${Date.now()}`,{cache:'no-store'});if(!manifestRes.ok)throw new Error('manifest');manifest=await manifestRes.json();const version=encodeURIComponent(manifest.dataVersion);const [corpusRes,speakingRes,questionsRes]=await Promise.all([fetch(`${manifest.files.corpus}?v=${version}`,{cache:'no-cache'}),fetch(`${manifest.files.speaking}?v=${version}`,{cache:'no-cache'}),fetch(`${manifest.files.questions}?v=${version}`,{cache:'no-cache'})]);if(!corpusRes.ok||!speakingRes.ok||!questionsRes.ok)throw new Error('data');[data,speakingData,questionBank]=await Promise.all([corpusRes.json(),speakingRes.json(),questionsRes.json()]);const updated=new Date(manifest.generatedAt).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});$('#data-status').textContent=`在线数据 ${manifest.dataVersion}`;$('#data-version').innerHTML=`当前公开数据库版本：<b>${esc(manifest.dataVersion)}</b> · 北京时间 ${esc(updated)} · ${fmt(manifest.counts.topics)} 个合并主题 · ${fmt(manifest.counts.practiceQuestions)} 道准备问答。<a href="${safeUrl(manifest.repository)}/tree/main/data" target="_blank" rel="noreferrer">查看 GitHub 数据文件 ↗</a>`;renderHome();renderWords();renderTopics();renderWriting();renderCoverage();renderSources();showView();addEventListener('hashchange',showView);$('#loading').classList.add('done')}catch(e){console.error(e);$('#loading').textContent='数据载入失败，请刷新页面。'}}
boot();
