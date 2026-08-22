// 画面の配線。音づくりそのものは pitch/check/audio/scale が受け持つ。
//
// このファイルがすることは3つ。
//   1. マイクのボタンから録音までの流れを進める
//   2. できた8音を画面に並べる
//   3. ダウンロードのボタンをつなぐ

import { trim } from './audio.js';
import { MESSAGES, judge } from './check.js';
import { detect } from './pitch.js';
import { Player } from './player.js';
import { Recorder } from './recorder.js';
import { build } from './scale.js';
import { SoundSet, ZIP_NAME } from './sounds.js';

const COUNTDOWN_SEC = 3;
const RECORD_SEC = 2;
// 2秒録るが、使うのは最大1.0秒。カウントダウン終了から声が出るまで
// 0.3〜0.5秒のラグがあり、さらに最高音は再生速度2倍で長さが半分になるため、
// 元が1.0秒必要になる。

const RING_MAX_SCALE = 2; // 音量が最大のときの輪の大きさ。ボタンの外まで届く
const RING_GAIN = 2.2; // 平方根を通したあとの効き。声の大小が伝わる強さに合わせた

const HINTS = {
  idle: 'マイクを押してね',
  asking: 'マイクの使用を許可してね',
  counting: '準備して…',
  recording: '声を出して！',
  working: '作っています…',
};
const DOWNLOAD_HINTS = {
  ready: `8つの音が ${ZIP_NAME} にまとまって保存されるよ`,
  done: `${ZIP_NAME} を開くと、8つの音が入っているよ`,
};
const MIC_ERRORS = {
  NotAllowedError: 'マイクを使う許可を押してね',
  default: 'マイクが見つかりません。先生を呼んでね',
};

const $ = (id) => document.getElementById(id);
const micButton = $('mic-button');
const countLabel = $('count');
const recordHint = $('record-hint');
const recordError = $('record-error');
const ring = document.querySelector('.mic-ring');
const downloadButton = $('download-all');

const recorder = new Recorder();
const player = new Player();
let soundSet = null;

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

// ── 画面 ────────────────────────────────────────────

function showScreen(name) {
  for (const section of document.querySelectorAll('.screen')) {
    section.removeAttribute('data-active');
  }
  $(`screen-${name}`).setAttribute('data-active', '');
  window.scrollTo(0, 0);
}

// 押している間だけ見た目を変える。鳴り終わったら戻す。
async function playWith(button, samples, sr) {
  button.setAttribute('data-playing', '');
  const source = await player.play(samples, sr);
  source.onended = () => button.removeAttribute('data-playing');
}

function renderSounds() {
  const box = $('result-keys');
  box.textContent = '';
  for (const sound of soundSet.sounds) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'key';
    button.textContent = sound.name;
    // 録音した声にいちばん近い音には目印をつける
    if (sound.name === soundSet.nearest.name) button.setAttribute('data-near', '');
    button.addEventListener('click', () => playWith(button, sound.samples));
    box.append(button);
  }
  $('near-note').innerHTML = `君の声に近い音は <b>${soundSet.nearest.name}</b>`;
  $('download-hint').textContent = DOWNLOAD_HINTS.ready;
}

// ── マイク ──────────────────────────────────────────

function setMicState(state) {
  if (state) micButton.dataset.state = state;
  else delete micButton.dataset.state;
  micButton.disabled = Boolean(state);
  recordHint.textContent = HINTS[state ?? 'idle'];
}

// 音量に応じて輪を広げる。声が届いていることを見せるための表示で、
// 輪が動かなければそのパソコンのマイクが壊れているとその場で分かる。
//
// 平方根を通してから広げる。そのまま使うと少し大きい声ですぐ上限に張りつき、
// 声の大小が伝わらない。
function animateRing() {
  if (micButton.dataset.state !== 'recording') return;
  const loudness = Math.min(1, Math.sqrt(recorder.level) * RING_GAIN);
  ring.setAttribute('transform', `scale(${(1 + (RING_MAX_SCALE - 1) * loudness).toFixed(3)})`);
  requestAnimationFrame(animateRing);
}

// ── 録音の流れ ──────────────────────────────────────

async function openMic() {
  setMicState('asking');
  try {
    await recorder.open();
    return true;
  } catch (err) {
    setMicState(null);
    recordError.textContent = MIC_ERRORS[err?.name] ?? MIC_ERRORS.default;
    return false;
  }
}

async function captureVoice() {
  setMicState('counting');
  for (let n = COUNTDOWN_SEC; n > 0; n -= 1) {
    countLabel.textContent = String(n);
    await sleep(1000);
  }

  setMicState('recording');
  recorder.start();
  animateRing();
  // 残り秒数はマイクの絵に重ねず、下の行に出す。重ねると読めない。
  countLabel.textContent = '';
  for (let left = RECORD_SEC; left > 0; left -= 1) {
    recordHint.textContent = `${HINTS.recording}　あと ${left}秒`;
    await sleep(1000);
  }
  return { samples: recorder.stop(), sr: recorder.sampleRate };
}

async function record() {
  recordError.textContent = '';
  if (!(await openMic())) return;

  const raw = await captureVoice();

  setMicState('working');
  countLabel.textContent = '';
  await sleep(0); // 画面を描き直させてから重い処理に入る

  const wave = trim(raw.samples);
  const pitch = detect(wave, raw.sr);
  const reasons = judge(wave, raw.sr, pitch);
  setMicState(null);

  if (reasons.length > 0) {
    recordError.innerHTML = reasons.map((reason) => MESSAGES[reason]).join('<br />');
    return;
  }

  soundSet = new SoundSet(
    await build(wave, pitch.f0, raw.sr),
    { samples: Float32Array.from(wave), sr: raw.sr },
    pitch.f0
  );
  renderSounds();
  showScreen('result');
}

// ── 配線 ────────────────────────────────────────────

micButton.addEventListener('click', record);

$('play-original').addEventListener('click', (event) => {
  if (!soundSet) return;
  playWith(event.currentTarget, soundSet.original.samples, soundSet.original.sr);
});

downloadButton.addEventListener('click', () => {
  if (!soundSet) return;
  soundSet.download();
  $('download-hint').textContent = DOWNLOAD_HINTS.done;
});

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
