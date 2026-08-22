// 録音1回ぶんの成果物。
//
// 8音と、変換する前の声をまとめて持つ。ダウンロード用の object URL を
// 抱えるので、録り直すときは dispose() で捨てる。

import { OUT_SR } from './audio.js';
import { nearestNote } from './scale.js';
import { encodeWav } from './wav.js';

const DOWNLOAD_INTERVAL_MS = 250; // 続けざまに落とすとブラウザが取りこぼす

export class SoundSet {
  // sounds: scale.js の build() が返す [{name, samples}]
  // original: 変換する前の録音 {samples, sr}
  constructor(sounds, original, f0) {
    this.sounds = sounds;
    this.original = original;
    this.nearest = nearestNote(f0);
    this.urls = sounds.map((sound) => URL.createObjectURL(encodeWav(sound.samples, OUT_SR)));
  }

  // 8つまとめて保存する。ブラウザは「複数ファイルのダウンロード」を一度だけ確認してくる。
  async downloadAll(onProgress) {
    for (let i = 0; i < this.sounds.length; i += 1) {
      const link = document.createElement('a');
      link.href = this.urls[i];
      link.download = `${this.sounds[i].name}.wav`;
      document.body.append(link);
      link.click();
      link.remove();
      if (onProgress) onProgress(i + 1, this.sounds.length);
      await new Promise((done) => setTimeout(done, DOWNLOAD_INTERVAL_MS));
    }
  }

  dispose() {
    for (const url of this.urls) URL.revokeObjectURL(url);
    this.urls = [];
  }
}
