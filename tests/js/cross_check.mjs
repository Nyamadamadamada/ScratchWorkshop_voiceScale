// app/ の JavaScript に、Python 版と同じ入力を通して結果を返す。
// tests/test_parity.py から呼ばれる。
import { readFileSync } from 'node:fs';
import { fitLength, normalize, trim } from '../../app/audio.js';
import { judge } from '../../app/check.js';
import { detect } from '../../app/pitch.js';
import { baseFrequency, nearestNote } from '../../app/scale.js';

// 長さと音量をそろえたあと、鳴り終わりの振幅がどうなるか。
// フェードが抜けているとここに差が出る。
function fitted(x) {
  const out = normalize(fitLength(x, 22050, 44100));
  let last = 0;
  for (let i = 0; i < out.length; i += 1) if (Math.abs(out[i]) > 1e-4) last = i;
  return { length: out.length, end: Number(Math.abs(out[last]).toFixed(4)) };
}

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
    base: Number.isFinite(p.f0) ? baseFrequency(p.f0).hz : null,
    near: Number.isFinite(p.f0) ? nearestNote(p.f0).name : null,
    fitted: fitted(x),
  };
}
process.stdout.write(JSON.stringify(out));
