// マイクから生の波形を取る。

// 自動音量調整とノイズ除去は必ず切る。効いていると声の高さが揺れて検出できない。
const CONSTRAINTS = {
  audio: {
    echoCancellation: false,
    noiseSuppression: false,
    autoGainControl: false,
    channelCount: 1,
  },
};

export class Recorder {
  constructor() {
    this.ctx = null;
    this.stream = null;
    this.node = null;
    this.chunks = [];
    this.recording = false;
    this.level = 0; // 直前のフレームの音量。マイクの輪に使う
  }

  get sampleRate() {
    return this.ctx ? this.ctx.sampleRate : 0;
  }

  // マイクの許可を求めて配線する。以降は使い回す。
  async open() {
    if (this.ctx) {
      await this.ctx.resume();
      return;
    }
    this.stream = await navigator.mediaDevices.getUserMedia(CONSTRAINTS);
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    await this.ctx.resume();
    // addModule は index.html の場所を基準に解決する。このファイルからの
    // 相対で書くと外れるので、import.meta.url から組み立てる。
    await this.ctx.audioWorklet.addModule(new URL('./recorder-worklet.js', import.meta.url));

    this.node = new AudioWorkletNode(this.ctx, 'recorder');
    this.node.port.onmessage = (event) => {
      const chunk = event.data;
      let sum = 0;
      for (let i = 0; i < chunk.length; i += 1) sum += chunk[i] * chunk[i];
      this.level = Math.sqrt(sum / chunk.length);
      if (this.recording) this.chunks.push(chunk);
    };
    // Web Audio は出力へたどり着けるノードしか処理しない。
    // 出力につながないと process() が一度も呼ばれず、無音しか録れない。
    // 音量ゼロのゲインを挟んで、ハウリングさせずにグラフをつなぐ。
    const mute = this.ctx.createGain();
    mute.gain.value = 0;
    this.ctx.createMediaStreamSource(this.stream).connect(this.node);
    this.node.connect(mute).connect(this.ctx.destination);
  }

  start() {
    this.chunks = [];
    this.recording = true;
  }

  stop() {
    this.recording = false;
    const total = this.chunks.reduce((n, c) => n + c.length, 0);
    const out = new Float32Array(total);
    let offset = 0;
    for (const chunk of this.chunks) {
      out.set(chunk, offset);
      offset += chunk.length;
    }
    this.chunks = [];
    return out;
  }
}
