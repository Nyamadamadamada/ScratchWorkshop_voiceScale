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

// 基準にできるオクターブの範囲。C2(65Hz) から C5(523Hz) まで
export const MIN_OCTAVE = -2;
export const MAX_OCTAVE = 1;

// 基準になるドの周波数。いちばん近いオクターブを選ぶ。
// 声の高さをそのまま活かすため、変換の比は 0.52〜1.41倍に収まる。
//
// 上限だけ C5 で止める。止めないと高い音源で基準が C6 まで上がり、
// 最高音が2000Hzを超えて金切り声になる。
//
// 下限を切ってはいけない。以前 0 で切っていたため、大人の低い声（110Hz）が
// 15半音も持ち上げられ、まるで別人の声になっていた。
export function baseFrequency(f0) {
  const k = Math.min(MAX_OCTAVE, Math.max(MIN_OCTAVE, Math.round(Math.log2(f0 / C4))));
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

// 録音した声にいちばん近い音の名前と、そのずれ[セント]を返す。
// 声が基準の外にあっても、オクターブを折り返してから比べる。110Hz なら「ラ」になる。
//
// 折り返す窓は4分音ぶん下げてある。基準のすぐ下にある声が「高いド」に
// 回り込むのを防ぐため。ドと高いドは同じ音なので、低いほうの「ド」で答える。
export function nearestNote(f0) {
  const { base } = baseFrequency(f0);
  const low = base * 2 ** (-1 / 24);
  let folded = f0;
  while (folded < low) folded *= 2;
  while (folded >= low * 2) folded /= 2;

  let best = NOTES[0];
  let bestGap = Infinity;
  for (const note of NOTES) {
    if (note[1] >= 12) continue;
    const gap = Math.abs(1200 * Math.log2(folded / (base * 2 ** (note[1] / 12))));
    if (gap < bestGap) {
      bestGap = gap;
      best = note;
    }
  }
  return { name: best[0], cents: 1200 * Math.log2(folded / (base * 2 ** (best[1] / 12))) };
}
