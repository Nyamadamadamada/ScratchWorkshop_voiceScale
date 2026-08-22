// 波形を鳴らす。
//
// AudioContext を1つだけ持って使い回す。押すたびに作ると端末によっては
// すぐ上限に達して鳴らなくなる。

import { OUT_SR } from '../sound/audio.js';

export class Player {
  constructor() {
    this.ctx = null;
  }

  // 鳴らし始めた AudioBufferSourceNode を返す。
  // 呼び出し側は onended で「再生中」の見た目を戻す。
  async play(samples, sr = OUT_SR) {
    if (!this.ctx) {
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    }
    await this.ctx.resume();

    const buffer = this.ctx.createBuffer(1, samples.length, sr);
    buffer.copyToChannel(samples, 0);

    const source = this.ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(this.ctx.destination);
    source.start();
    return source;
  }
}
