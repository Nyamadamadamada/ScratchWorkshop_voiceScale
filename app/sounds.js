// 録音1回ぶんの成果物。8音と、変換する前の声をまとめて持つ。

import { OUT_SR } from './audio.js';
import { nearestNote } from './scale.js';
import { encodeWav } from './wav.js';
import { createZip } from './zip.js';

export const ZIP_NAME = '音階.zip';

// ダウンロードが始まる前に URL を捨てると、端末によっては失敗する
const REVOKE_DELAY_MS = 10000;

export class SoundSet {
  // sounds: scale.js の build() が返す [{name, samples}]
  // original: 変換する前の録音 {samples, sr}
  constructor(sounds, original, f0) {
    this.sounds = sounds;
    this.original = original;
    this.nearest = nearestNote(f0);
  }

  // 8つを1つの ZIP にまとめて保存する。
  //
  // ばらばらに落とすと、ブラウザの設定によっては保存先を8回聞かれる。
  // まとめれば1回で済み、展開したときに8つが1つのフォルダにそろう。
  download() {
    const files = this.sounds.map((sound) => ({
      name: `${sound.name}.wav`,
      data: encodeWav(sound.samples, OUT_SR),
    }));

    const url = URL.createObjectURL(createZip(files));
    const link = document.createElement('a');
    link.href = url;
    link.download = ZIP_NAME;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), REVOKE_DELAY_MS);
  }
}
