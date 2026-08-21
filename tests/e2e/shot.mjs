// 画面の見た目を撮って書き出す。レイアウト崩れを目で確かめるために使う。
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const BASE = process.env.BASE_URL ?? 'http://localhost:8765/';
const OUT = process.argv[2] ?? '/tmp/vs_shot';
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome',
  args: ['--autoplay-policy=no-user-gesture-required'] });

for (const [tag, width, height] of [['pc', 1280, 900], ['narrow', 390, 844]]) {
  const ctx = await browser.newContext({ permissions: ['microphone'],
    viewport: { width, height }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = async () => {
      const ac = new AudioContext();
      const dest = ac.createMediaStreamDestination();
      const buf = ac.createBuffer(1, ac.sampleRate * 4, ac.sampleRate);
      const ch = buf.getChannelData(0);
      for (let i = 0; i < ch.length; i += 1) {
        const t = i / ac.sampleRate;
        let v = 0;
        for (let k = 1; k <= 5; k += 1) v += (1 / k) * Math.sin(2 * Math.PI * 300 * k * t);
        ch[i] = (0.6 * v) / 2.28;
      }
      const src = ac.createBufferSource();
      src.buffer = buf; src.loop = true; src.connect(dest); src.start();
      return dest.stream;
    };
  });
  await page.goto(BASE);
  await page.screenshot({ path: `${OUT}/${tag}-1-待機.png` });

  await page.click('#mic-button');
  await page.waitForFunction(() =>
    document.getElementById('mic-button').dataset.state === 'recording');
  await page.waitForTimeout(1100);
  await page.screenshot({ path: `${OUT}/${tag}-2-録音中.png` });

  await page.waitForSelector('#screen-result[data-active]', { timeout: 20000 });
  await page.screenshot({ path: `${OUT}/${tag}-3-確認と保存.png` });
  await ctx.close();
  console.log(`${tag} 撮影`);
}
await browser.close();
