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
let lastTopicTrigger;
let activeTopicId='';
let dialogMode='source';
let sourceViewState={part:'',current:false,q:'',limit:40};
let wordState = {skill:'Reading',scope:'overall',q:'',page:1};
let topicState = {part:'',current:true,q:'',page:1};

function tags(groups){return `<div class="tags">${groups.map(g=>`<span>${esc(groupZh[g]||g)}</span>`).join('')}</div>`}
function showView(){const view=(location.hash.slice(1)||'home').split('?')[0];$$('.view').forEach(el=>el.hidden=el.dataset.view!==view);scrollTo({top:0,behavior:'instant'});}
function buttonTabs(el, items, current, callback){el.innerHTML=items.map(([v,l])=>`<button class="${v===current?'active':''}" data-value="${v}">${l}</button>`).join('');el.querySelectorAll('button').forEach(b=>b.onclick=()=>callback(b.dataset.value));}
function pager(el,page,total,size,callback){const pages=Math.max(1,Math.ceil(total/size));el.innerHTML=`<button ${page===1?'disabled':''} data-d="-1">上一页</button><span>第 ${page} / ${pages} 页</span><button ${page>=pages?'disabled':''} data-d="1">下一页</button>`;el.querySelectorAll('button').forEach(b=>b.onclick=()=>callback(page+Number(b.dataset.d)));}

