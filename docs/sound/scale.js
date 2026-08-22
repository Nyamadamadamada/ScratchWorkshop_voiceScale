// 録音した1音から、ドレミファソラシドの8音をつくる。
// ../src/voice_scale/scale.py と同じ。

import { OUT_SR, fitLength, normalize, resample } from './audio.js';

export const C4 = 261.6256;
export const NOTE_SEC = 0.5;      // 四分音符の長さ。テンポ120にあたる
export const MAX_SOURCE_SEC = 1;  // ここまでを素材として使う

// ファイル名がそのまま Scratch の音の名前になるので、子どもが読める日本語にする
// name は画面に出す名前、file は WAV のファイル名。
//
// ファイル名はローマ字にする。日本語のままだと、UTF-8 のフラグを見ない古い
// 展開ツールに当たったとき Windows で文字化けする。会場のパソコンはレンタルで
// 中身を選べないので、危ない橋は渡らない。
export const NOTES = [
  { name: 'ド', file: 'do', semitone: 0 },
  { name: 'レ', file: 're', semitone: 2 },
  { name: 'ミ', file: 'mi', semitone: 4 },
  { name: 'ファ', file: 'fa', semitone: 5 },
  { name: 'ソ', file: 'so', semitone: 7 },
  { name: 'ラ', file: 'ra', semitone: 9 },
  { name: 'シ', file: 'si', semitone: 11 },
  { name: '高いド', file: 'do_high', semitone: 12 },
];

// 基準にできるオクターブの範囲。C2(65Hz) から C6(1046Hz) まで。
// 音程検出が 80〜1000Hz を見るので、いちばん近いオクターブを選べば
// 必ずこの範囲に収まる。つまりこれは安全弁であって、声を曲げる制限ではない。
export const MIN_OCTAVE = -2;
export const MAX_OCTAVE = 2;

// 基準になるドの周波数。いちばん近いオクターブを選ぶので、
// 変換の比は必ず 0.71〜1.41倍、つまり上下6半音以内に収まる。
//
// 範囲を狭めてはいけない。以前 C4〜C5 に絞っていたため、両端で声が壊れた。
// 大人の低い声（110Hz）は15半音も持ち上げられ、高い声（990Hz）は逆に
// ドが半オクターブ下がって「どーん」と鳴り、本人の声に聞こえなくなった。
export function baseFrequency(f0) {
  const octave = Math.min(MAX_OCTAVE, Math.max(MIN_OCTAVE, Math.round(Math.log2(f0 / C4))));
  return { hz: C4 * 2 ** octave, octave };
}

// 8音ぶんの波形を NOTES の順で返す。すべて同じ長さになる。
export async function build(x, f0, srcSr, noteSec = NOTE_SEC) {
  const source = x.subarray(0, Math.min(x.length, Math.round(srcSr * MAX_SOURCE_SEC)));
  const base = baseFrequency(f0);
  const length = Math.round(OUT_SR * noteSec);

  const sounds = [];
  for (const note of NOTES) {
    const target = base.hz * 2 ** (note.semitone / 12);
    // 直列に回す。8回ぶんの OfflineAudioContext を同時に開くと端末によっては失敗する
    // eslint-disable-next-line no-await-in-loop
    const shifted = await resample(source, srcSr, target / f0);
    sounds.push({
      name: note.name,
      file: note.file,
      samples: normalize(fitLength(shifted, length, OUT_SR)),
    });
  }
  return sounds;
}

// 録音した声にいちばん近い音の名前と、そのずれ[セント]を返す。
// 声が基準の外にあっても、オクターブを折り返してから比べる。110Hz なら「ラ」になる。
//
// 折り返す窓は4分音ぶん下げてある。基準のすぐ下にある声が「高いド」に
// 回り込むのを防ぐため。ドと高いドは同じ音なので、低いほうの「ド」で答える。
export function nearestNote(f0) {
  const base = baseFrequency(f0);
  const low = base.hz * 2 ** (-1 / 24);
  let folded = f0;
  while (folded < low) folded *= 2;
  while (folded >= low * 2) folded /= 2;

  const centsFrom = (note) => 1200 * Math.log2(folded / (base.hz * 2 ** (note.semitone / 12)));

  let closest = NOTES[0];
  for (const note of NOTES) {
    if (note.semitone >= 12) continue; // ドと高いドは同じ音。低いほうで答える
    if (Math.abs(centsFrom(note)) < Math.abs(centsFrom(closest))) closest = note;
  }
  return { name: closest.name, cents: centsFrom(closest) };
}
