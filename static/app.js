const {modes,bins}=window.CONFIG;
const content=document.querySelector('#content'),notice=document.querySelector('#notice'),music=document.querySelector('#music');
let state=null,busy=false,clockOffset=0,feedback=null,ranking=[],rankMode='all',rankSort='score',audioCtx;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function section(){return location.hash.slice(1)||({'/leaderboard':'leaderboard','/guide':'guide','/quiz':'play-quiz','/quick_sort':'play-quick','/true_false':'play-tf','/timed':'play-timed'}[location.pathname])||'games';}
async function api(data){
 const res=await fetch(`/api/game?mode=${encodeURIComponent(rankMode)}&sort=${rankSort}`,data?{method:'POST',headers:{'Content-Type':'application/json','X-SmartTrash':'1'},body:JSON.stringify(data)}:{});
 const body=await res.json();
 if(body.player)state=body.player;
 if(body.ranking)ranking=body.ranking;
 if(body.serverTime)clockOffset=body.serverTime-Date.now()/1000;
 if(!res.ok)throw new Error(body.error||'Không thể lưu. Hãy thử lại.');
 return body;
}
function profile(){if(!state)return;document.querySelector('#playerName').textContent=state.name;document.querySelector('#totals').textContent=`⭐ ${state.score} điểm · ♻️ ${state.items} câu đã làm`;}
function render(){
 if(!state)return;profile();const page=section();
 if(page==='leaderboard'){
 content.innerHTML=`<section class="panel"><h2>🏆 Bảng xếp hạng</h2><div class="filters"><select id="rankMode"><option value="all">Tất cả chế độ</option>${Object.entries(modes).map(([id,m])=>`<option value="${id}">${m.name}</option>`).join('')}</select><select id="rankSort"><option value="score">Theo điểm</option><option value="streak">Theo chuỗi tốt nhất</option></select></div><div class="tablewrap"><table><thead><tr><th>Hạng</th><th>Người chơi</th><th>Điểm</th><th>Chuỗi</th></tr></thead><tbody>${ranking.map((p,i)=>`<tr><td>${i+1}</td><td>${esc(p.name)}</td><td>${p.score}</td><td>${p.best}</td></tr>`).join('')}</tbody></table></div></section>`;
 document.querySelector('#rankMode').value=rankMode;document.querySelector('#rankSort').value=rankSort;
 for(const id of ['rankMode','rankSort'])document.querySelector('#'+id).onchange=async e=>{if(id==='rankMode')rankMode=e.target.value;else rankSort=e.target.value;await refresh();};return;
 }
 if(page==='guide'){
 content.innerHTML=`<section class="panel guide"><h2>🌱 Cẩm nang xanh</h2><p>Giảm dùng đồ một lần, tái sử dụng trước khi bỏ đi, và tách rác ngay tại nguồn.</p>${Object.values(bins).map(([name,tip])=>`<h3>${esc(name)}</h3><p>${esc(tip)}</p>`).join('')}<h3>Ba bước dễ nhớ</h3><p>1. Nhận diện vật liệu và mức độ nhiễm bẩn.<br>2. Tách thực phẩm khỏi bao bì; giữ vật liệu tái chế sạch, khô.<br>3. Hỏi đơn vị thu gom địa phương về loại họ tiếp nhận.</p><p>Không tự xử lý pin, hóa chất hay thiết bị điện tử hỏng. Phân loại trong trò chơi là mô hình học tập; hướng dẫn thực tế tùy nơi thu gom.</p><p>Nguồn: <a href="https://www.epa.gov/recycle" target="_blank" rel="noopener">EPA — Recycling</a> · <a href="https://www.epa.gov/recycle/used-household-batteries" target="_blank" rel="noopener">Pin đã dùng</a></p></section>`;return;
 }
 if(page.startsWith('play-')&&modes[page.slice(5)]){
 const mode=page.slice(5),m=modes[mode],g=state.games[mode];
 if(!g){content.innerHTML='<p>Đang mở thử thách…</p>';return;}
 const top=`<div class="gameTop"><h2>${m.name}</h2><a href="#games">← Trang chủ</a></div><div class="stats"><span>⭐ ${g.score} điểm</span><span>🔥 Chuỗi: ${g.streak}</span><span>🏅 Tốt nhất: ${g.best}</span></div>`;
 if(!g.question){content.innerHTML=`<section class="panel">${top}<h3>🎉 Hoàn thành!</h3><p>Bạn trả lời đúng ${g.correct}/${m.length} câu.</p><button id="again">Chơi vòng mới</button> <a class="button secondary" href="#leaderboard">Xem bảng điểm</a></section>`;document.querySelector('#again').onclick=()=>start(mode);return;}
 content.innerHTML=`<section class="panel">${top}<p>Câu ${g.index+1}/${m.length}</p><progress value="${g.index}" max="${m.length}"></progress>${g.deadline?'<p>⏱️ <strong id="timer"></strong></p><progress id="timerbar" max="'+m.seconds+'"></progress>':''}<h3 class="question">${esc(g.question.text)}</h3>${feedback?`<div class="feedback ${feedback.correct?'':'wrong'}">${feedback.correct?'✅ Đúng!':feedback.late?'⏱️ Hết giờ!':'❌ Chưa đúng.'} Đáp án: ${esc(feedback.answer)}<br>${esc(feedback.tip)}</div>`:''}<div class="answers">${g.question.options.map(o=>`<button data-answer="${o.id}" ${busy?'disabled':''}>${esc(o.label)}</button>`).join('')}</div></section>`;
 document.querySelectorAll('[data-answer]').forEach(b=>b.onclick=()=>answer(mode,b.dataset.answer));tick();return;
 }
 content.innerHTML=`<h2>Chọn thử thách của bạn</h2><div class="cards">${Object.entries(modes).map(([id,m],i)=>`<article class="card"><div class="icon">${['📚','⚡','✅','⏱️'][i]}</div><h2>${m.name}</h2><p>${m.length} câu · ${m.seconds?m.seconds+' giây mỗi câu':'Không giới hạn thời gian'}</p><a class="button" href="#play-${id}">${state.games[id]?.question?'Tiếp tục':'Bắt đầu'} →</a></article>`).join('')}</div><section class="panel"><h3>🕒 Lịch sử gần đây</h3>${state.history.slice(0,8).map(h=>`<p>${modes[h.mode].name} · ${h.score} điểm · Chuỗi ${h.best}</p>`).join('')||'<p>Hoàn thành một vòng để xem kết quả tại đây.</p>'}</section>`;
}
async function refresh(){try{await api();render();}catch(e){notice.textContent=e.message;}}
async function start(mode){if(busy)return;busy=true;notice.textContent='';try{await api({action:'start',mode});feedback=null;}catch(e){notice.textContent=e.message;}finally{busy=false;render();}}
async function navigate(){feedback=null;const page=section();if(page.startsWith('play-')&&modes[page.slice(5)]&&!state?.games[page.slice(5)]?.question)await start(page.slice(5));else await refresh();}
function effect(ok){try{audioCtx??=new(window.AudioContext||window.webkitAudioContext)();audioCtx.resume();const osc=audioCtx.createOscillator(),gain=audioCtx.createGain();osc.frequency.value=ok?760:180;gain.gain.setValueAtTime(0.2*Number(document.querySelector('#volume').value),audioCtx.currentTime);gain.gain.exponentialRampToValueAtTime(0.001,audioCtx.currentTime+.3);osc.connect(gain);gain.connect(audioCtx.destination);osc.start();osc.stop(audioCtx.currentTime+.3);}catch{}}
async function answer(mode,value){if(busy)return;const g=state.games[mode];if(!g?.question)return;busy=true;render();try{const body=await api({action:'answer',mode,answer:value,token:g.token});feedback=body.feedback;effect(feedback.correct);notice.textContent='';}catch(e){notice.textContent=e.message;}finally{busy=false;render();}}
function tick(){const page=section();if(!page.startsWith('play-')||busy)return;const mode=page.slice(5),g=state?.games[mode];if(!g?.question||!g.deadline)return;const left=Math.max(0,g.deadline-Date.now()/1000-clockOffset);const timer=document.querySelector('#timer'),bar=document.querySelector('#timerbar');if(timer)timer.textContent=Math.ceil(left)+' giây';if(bar)bar.value=left;if(left===0)answer(mode,null);}
setInterval(tick,250);
document.querySelector('#rename').onclick=async()=>{const name=prompt('Tên của bạn (1–40 ký tự):',state?.name||'');if(name===null)return;try{await api({action:'name',name});render();}catch(e){notice.textContent=e.message;}};
document.querySelector('#reset').onclick=async()=>{if(!confirm('Xóa toàn bộ điểm và tiến độ của người chơi này?'))return;try{await api({action:'reset',confirm:true});feedback=null;location.hash='games';render();}catch(e){notice.textContent=e.message;}};
music.volume=.7;document.querySelector('#volume').oninput=e=>{music.volume=Number(e.target.value);};document.querySelector('#soundToggle').onclick=async()=>{if(music.paused){try{await music.play();document.querySelector('#soundToggle').textContent='🔇 Tắt nhạc';}catch{notice.textContent='Không thể phát nhạc. Hãy thử bấm lại.';}}else{music.pause();document.querySelector('#soundToggle').textContent='🔊 Bật nhạc';}};
window.addEventListener('hashchange',navigate);refresh().then(navigate);
