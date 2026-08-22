// 実ブラウザで8音をつくり、WAV として書き出す。
//
// 見本音源づくりと、Python 側の検証の両方がこれを使う。ページに読み込ませて
// docs/sound/ をそのまま動かすので、当日子どもが動かすコードと同じものを試せる。
//
//   node tools/generate.mjs --file 素材/にゃー.mp3 --out 見本/
//   node tools/generate.mjs --tone 300 --out /tmp/x
//   node tools/generate.mjs --noise --out /tmp/x
//   node tools/generate.mjs --batch specs.json --out /tmp/x   まとめて（テスト用）
//
// まとめて渡すと、ブラウザを一度だけ立ち上げて全部処理する。テストのたびに
// Chrome を起動し直すと遅いため。
//
// マイクの代わりに、既知の波形を getUserMedia へ流し込む…のではなく、
// docs/sound/ のモジュールを直接呼ぶ。画面まわりを通さないぶん速く、
// 入力を厳密に決められる。画面ごと通した確認は tests/e2e/run.mjs が受け持つ。

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import { chromium } from 'playwright';

const BASE = process.env.BASE_URL ?? 'http://localhost:8761/';
const DEVICE_SR = 48000; // 多くのパソコンのマイクがこのレート

function parseArgs(argv) {
  const args = { gain: 0.6, sec: 1.0 };
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i].replace(/^--/, '');
    if (key === 'noise') {
      args.noise = true;
      i -= 1;
      continue;
    }
    args[key] = argv[i + 1];
  }
  return args;
}

const args = parseArgs(process.argv.slice(2));
if (!args.out) {
  console.error('--out が要ります');
  process.exit(2);
}

// 1件ぶんの指定をつくる。file は base64 にしてページへ渡す。
function toSpec(one) {
  return {
    id: one.id ?? (one.file ? basename(one.file) : (one.tone ?? 'noise')),
    sr: DEVICE_SR,
    hz: one.tone ? Number(one.tone) : null,
    noise: Boolean(one.noise),
    gain: Number(one.gain ?? 0.6),
    sec: Number(one.sec ?? 1.0),
    audio: one.file ? readFileSync(one.file).toString('base64') : null,
  };
}

const specs = args.batch
  ? JSON.parse(readFileSync(args.batch, 'utf8')).map(toSpec)
  : [toSpec(args)];

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage();
await page.goto(BASE);

const runOne = (spec) =>
  page.evaluate(async (spec) => {
  const { trim } = await import('./sound/audio.js');
  const { MESSAGES, judge } = await import('./sound/check.js');
  const { detect } = await import('./sound/pitch.js');
  const { baseFrequency, build, nearestNote } = await import('./sound/scale.js');
  const { encodeWav } = await import('./sound/wav.js');

  // 入力の波形をつくる
  let samples;
  let sr = spec.sr;
  if (spec.audio) {
    const bytes = Uint8Array.from(atob(spec.audio), (c) => c.charCodeAt(0));
    const ctx = new AudioContext();
    const buffer = await ctx.decodeAudioData(bytes.buffer);
    samples = buffer.getChannelData(0);
    sr = buffer.sampleRate;
  } else if (spec.noise) {
    samples = new Float32Array(Math.round(sr * spec.sec));
    for (let i = 0; i < samples.length; i += 1) samples[i] = spec.gain * (Math.random() * 2 - 1);
  } else {
    samples = new Float32Array(Math.round(sr * spec.sec));
    for (let i = 0; i < samples.length; i += 1) {
      const t = i / sr;
      let v = 0;
      for (let k = 1; k <= 5; k += 1) v += (1 / k) * Math.sin(2 * Math.PI * spec.hz * k * t);
      samples[i] = (spec.gain * v) / 2.28;
    }
  }

  // 当日と同じ順で通す
  const wave = trim(samples);
  const pitch = detect(wave, sr);
  const reasons = judge(wave, sr, pitch);
  if (reasons.length > 0) {
    return { ok: false, reasons, messages: reasons.map((r) => MESSAGES[r]) };
  }

  const base = baseFrequency(pitch.f0);
  const sounds = await build(wave, pitch.f0, sr);
  const toBase64 = (bytes) => {
    let s = '';
    for (let i = 0; i < bytes.length; i += 1) s += String.fromCharCode(bytes[i]);
    return btoa(s);
  };
  return {
    ok: true,
    sourceSec: wave.length / sr,
    f0: pitch.f0,
    voicedRatio: pitch.voicedRatio,
    spreadCents: pitch.spreadCents,
    base: base.hz,
    octave: base.octave,
    nearest: nearestNote(pitch.f0),
    files: sounds.map((sound) => ({
      name: sound.name,
      file: sound.file,
      wav: toBase64(encodeWav(sound.samples, 44100)),
    })),
  };
  }, spec);

let failed = 0;
for (const spec of specs) {
  const result = await runOne(spec);
  const dir = args.batch ? join(args.out, String(spec.id)) : args.out;
  mkdirSync(dir, { recursive: true });

  const report = { ...result, input: spec.id };
  if (result.ok) {
    for (const file of result.files) {
      writeFileSync(join(dir, `${file.file}.wav`), Buffer.from(file.wav, 'base64'));
    }
    report.files = result.files.map((f) => ({ name: f.name, file: f.file }));
    console.log(
      `${String(spec.id).padEnd(16)} ${result.f0.toFixed(1)}Hz  基準C${4 + result.octave}  ` +
        `近い音=${result.nearest.name}  → ${dir}`
    );
  } else {
    failed += 1;
    console.log(`${String(spec.id).padEnd(16)} 音階にできません: ${result.messages.join(' / ')}`);
  }
  writeFileSync(join(dir, 'report.json'), JSON.stringify(report, null, 2));
}

await browser.close();
process.exit(args.batch ? 0 : failed ? 1 : 0);
