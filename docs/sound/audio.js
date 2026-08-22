// 波形の長さ・音量をそろえる処理。
// ../src/voice_scale/audio.py と同じ。

export const OUT_SR = 44100;
export const FADE_IN_MS = 10;
export const FADE_OUT_MS = 30;
export const PEAK_DB = -3;
export const TRIM_TOP_DB = 35;
const SILENCE = 1e-4; // これ以下は鳴っていないとみなす

// 再生速度を ratio 倍にして、書き出し用のレートにそろえる。
// ratio が大きいほど音は高く、そして短くなる。これが音階をつくる中心の処理で、
// サンプラーという楽器が昔からやっている方式と同じ。
//
// Python 版は numpy.interp で同じことをする。ブラウザではリサンプラーを
// 自前で書かず、OfflineAudioContext の playbackRate に任せる。
export async function resample(samples, srcSr, ratio) {
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

// 前後の無音を削る。閾値はピーク音量からの相対値。
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
  const end = Math.min(x.length, n);
  out.set(x.subarray(0, end));

  // 鳴り終わりの位置は、長さではなく値を見て決める。
  //
  // ブラウザのリサンプラーは音を引き伸ばすとき、末尾を十数ミリ秒とりこぼす。
  // 長さだけを見てフェードすると、その無音の上に掛かってしまい、実際の音は
  // 振幅を持ったまま切れる。結果「プチッ」と鳴り、音が途中で切られたように
  // 聞こえる。
  let sound = end;
  while (sound > 0 && Math.abs(out[sound - 1]) <= SILENCE) sound -= 1;

  const fadeOut = Math.min(Math.floor((sr * FADE_OUT_MS) / 1000), sound);
  if (fadeOut > 1) {
    for (let i = 0; i < fadeOut; i += 1) out[sound - fadeOut + i] *= 1 - i / (fadeOut - 1);
  }
  const fadeIn = Math.min(Math.floor((sr * FADE_IN_MS) / 1000), sound);
  if (fadeIn > 1) {
    for (let i = 0; i < fadeIn; i += 1) out[i] *= i / (fadeIn - 1);
  }
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
