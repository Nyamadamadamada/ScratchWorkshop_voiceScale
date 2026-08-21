// 波形の長さ・音量をそろえる処理。
// ../src/voice_scale/audio.py と同じ。

export const OUT_SR = 44100;
export const FADE_IN_MS = 10;
export const FADE_OUT_MS = 30;
export const PEAK_DB = -3;
export const TRIM_TOP_DB = 35;

// 前後の無音を削る。閾値はピーク音量からの相対値。
// 会場は子どもが十数人いて暗騒音が大きく、絶対値の閾値ではカットが効かない。
export function trim(x, topDb = TRIM_TOP_DB, frame = 1024, hop = 256) {
  if (x.length < frame) return x;
  const count = 1 + Math.floor((x.length - frame) / hop);
  const rms = new Float64Array(count);
  let maxRms = 0;
  for (let k = 0; k < count; k += 1) {
    let sum = 0;
    const base = k * hop;
    for (let i = 0; i < frame; i += 1) sum += x[base + i] * x[base + i];
    rms[k] = Math.sqrt(sum / frame);
    if (rms[k] > maxRms) maxRms = rms[k];
  }
  if (maxRms <= 0) return x.subarray(0, 0);

  const threshold = maxRms * 10 ** (-topDb / 20);
  let first = -1;
  let last = -1;
  for (let k = 0; k < count; k += 1) {
    if (rms[k] >= threshold) {
      if (first < 0) first = k;
      last = k;
    }
  }
  if (first < 0) return x.subarray(0, 0);
  return x.subarray(first * hop, Math.min(x.length, last * hop + frame));
}

// 長さを n サンプルちょうどにそろえる。
// Scratch の「音を鳴らす」は鳴り終わるまで次へ進まないため、
// 8音の長さがそろっていないとメロディのテンポが崩れる。
export function fitLength(x, n, sr) {
  const out = new Float32Array(n);
  out.set(x.subarray(0, Math.min(x.length, n)));

  if (x.length > n) {
    const fade = Math.min(Math.floor((sr * FADE_OUT_MS) / 1000), n);
    for (let i = 0; i < fade; i += 1) out[n - fade + i] *= 1 - i / (fade - 1);
  }
  const fadeIn = Math.min(Math.floor((sr * FADE_IN_MS) / 1000), n);
  for (let i = 0; i < fadeIn; i += 1) out[i] *= i / (fadeIn - 1);
  return out;
}

// ピークを peakDb にそろえる。
export function normalize(x, peakDb = PEAK_DB) {
  let peak = 0;
  for (let i = 0; i < x.length; i += 1) {
    const v = Math.abs(x[i]);
    if (v > peak) peak = v;
  }
  if (peak <= 0) return x;
  const gain = 10 ** (peakDb / 20) / peak;
  const out = new Float32Array(x.length);
  for (let i = 0; i < x.length; i += 1) out[i] = x[i] * gain;
  return out;
}
