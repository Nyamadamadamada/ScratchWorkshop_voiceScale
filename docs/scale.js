// 録音した1音から、ドレミファソラシドの8音をつくる。
// ../src/voice_scale/scale.py と同じ。

import { OUT_SR, fitLength, normalize } from './audio.js';

export const C4 = 261.6256;
export const NOTE_SEC = 0.5;      // 四分音符の長さ。テンポ120にあたる
export const MAX_SOURCE_SEC = 1;  // ここまでを素材として使う

// ファイル名がそのまま Scratch の音の名前になるので、子どもが読める日本語にする
export const NOTES = [
  ['ド', 0],
  ['レ', 2],
  ['ミ', 4],
  ['ファ', 5],
  ['ソ', 7],
  ['ラ', 9],
  ['シ', 11],
  ['高いド', 12],
];

// 基準になるドの周波数。C4 か C5 に必ず収める。
// 制限しないと、高い音源では基準が C6 まで上がり最高音が金切り声になる。
export function baseFrequency(f0) {
  const k = Math.min(1, Math.max(0, Math.round(Math.log2(f0 / C4))));
  return { base: C4 * 2 ** k, k };
}

// 再生速度を ratio 倍にして、出力サンプリングレートにそろえる。
// ratio が大きいほど音は高く、そして短くなる。
async function resample(samples, srcSr, ratio) {
  const length = Math.max(1, Math.ceil((OUT_SR * samples.length) / (srcSr * ratio)));
  const ctx = new OfflineAudioContext(1, length, OUT_SR);
  const buffer = ctx.createBuffer(1, samples.length, srcSr);
  buffer.copyToChannel(Float32Array.from(samples), 0);

  const source = ctx.createBufferSource();
  source.buffer = buffer;
  source.playbackRate.value = ratio;
  source.connect(ctx.destination);
  source.start();
  const rendered = await ctx.startRendering();
  return rendered.getChannelData(0);
}

// 8音ぶんの波形を返す。すべて同じ長さになる。
export async function build(x, f0, srcSr, noteSec = NOTE_SEC) {
  const source = x.subarray(0, Math.min(x.length, Math.round(srcSr * MAX_SOURCE_SEC)));
  const { base } = baseFrequency(f0);
  const length = Math.round(OUT_SR * noteSec);

  const notes = [];
  for (const [name, semitone] of NOTES) {
    const target = base * 2 ** (semitone / 12);
    // 直列に回す。8回ぶんの OfflineAudioContext を同時に開くと端末によっては失敗する
    // eslint-disable-next-line no-await-in-loop
    const shifted = await resample(source, srcSr, target / f0);
    notes.push({ name, samples: normalize(fitLength(shifted, length, OUT_SR)) });
  }
  return notes;
}
