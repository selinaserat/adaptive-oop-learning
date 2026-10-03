// This UI renders API results. Official scores and eligibility come from Flask.
const $ = id => document.getElementById(id);
let studentId = null;
let topics = [];
let dashboard = null;
let assessmentTopic = null;
let questions = [];
let busy = false;

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function notice(message = '', error = false) {
  $('notice').textContent = message;
  $('notice').classList.toggle('error', error);
}
async function api(path, body) {
  const response = await fetch('/api' + path, body === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message || 'Request failed. Please try again.');
  return data;
}
async function action(task) {
  if (busy) return;
  busy = true;
  const buttons = [...document.querySelectorAll('button')].filter(b => !b.disabled);
  buttons.forEach(b => b.disabled = true);
  try { await task(); } catch (error) { notice(error.message, true); }
  finally { busy = false; buttons.forEach(b => b.disabled = false); }
}
function show(view) {
  ['welcome','dashboard','workspace'].forEach(id => $(id).hidden = id !== view);
  $('switch').hidden = studentId === null;
}
function topicName(id) { return topics.find(t => t.topic_id === id)?.title || 'Topic ' + id; }
function button(text, task, disabled = false) {
  const b = node('button', text, 'quiet');
  b.type = 'button'; b.disabled = disabled;
  b.addEventListener('click', () => action(task));
  return b;
}
async function refresh() {
  const [data, history] = await Promise.all([
    api(`/students/${studentId}/dashboard`), api(`/students/${studentId}/attempts`)
  ]);
  dashboard = data;
  $('greeting').textContent = `Welcome, ${data.student.name}.`;
  $('mastered-count').textContent = `${data.progress.filter(p => p.state === 'mastered').length} / ${topics.length}`;
  $('threshold').textContent = `${data.mastery_threshold}% to master a topic`;
  const rec = data.recommendation;
  const panel = $('recommendation'); panel.replaceChildren();
  const copy = node('div'); copy.append(node('span','YOUR NEXT STEP','eyebrow'));
  copy.append(node('h2',rec.action === 'take_diagnostic' ? 'Find your starting point' : rec.action === 'completed' ? 'A foundation worth celebrating.' : topicName(rec.topic_id)));
  copy.append(node('p',rec.action === 'completed' ? 'You’ve mastered every topic. Revisit a lesson to keep your skills fresh.' : rec.reason));
  panel.append(copy);
  if (rec.action !== 'completed') panel.append(button(rec.action === 'take_diagnostic' ? 'Take diagnostic →' : 'Continue learning →', () => openAssessment(rec.topic_id)));
  $('topics').replaceChildren();
  for (const topic of topics) {
    const progress = data.progress.find(p => p.topic_id === topic.topic_id);
    const eligible = progress.unlocked && data.student.diagnostic_completed;
    const card = node('article', undefined, 'topic-card');
    const top = node('div', undefined, 'topic-top');
    top.append(node('span',String(topic.topic_id).padStart(2,'0'),'topic-number'));
    const label = progress.state === 'mastered' ? 'Mastered' : !progress.unlocked ? 'Locked' : progress.state === 'in_progress' ? 'In progress' : 'Not started';
    top.append(node('span',label,'badge'));
    card.append(top,node('h2',topic.title),node('p',topic.description));
    card.append(node('small',progress.best_score === null ? 'No score yet' : `Best score: ${progress.best_score}%`));
    if (!eligible) card.append(node('small', !data.student.diagnostic_completed ? 'Complete your diagnostic to begin.' : 'First master: ' + topic.prerequisites.map(topicName).join(', ')));
    card.append(button(progress.state === 'mastered' ? 'Revisit lesson →' : 'Lesson & practice →', () => openAssessment(topic.topic_id), !eligible));
    $('topics').append(card);
  }
  $('attempts').replaceChildren();
  if (!history.attempts.length) $('attempts').append(node('p','Your practice history will appear here.'));
  for (const attempt of history.attempts.slice(-6).reverse()) {
    const row = node('div', undefined, 'attempt-row');
    const detail = node('div'); detail.append(node('div',attempt.kind === 'diagnostic' ? 'Diagnostic assessment' : topicName(attempt.topic_id)),node('span',new Date(attempt.created_at).toLocaleString()));
    row.append(detail,node('strong',`${attempt.score}%`)); $('attempts').append(row);
  }
  show('dashboard');
}
async function openAssessment(topicId) {
  const data = await api(topicId === null ? '/diagnostic' : `/topics/${topicId}/quiz`);
  assessmentTopic = topicId; questions = data.questions;
  $('workspace-kind').textContent = topicId === null ? 'DISCOVER YOUR STARTING POINT' : 'LEARN & PRACTICE';
  $('workspace-title').textContent = topicId === null ? 'Your diagnostic assessment' : topicName(topicId);
  $('lesson').textContent = topicId === null ? 'Answer every question. Your results will help us find the right place to begin.' : topics.find(t => t.topic_id === topicId).lesson.content;
  $('questions').replaceChildren();
  questions.forEach((q, index) => {
    const field = node('fieldset'); field.append(node('legend',`${index + 1}. ${q.question}`));
    for (const [key,text] of Object.entries(q.options)) {
      const label = node('label');
      const radio = node('input'); radio.type = 'radio'; radio.name = String(q.question_id); radio.value = key; radio.required = true;
      label.append(radio,node('span',`${key}. ${text}`)); field.append(label);
    }
    $('questions').append(field);
  });
  notice(); show('workspace'); $('workspace-title').focus();
}
$('enroll').addEventListener('submit', event => {
  event.preventDefault();
  action(async () => {
    const data = await api('/students',{name:$('name').value});
    studentId = data.student.student_id;
    await refresh(); notice('Profile created. Start with your diagnostic assessment.');
  });
});
$('assessment').addEventListener('submit', event => {
  event.preventDefault();
  action(async () => {
    const form = new FormData($('assessment'));
    const answers = Object.fromEntries(questions.map(q => [String(q.question_id), form.get(String(q.question_id))]));
    const path = assessmentTopic === null ? `/students/${studentId}/diagnostic` : `/students/${studentId}/topics/${assessmentTopic}/quiz`;
    const result = await api(path, {answers});
    await refresh();
    notice(`Practice saved. You scored ${result.attempt.score}% (${result.attempt.correct_count} of ${result.attempt.question_count} correct). Your learning path is updated.`);
    window.scrollTo({top:0,behavior:'smooth'});
  });
});
$('back').addEventListener('click', () => { if (!busy) { notice(); show('dashboard'); } });
$('retake').addEventListener('click', () => action(() => openAssessment(null)));
$('switch').addEventListener('click', () => {
  if (busy) return;
  studentId = null; dashboard = null; $('name').value = ''; notice(); show('welcome');
});
action(async () => { topics = (await api('/topics')).topics; });
