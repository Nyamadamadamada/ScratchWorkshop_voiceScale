// 実ブラウザで画面1から画面3まで通す。
//
// マイクの代わりに既知の波形を getUserMedia へ流し込む。Chrome の偽マイク機能は
// 指定したファイルを再生してくれなかったため、こちらの方式にしている。
// 検証したいのは自分たちのコードなので、これで足りる。
//
//   npm test            # サーバーを立ててから実行する
//   python3 -m http.server -d docs 8765
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = process.env.BASE_URL ?? 'http://localhost:8765/';
const OUT = process.env.OUT_DIR ?? null;

// [名前, 波形を作る関数のソース, 期待する結果]
const CASES = [
  ['子どもの声 300Hz', { kind: 'tone', hz: 300, gain: 0.5 }, { pass: true, base: 261.6 }],
  ['高い声 784Hz', { kind: 'tone', hz: 784, gain: 0.5 }, { pass: true, base: 523.3 }],
  ['低い声 130Hz', { kind: 'tone', hz: 130.81, gain: 0.5 }, { pass: true, base: 261.6 }],
  ['ホワイトノイズ', { kind: 'noise', gain: 0.5 }, { pass: false, message: 'のばしてね' }],
  ['小さすぎる声', { kind: 'tone', hz: 300, gain: 0.003 }, { pass: false, message: 'ちかくで' }],
];

function makeSource(spec) {
  return (s) => {
    navigator.mediaDevices.getUserMedia = async () => {
      const ac = new AudioContext();
      const dest = ac.createMediaStreamDestination();
      const buf = ac.createBuffer(1, ac.sampleRate * 4, ac.sampleRate);
      const ch = buf.getChannelData(0);
      if (s.kind === 'noise') {
        for (let i = 0; i < ch.length; i += 1) ch[i] = s.gain * (Math.random() * 2 - 1);
      } else {
        for (let i = 0; i < ch.length; i += 1) {
          const t = i / ac.sampleRate;
          let v = 0;
          for (let k = 1; k <= 5; k += 1) v += (1 / k) * Math.sin(2 * Math.PI * s.hz * k * t);
          ch[i] = (s.gain * v) / 2.28;
        }
      }
      const src = ac.createBufferSource();
      src.buffer = buf;
      src.loop = true;
      src.connect(dest);
      src.start();
      return dest.stream;
    };
  };
}

const browser = await chromium.launch({
  channel: 'chrome',
  args: ['--autoplay-policy=no-user-gesture-required'],
});

let failed = 0;
for (const [title, spec, expect] of CASES) {
  const ctx = await browser.newContext({ permissions: ['microphone'] });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.addInitScript(makeSource(spec), spec);
  await page.goto(BASE);
  await page.click('#mic-button');

  const deadline = Date.now() + 25000;
  while (Date.now() < deadline) {
    if (await page.locator('#screen-listen[data-active]').count()) break;
    if ((await page.locator('#record-error').innerText()).trim()) break;
    await page.waitForTimeout(100);
  }

  const reached = Boolean(await page.locator('#screen-listen[data-active]').count());
  const message = (await page.locator('#record-error').innerText()).replace(/\s+/g, ' ').trim();
  const problems = [];

  if (reached !== expect.pass) {
    problems.push(expect.pass ? `画面2へ進めなかった (${message})` : '弾かれるはずが通った');
  }
  if (!expect.pass && expect.message && !message.includes(expect.message)) {
    problems.push(`文言が違う: ${message}`);
  }

  if (reached) {
    await page.click('[data-goto="download"]');
    const links = page.locator('#download-keys a.key');
    const count = await links.count();
    if (count !== 8) problems.push(`ファイルが ${count} 個`);

    const names = [];
    for (let i = 0; i < count; i += 1) names.push(await links.nth(i).getAttribute('download'));
    const want = ['ド', 'レ', 'ミ', 'ファ', 'ソ', 'ラ', 'シ', '高いド'].map((n) => `${n}.wav`);
    if (names.join() !== want.join()) problems.push(`名前が違う: ${names.join(' ')}`);

    if (OUT) {
      const dir = `${OUT}/${title.replace(/\s+/g, '_')}`;
      mkdirSync(dir, { recursive: true });
      for (let i = 0; i < count; i += 1) {
        const b64 = await page.evaluate(async (u) => {
          const v = new Uint8Array(await (await fetch(u)).arrayBuffer());
          let s = '';
          for (let k = 0; k < v.length; k += 1) s += String.fromCharCode(v[k]);
          return btoa(s);
        }, await links.nth(i).getAttribute('href'));
        writeFileSync(`${dir}/${names[i]}`, Buffer.from(b64, 'base64'));
      }
    }
  }

  if (errors.length) problems.push(`コンソールエラー: ${errors.join(' / ')}`);
  if (problems.length) failed += 1;
  console.log(`${problems.length ? '✗' : '○'} ${title}${problems.length ? `\n    ${problems.join('\n    ')}` : ''}`);
  await ctx.close();
}

await browser.close();
console.log(failed ? `\n${failed} 件 失敗` : '\nすべて通った');
process.exit(failed ? 1 : 0);
