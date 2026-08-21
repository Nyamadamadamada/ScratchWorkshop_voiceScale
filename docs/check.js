// 音階にできない音を弾く。
// ../src/voice_scale/check.py と同じ閾値。

export const MIN_PEAK = 0.01;
export const MIN_SEC = 0.15;
export const MIN_VOICED = 0.5;
export const MAX_SPREAD_CENTS = 150;

// 教室で何度も弾かれると子どもが萎縮する。原理的に無理なものだけ確実に止め、
// 多少音程が動く程度は通す。150セントはそのために緩めに取ってある。
export const MESSAGES = {
  quiet: 'もっと ちかくで こえを だしてね',
  short: 'もうすこし ながく こえを だしてね',
  unpitched: '「あー」や「にゃー」のように こえを のばしてね',
  unstable: 'おなじ たかさで こえを だしてね',
};

export function peakOf(x) {
  let peak = 0;
  for (let i = 0; i < x.length; i += 1) {
    const v = Math.abs(x[i]);
    if (v > peak) peak = v;
  }
  return peak;
}

// 弾く理由のキーを並べて返す。空なら音階にできる。
export function judge(x, sr, pitch) {
  const reasons = [];
  if (peakOf(x) < MIN_PEAK) reasons.push('quiet');
  if (x.length / sr < MIN_SEC) reasons.push('short');
  if (pitch.voicedRatio < MIN_VOICED || !Number.isFinite(pitch.f0)) reasons.push('unpitched');
  else if (pitch.spreadCents > MAX_SPREAD_CENTS) reasons.push('unstable');
  return reasons;
}
