// YIN法による基本周波数の検出。
// ../src/voice_scale/pitch.py と同じアルゴリズム。

export const WIN = 2048;      // 窓長
export const HOP = 512;       // ホップ
export const HALF = WIN / 2;  // 相関を取る幅
export const THRESHOLD = 0.15;
export const FMIN = 80;
export const FMAX = 1000;

// 1窓ぶんの [f0, d'(tau)の値] を返す。
function frameF0(x, offset, sr) {
  const tauMin = Math.max(1, Math.ceil(sr / FMAX));
  const tauMax = Math.min(HALF, Math.floor(sr / FMIN));
  if (tauMax <= tauMin) return [NaN, 1];

  const cumsq = new Float64Array(WIN + 1);
  for (let i = 0; i < WIN; i += 1) {
    const v = x[offset + i];
    cumsq[i + 1] = cumsq[i] + v * v;
  }
  const powerHead = cumsq[HALF];

  // 差分関数 d(tau) = Σ (x[i] - x[i+tau])^2
  const d = new Float64Array(tauMax + 1);
  for (let tau = 0; tau <= tauMax; tau += 1) {
    let r = 0;
    for (let i = 0; i < HALF; i += 1) r += x[offset + i] * x[offset + i + tau];
    d[tau] = powerHead + (cumsq[HALF + tau] - cumsq[tau]) - 2 * r;
  }
  d[0] = 0;

  // 累積平均正規化 d'(tau) = d(tau) * tau / Σ_{j=1..tau} d(j)
  const dp = new Float64Array(tauMax + 1).fill(1);
  let cum = 0;
  for (let tau = 1; tau <= tauMax; tau += 1) {
    cum += d[tau];
    if (cum > 0) dp[tau] = (d[tau] * tau) / cum;
  }

  // 閾値を最初に下回った谷を採る。なければ最小値
  let tau = -1;
  for (let t = tauMin; t <= tauMax; t += 1) {
    if (dp[t] < THRESHOLD) {
      let k = t;
      while (k + 1 <= tauMax && dp[k + 1] < dp[k]) k += 1;
      tau = k;
      break;
    }
  }
  if (tau < 0) {
    tau = tauMin;
    for (let t = tauMin; t <= tauMax; t += 1) if (dp[t] < dp[tau]) tau = t;
  }

  const confidence = dp[tau];

  // 放物線補間でサンプル間の位置を求める
  let tauF = tau;
  if (tau > tauMin && tau < tauMax) {
    const s0 = dp[tau - 1];
    const s1 = dp[tau];
    const s2 = dp[tau + 1];
    const denom = 2 * (s0 - 2 * s1 + s2);
    if (denom !== 0) tauF = tau + (s0 - s2) / denom;
  }
  if (tauF <= 0) return [NaN, 1];
  return [sr / tauF, confidence];
}

const median = (a) => {
  const s = Float64Array.from(a).sort();
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

// 波形全体から f0 と、判定に使う指標を求める。
export function detect(x, sr) {
  if (x.length < WIN) return { f0: NaN, voicedRatio: 0, spreadCents: Infinity, frames: 0 };

  const values = [];
  let frames = 0;
  for (let start = 0; start + WIN <= x.length; start += HOP) {
    const [f0, confidence] = frameF0(x, start, sr);
    frames += 1;
    if (confidence < THRESHOLD && f0 >= FMIN && f0 <= FMAX) values.push(f0);
  }
  if (values.length === 0) {
    return { f0: NaN, voicedRatio: 0, spreadCents: Infinity, frames };
  }

  const f0 = median(values);
  const spreadCents = median(values.map((v) => Math.abs(1200 * Math.log2(v / f0))));
  return { f0, voicedRatio: values.length / frames, spreadCents, frames };
}
