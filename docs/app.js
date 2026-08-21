// 画面の制御。

import { OUT_SR, trim } from './audio.js';
import { MESSAGES, judge } from './check.js';
import { detect } from './pitch.js';
import { Recorder } from './recorder.js';
import { build, nearestNote } from './scale.js';
import { encodeWav } from './wav.js';

const RECORDING_TEXT = '声を出して！';
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

function showScreen(step) {
  for (const section of document.querySelectorAll('.screen')) {
    section.removeAttribute('data-active');
  }
  $(`screen-${step}`).setAttribute('data-active', '');
  window.scrollTo(0, 0);
}

function setMicState(state) {
  if (state) micButton.dataset.state = state;
  else delete micButton.dataset.state;
  micButton.disabled = Boolean(state);
}

// 音量に応じて輪を広げる。声が届いていることを見せるための表示。
//
// 平方根を通してから広げる。そのまま使うと少し大きい声ですぐ上限に張りつき、
// 声の大小が伝わらない。上限の2倍でボタンの外側まで届く。
const RING_MAX_SCALE = 2;

function animateRing() {
  if (micButton.dataset.state !== 'recording') return;
  const loudness = Math.min(1, Math.sqrt(recorder.level) * 2.2);
  const scale = 1 + (RING_MAX_SCALE - 1) * loudness;
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

// 8つの音のボタンを並べる。録音した声にいちばん近い音には目印をつける。
function renderKeys(box, near, onClick) {
  box.textContent = '';
  for (const note of notes) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'key';
    button.textContent = note.name;
    if (note.name === near) button.setAttribute('data-near', '');
    button.addEventListener('click', () => onClick(note, button));
    box.append(button);
  }
}

function renderResult(f0) {
  const near = nearestNote(f0);
  renderKeys($('result-keys'), near.name, async (note, button) => {
    button.setAttribute('data-playing', '');
    const source = await playNote(note.samples);
    source.onended = () => button.removeAttribute('data-playing');
  });
  $('near-note').innerHTML = `君の声に近い音は <b>${near.name}</b>`;

  for (const url of objectUrls) URL.revokeObjectURL(url);
  objectUrls = notes.map((note) => URL.createObjectURL(encodeWav(note.samples, OUT_SR)));
  $('download-hint').textContent =
    '「まとめてダウンロードしますか？」と出たら「許可」を押してね';
}

// 8つまとめて保存する。ブラウザが「複数ファイルのダウンロード」を一度だけ確認してくる。
async function downloadAll(button) {
  button.disabled = true;
  const original = button.textContent;
  for (let i = 0; i < notes.length; i += 1) {
    const link = document.createElement('a');
    link.href = objectUrls[i];
    link.download = `${notes[i].name}.wav`;
    document.body.append(link);
    link.click();
    link.remove();
    button.textContent = `保存中… ${i + 1} / ${notes.length}`;
    await sleep(250);
  }
  button.textContent = original;
  button.disabled = false;
  $('download-hint').textContent = 'ダウンロードフォルダに8つ入っているか見てみよう';
}

async function record() {
  recordError.textContent = '';

  // マイクの許可
  setMicState('asking');
  recordHint.textContent = 'マイクの使用を許可してね';
  try {
    await recorder.open();
  } catch (err) {
    setMicState(null);
    recordHint.textContent = 'マイクを押してね';
    recordError.textContent =
      err && err.name === 'NotAllowedError'
        ? 'マイクを使う許可を押してね'
        : 'マイクが見つかりません。先生を呼んでね';
    return;
  }

  // カウントダウン
  setMicState('counting');
  recordHint.textContent = '準備して…';
  for (let n = COUNTDOWN_SEC; n > 0; n -= 1) {
    countLabel.textContent = String(n);
    await sleep(1000);
  }

  // 録音
  setMicState('recording');
  recordHint.textContent = RECORDING_TEXT;
  recorder.start();
  animateRing();
  // 残り秒数はマイクの絵に重ねず、下の行に出す。重ねると読めない。
  countLabel.textContent = '';
  for (let left = RECORD_SEC; left > 0; left -= 1) {
    recordHint.textContent = `${RECORDING_TEXT}　あと ${left}秒`;
    await sleep(1000);
  }
  const raw = recorder.stop();
  const sr = recorder.sampleRate;

  // 判定
  setMicState('working');
  countLabel.textContent = '';
  recordHint.textContent = '作っています…';
  await sleep(0); // 画面を描き直させてから重い処理に入る

  const wave = trim(raw);
  const pitch = detect(wave, sr);
  const reasons = judge(wave, sr, pitch);

  setMicState(null);
  recordHint.textContent = 'マイクを押してね';

  if (reasons.length > 0) {
    recordError.innerHTML = reasons.map((r) => MESSAGES[r]).join('<br />');
    return;
  }

  notes = await build(wave, pitch.f0, sr);
  renderResult(pitch.f0);
  showScreen('result');
}

micButton.addEventListener('click', record);
$('download-all').addEventListener('click', (event) => downloadAll(event.currentTarget));

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
