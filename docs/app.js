// 画面の制御。

import { OUT_SR, trim } from './audio.js';
import { MESSAGES, judge } from './check.js';
import { detect } from './pitch.js';
import { Recorder } from './recorder.js';
import { build } from './scale.js';
import { encodeWav } from './wav.js';

const COUNTDOWN_SEC = 3;
const RECORD_SEC = 2; // 2秒録るが、使うのは最大1.0秒。
// カウントダウン終了から声が出るまで0.3〜0.5秒のラグがあり、
// さらに最高音は再生速度2倍で長さが半分になるため、元が1.0秒必要になる。

const $ = (id) => document.getElementById(id);
const micButton = $('mic-button');
const countLabel = $('count');
const recordHint = $('record-hint');
const recordError = $('record-error');
const ring = document.querySelector('.mic-ring');

const recorder = new Recorder();
let playbackCtx = null;
let notes = [];
let objectUrls = [];

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

// ふりがなをつけた表示名にする
const label = (name) => (name === '高いド' ? '<ruby>高<rt>たか</rt></ruby>いド' : name);

function showScreen(step) {
  for (const section of document.querySelectorAll('.screen')) {
    section.removeAttribute('data-active');
  }
  $(`screen-${step}`).setAttribute('data-active', '');
  for (const dot of document.querySelectorAll('.dots span')) {
    dot.toggleAttribute('data-active', dot.dataset.step === step);
  }
}

function setMicState(state) {
  if (state) micButton.dataset.state = state;
  else delete micButton.dataset.state;
  micButton.disabled = Boolean(state);
}

// 音量に応じて輪を広げる。声が届いていることを子どもに見せるための表示。
function animateRing() {
  if (micButton.dataset.state !== 'recording') return;
  const scale = 1 + Math.min(1.4, recorder.level * 14);
  ring.setAttribute('transform', `scale(${scale.toFixed(3)})`);
  requestAnimationFrame(animateRing);
}

async function playNote(samples) {
  if (!playbackCtx) {
    playbackCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  await playbackCtx.resume();
  const buffer = playbackCtx.createBuffer(1, samples.length, OUT_SR);
  buffer.copyToChannel(samples, 0);
  const source = playbackCtx.createBufferSource();
  source.buffer = buffer;
  source.connect(playbackCtx.destination);
  source.start();
  return source;
}

function renderListenKeys() {
  const box = $('listen-keys');
  box.textContent = '';
  notes.forEach((note, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'key';
    button.innerHTML = `<span>${label(note.name)}</span><span class="num">${index + 1}</span>`;
    button.addEventListener('click', async () => {
      button.setAttribute('data-playing', '');
      const source = await playNote(note.samples);
      source.onended = () => button.removeAttribute('data-playing');
    });
    box.append(button);
  });
}

function renderDownloadKeys() {
  const box = $('download-keys');
  box.textContent = '';
  for (const url of objectUrls) URL.revokeObjectURL(url);
  objectUrls = [];

  notes.forEach((note, index) => {
    const url = URL.createObjectURL(encodeWav(note.samples, OUT_SR));
    objectUrls.push(url);

    const link = document.createElement('a');
    link.className = 'key';
    link.href = url;
    link.download = `${note.name}.wav`;
    link.innerHTML = `<span>${label(note.name)}</span><span class="num">${index + 1}</span>`;
    link.addEventListener('click', () => link.setAttribute('data-done', ''));
    box.append(link);
  });
}

async function record() {
  recordError.textContent = '';

  // マイクの許可
  setMicState('asking');
  recordHint.textContent = 'マイクを つかっても いい？ を おしてね';
  try {
    await recorder.open();
  } catch (err) {
    setMicState(null);
    recordHint.textContent = 'マイクの えを おしてね';
    recordError.textContent =
      err && err.name === 'NotAllowedError'
        ? 'マイクを つかう きょかを おしてね'
        : 'マイクが みつかりません。せんせいを よんでね';
    return;
  }

  // カウントダウン
  setMicState('counting');
  recordHint.textContent = 'じゅんび して…';
  for (let n = COUNTDOWN_SEC; n > 0; n -= 1) {
    countLabel.textContent = String(n);
    await sleep(1000);
  }

  // 録音
  setMicState('recording');
  recordHint.textContent = 'こえを だして！';
  recorder.start();
  animateRing();
  for (let left = RECORD_SEC; left > 0; left -= 1) {
    countLabel.textContent = `あと ${left}`;
    await sleep(1000);
  }
  const raw = recorder.stop();
  const sr = recorder.sampleRate;

  // 判定
  setMicState('working');
  countLabel.textContent = '';
  recordHint.textContent = 'つくって います…';
  await sleep(0); // 画面を描き直させてから重い処理に入る

  const wave = trim(raw);
  const pitch = detect(wave, sr);
  const reasons = judge(wave, sr, pitch);

  setMicState(null);
  recordHint.textContent = 'マイクの えを おしてね';

  if (reasons.length > 0) {
    recordError.innerHTML = reasons.map((r) => MESSAGES[r]).join('<br />');
    return;
  }

  notes = await build(wave, pitch.f0, sr);
  renderListenKeys();
  renderDownloadKeys();
  showScreen('listen');
}

micButton.addEventListener('click', record);

for (const button of document.querySelectorAll('[data-goto]')) {
  button.addEventListener('click', () => showScreen(button.dataset.goto));
}

showScreen('record');

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js', { scope: './' }).catch(() => {
      // 登録できなくてもアプリ自体は動く
    });
  });
}
