// pitch.js / check.js / audio.js が Python 版と同じ値を出すか確かめる。
// 同じ入力を tests/js/cases.json から読み、結果を JSON で返す。
import { readFileSync } from 'node:fs';
import { detect } from '../../docs/pitch.js';
import { judge } from '../../docs/check.js';
import { trim, fitLength, normalize } from '../../docs/audio.js';

const cases = JSON.parse(readFileSync(new URL('./cases.json', import.meta.url), 'utf8'));
const out = {};
for (const [name, c] of Object.entries(cases)) {
  const x = Float32Array.from(c.samples);
  const t = trim(x);
  const p = detect(t, c.sr);
  out[name] = {
    trimmed: t.length,
    f0: p.f0,
    voicedRatio: p.voicedRatio,
    spreadCents: p.spreadCents,
    frames: p.frames,
    reasons: judge(t, c.sr, p),
    fitted: fitLength(t, 22050, 44100).length,
    peak: Math.max(...normalize(t.subarray(0, 4096))).toFixed(4),
  };
}
process.stdout.write(JSON.stringify(out));