function renderHome(){
  $('#hero-stats').innerHTML=`<span><b>${fmt(data.meta.documentCount)}</b>统计单元</span><span><b>${fmt(data.meta.filteredTokenCount)}</b>学习词 token</span><span><b>${fmt(speakingData.meta.mergedTopicCount)}</b>口语合并主题</span><span><b>${fmt(speakingData.meta.uniqueQuestionCount)}</b>来源题目</span>`;
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
  const all=speakingData.topics.filter(r=>(!topicState.current||r.current)&&(!topicState.part||r.parts.includes(topicState.part))&&(!topicState.q||r.title.toLowerCase().includes(topicState.q)||r.titleZh.includes(topicState.q)||r.aliases.some(alias=>alias.toLowerCase().includes(topicState.q))));const rows=all.slice((topicState.page-1)*36,topicState.page*36);
  $('#topic-note').textContent=`匹配 ${fmt(all.length)} 个合并主题；${fmt(speakingData.meta.sourceQuestionOccurrences)} 次来源记录已归并为 ${fmt(speakingData.meta.uniqueQuestionCount)} 道去重题目。`;
  $('#topic-grid').innerHTML=rows.map(r=>{const practice=questionBank.topics[r.id];const practiceCount=practice?.questions.length||0;const aliasText=r.aliases.slice(0,3).join(' · ');return `<article class="topic"><div class="topic-meta"><span>${esc(r.titleZh)}</span><span>${fmt(r.sourceCount)} 个来源记录</span></div><h2>${esc(r.title)}</h2><p>${esc(r.partStructure)} · ${fmt(r.questionCount)} 道来源题目${r.currentQuestionCount?` · 当季 ${fmt(r.currentQuestionCount)}`:''}</p>${aliasText?`<p class="topic-aliases">合并：${esc(aliasText)}${r.aliases.length>3?` 等 ${r.aliases.length} 个标题`:''}</p>`:''}${tags([speakingThemeZh[r.primaryTheme]||r.primaryTheme,`${practiceCount} 道本站练习`])}<button class="topic-open" data-topic-id="${esc(r.id)}">查看来源题目与回答辅助 <span aria-hidden="true">→</span></button></article>`}).join('')||'<p>没有匹配主题。</p>';
  $('#topic-grid').querySelectorAll('.topic-open').forEach(button=>button.onclick=()=>openTopic(button.dataset.topicId,button));
  pager($('#topic-pages'),topicState.page,all.length,36,p=>{topicState.page=p;renderTopics()});
}
function openTopic(topicId,trigger){
  const topic=speakingData.topics.find(item=>item.id===topicId);if(!topic)return;
  lastTopicTrigger=trigger||document.activeElement;activeTopicId=topicId;dialogMode='source';sourceViewState={part:'',current:false,q:'',limit:40};
  $('#topic-dialog-title').textContent=topic.title;
  $('#topic-dialog-meta').innerHTML=`<span>${esc(topic.titleZh)}</span><span>${esc(topic.partStructure)}</span><span>${fmt(topic.questionCount)} 道去重来源题</span><span>${fmt(topic.sourceCount)} 个来源记录</span>`;
  $('#topic-dialog-note').innerHTML=`<b>主题已合并</b>　相同问题只显示一次；展开题目可查看全部来源、时期、地区及回答框架。来源题与本站原创练习分栏展示，不把回忆或汇编冒充官方发布。`;
  renderDialogMode();
  const dialog=$('#topic-dialog');dialog.hidden=false;document.body.classList.add('dialog-open');$('#topic-dialog-close').focus();
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
  const controls=`<div class="source-controls"><div id="source-part-tabs" class="tabs small">${[['','全部 Part'],['Part 1','Part 1'],['Part 2','Part 2'],['Part 3','Part 3']].map(([value,label])=>`<button class="${sourceViewState.part===value?'active':''}" data-value="${value}">${label}</button>`).join('')}</div><label class="check"><input id="source-current-only" type="checkbox" ${sourceViewState.current?'checked':''}> 只看 2026</label><form id="source-question-search" class="inline-search"><input value="${esc(sourceViewState.q)}" placeholder="搜索题目、来源或地区" aria-label="搜索来源题目"><button>搜索</button></form></div><p class="source-result-note">当前显示 ${fmt(rows.length)} / ${fmt(filtered.length)} 道；同文题目的多个来源会合并到同一条。</p>`;
  const list=rows.map((question,index)=>{const answerId=`source-answer-${esc(question.id)}`;const refs=question.sourceRefs.map(ref=>speakingData.sources[ref]);const guide=sourceGuide(question.part);return `<article class="question-item source-question"><button class="question-toggle" aria-expanded="false" aria-controls="${answerId}"><span class="question-number">${String(index+1).padStart(2,'0')}</span><span><small>${esc(question.part)}${question.current?' · 含 2026 来源':''}</small><b>${esc(question.text)}</b><em>${esc(refs[0]?.name||'来源未标注')}${refs.length>1?` ＋${refs.length-1} 个来源`:''}</em></span><span class="toggle-mark" aria-hidden="true">＋</span></button><div class="question-answer" id="${answerId}" hidden><section><h3>原始来源</h3><div class="source-citations">${refs.map(source=>`<div><span>${esc(groupZh[source.sourceGroup]||source.sourceGroup)}</span><p><b>${esc(source.name)}</b><small>${esc(source.period)} · ${esc(source.region)}</small></p>${source.url?`<a href="${safeUrl(source.url)}" target="_blank" rel="noreferrer">来源页 ↗</a>`:''}</div>`).join('')}</div></section><section><h3>回答思路</h3><ol>${guide.ideas.map(idea=>`<li>${esc(idea)}</li>`).join('')}</ol></section><section><h3>适用框架</h3><p class="answer-template">${esc(guide.template)}</p></section></div></article>`}).join('');
  const more=filtered.length>rows.length?`<button id="source-load-more" class="load-more">再显示 ${fmt(Math.min(40,filtered.length-rows.length))} 道题</button>`:'';
  $('#question-list').innerHTML=controls+list+more||'<p>没有匹配的来源题目。</p>';
  $('#source-part-tabs').querySelectorAll('button').forEach(button=>button.onclick=()=>{sourceViewState.part=button.dataset.value;sourceViewState.limit=40;renderSourceQuestions()});
  $('#source-current-only').onchange=event=>{sourceViewState.current=event.target.checked;sourceViewState.limit=40;renderSourceQuestions()};
  $('#source-question-search').onsubmit=event=>{event.preventDefault();sourceViewState.q=event.target.querySelector('input').value.trim().toLowerCase();sourceViewState.limit=40;renderSourceQuestions()};
  $('#source-load-more')?.addEventListener('click',()=>{sourceViewState.limit+=40;renderSourceQuestions()});bindQuestionToggles();
}
function renderPracticeQuestions(){
  const practice=questionBank.topics[activeTopicId];if(!practice){$('#question-list').innerHTML='<p>该主题暂无本站练习。</p>';return}
  $('#question-list').innerHTML=`<p class="practice-note"><b>${esc(practice.contentLabel)}</b>　以下内容由本站整理生成，不是来源原题或 IELTS 官方答案。</p>`+practice.questions.map((question,index)=>{const answerId=`answer-${esc(question.id)}`;return `<article class="question-item"><button class="question-toggle" aria-expanded="false" aria-controls="${answerId}"><span class="question-number">${String(index+1).padStart(2,'0')}</span><span><small>${esc(question.part)}</small><b>${esc(question.question)}</b></span><span class="toggle-mark" aria-hidden="true">＋</span></button><div class="question-answer" id="${answerId}" hidden><section><h3>回答思路</h3><ol>${question.ideasZh.map(idea=>`<li>${esc(idea)}</li>`).join('')}</ol></section><section><h3>可替换模板</h3><p class="answer-template">${esc(question.templateEn)}</p></section><section><h3>示范回答</h3><p class="sample-answer" lang="en">${esc(question.sampleAnswerEn)}</p></section><section><h3>本题常用词</h3><div class="vocab-list">${question.vocabulary.map(item=>`<span><b>${esc(item.word)}</b>${esc(item.meaningZh)}</span>`).join('')}</div></section></div></article>`}).join('');bindQuestionToggles();
}
function renderDialogMode(){
  const topic=speakingData.topics.find(item=>item.id===activeTopicId);const practice=questionBank.topics[activeTopicId];
  $('#topic-dialog-mode').innerHTML=`<button class="${dialogMode==='source'?'active':''}" data-mode="source">来源题目 <b>${fmt(topic.questionCount)}</b></button><button class="${dialogMode==='practice'?'active':''}" data-mode="practice">本站练习与示范 <b>${fmt(practice?.questions.length||0)}</b></button>`;
  $('#topic-dialog-mode').querySelectorAll('button').forEach(button=>button.onclick=()=>{dialogMode=button.dataset.mode;renderDialogMode()});
  if(dialogMode==='source')renderSourceQuestions();else renderPracticeQuestions();
}
function closeTopic(){const dialog=$('#topic-dialog');if(dialog.hidden)return;dialog.hidden=true;document.body.classList.remove('dialog-open');lastTopicTrigger?.focus();}
function setupTopicDialog(){
  $('#topic-dialog-close').onclick=closeTopic;
  $('#topic-dialog').onclick=event=>{if(event.target.id==='topic-dialog')closeTopic()};
  addEventListener('keydown',event=>{if(event.key==='Escape')closeTopic()});
}
function facet(task,type,scope,limit=10){return `<div class="facet">${data.writingFacets.filter(r=>r.task===task&&r.facetType===type&&r.scope===scope).slice(0,limit).map(r=>`<div><span>${esc(labelZh[r.label]||r.label)}</span><strong>${fmt(r.count)}</strong><small>${r.sourceCount} 个来源集合</small></div>`).join('')}</div>`}
function renderWriting(){const block=(title,scope,type)=>`<section class="writing-section"><div class="section-head"><div><p class="eyebrow">${scope==='recent_3y'?'Recent 3 years':'Corpus categories'}</p><h2>${title}</h2></div></div><div class="panel-grid"><article class="panel"><h3>Task 1</h3>${facet('Task 1',type,scope)}</article><article class="panel"><h3>Task 2</h3>${facet('Task 2',type,scope)}</article></div></section>`;$('#writing-content').innerHTML=block('大小作文题型','overall','task_type')+block('总体常见主题','overall','theme')+block('2024–2026 常见主题','recent_3y','theme')}
function renderCoverage(){const rows=data.coverage.filter(r=>['Listening','Reading'].includes(r.skill));$('#lr-coverage').innerHTML=rows.map(r=>`<article class="metric"><p class="eyebrow">${r.skill}</p><strong>${fmt(r.documents)}</strong><h3>${skillZh[r.skill]}去重统计单元</h3><p>${fmt(r.filteredTokens)} 个学习词 token · ${r.sources} 个来源集合</p>${tags(r.sourceGroups)}</article>`).join('')}
function renderSources(){const sources=[...data.sources].sort((a,b)=>b.reliabilityWeight-a.reliabilityWeight||b.documentCount-a.documentCount);$('#source-list').innerHTML=sources.map(s=>`<article class="source"><div><span class="grade">${Math.round(s.reliabilityWeight*100)}%</span></div><div><p class="eyebrow">${esc(groupZh[s.sourceGroup]||s.sourceGroup)}</p><h2>${esc(s.name)}</h2><p>${esc(s.notes)}</p>${tags([s.skill,s.period||'时期未标注',s.publicDisplay])}</div><div class="numbers"><b>${fmt(s.documentCount)}</b><small>统计单元</small><b>${fmt(s.wordCount)}</b><small>学习词 token</small>${s.url?`<a href="${safeUrl(s.url)}" target="_blank" rel="noreferrer">原始来源 ↗</a>`:''}</div></article>`).join('')}
async function boot(){try{const manifestRes=await fetch(`data/manifest.json?t=${Date.now()}`,{cache:'no-store'});if(!manifestRes.ok)throw new Error('manifest');manifest=await manifestRes.json();const version=encodeURIComponent(manifest.dataVersion);const [corpusRes,speakingRes,questionsRes]=await Promise.all([fetch(`${manifest.files.corpus}?v=${version}`,{cache:'no-cache'}),fetch(`${manifest.files.speaking}?v=${version}`,{cache:'no-cache'}),fetch(`${manifest.files.questions}?v=${version}`,{cache:'no-cache'})]);if(!corpusRes.ok||!speakingRes.ok||!questionsRes.ok)throw new Error('data');[data,speakingData,questionBank]=await Promise.all([corpusRes.json(),speakingRes.json(),questionsRes.json()]);const updated=new Date(manifest.generatedAt).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});$('#data-status').textContent=`在线数据 ${manifest.dataVersion}`;$('#data-version').innerHTML=`当前公开数据库版本：<b>${esc(manifest.dataVersion)}</b> · 北京时间 ${esc(updated)} · ${fmt(manifest.counts.topics)} 个合并主题 · ${fmt(manifest.counts.sourceQuestions)} 道来源题目。<a href="${safeUrl(manifest.repository)}/tree/main/data" target="_blank" rel="noreferrer">查看 GitHub 数据文件 ↗</a>`;renderHome();renderWords();renderTopics();renderWriting();renderCoverage();renderSources();setupTopicDialog();showView();addEventListener('hashchange',showView);$('#loading').classList.add('done')}catch(e){console.error(e);$('#loading').textContent='数据载入失败，请刷新页面。'}}
boot();
