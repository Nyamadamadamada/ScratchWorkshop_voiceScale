// docs/ の JavaScript に、Python 版と同じ入力を通して結果を返す。
// tests/test_parity.py から呼ばれる。
import { readFileSync } from 'node:fs';
import { trim } from '../../docs/audio.js';
import { judge } from '../../docs/check.js';
import { detect } from '../../docs/pitch.js';
import { baseFrequency, nearestNote } from '../../docs/scale.js';

const cases = JSON.parse(readFileSync(new URL('./cases.json', import.meta.url), 'utf8'));
const out = {};
for (const [name, c] of Object.entries(cases)) {
  const x = trim(Float32Array.from(c.samples));
  const p = detect(x, c.sr);
  out[name] = {
    trimmed: x.length,
    frames: p.frames,
    voicedRatio: p.voicedRatio,
    f0: Number.isFinite(p.f0) ? p.f0 : null,
    reasons: judge(x, c.sr, p),
    base: Number.isFinite(p.f0) ? baseFrequency(p.f0).base : null,
    near: Number.isFinite(p.f0) ? nearestNote(p.f0).name : null,
  };
}
process.stdout.write(JSON.stringify(out));
