// マイクの生の波形を、そのままメインスレッドへ送る。
class RecorderProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (channel && channel.length) this.port.postMessage(channel.slice(0));
    return true;
  }
}
registerProcessor('recorder', RecorderProcessor);
