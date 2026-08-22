// ZIP を組み立てる。
//
// 8ファイルを1つにまとめて渡すために使う。ばらばらに落とすと、ブラウザの
// 設定によっては保存先を8回聞かれる。
//
// 圧縮はしない（格納のみ）。WAV は縮まないうえ、圧縮を入れると実装が増える。
// ファイル名に日本語を使うので、UTF-8 のフラグを必ず立てる。立てないと
// Windows で展開したときに文字化けする。

const UTF8_NAME = 0x0800; // 汎用フラグの11ビット目。ファイル名が UTF-8 であることを示す
const STORE = 0; // 無圧縮

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i += 1) {
    let c = i;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[i] = c >>> 0;
  }
  return table;
})();

function crc32(bytes) {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i += 1) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

// MS-DOS 形式の日時。ZIP はこの形式しか持てない。
function dosTime(date) {
  const time = (date.getHours() << 11) | (date.getMinutes() << 5) | (date.getSeconds() >> 1);
  const day = ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
  return { time, day };
}

// files: [{ name: string, data: Uint8Array }]
export function createZip(files, date = new Date()) {
  const { time, day } = dosTime(date);
  const encoder = new TextEncoder();

  const entries = files.map((file) => ({
    name: encoder.encode(file.name),
    data: file.data,
    crc: crc32(file.data),
  }));

  const localSize = entries.reduce((n, e) => n + 30 + e.name.length + e.data.length, 0);
  const centralSize = entries.reduce((n, e) => n + 46 + e.name.length, 0);
  const buffer = new ArrayBuffer(localSize + centralSize + 22);
  const view = new DataView(buffer);
  const bytes = new Uint8Array(buffer);

  let at = 0;
  const u16 = (v) => {
    view.setUint16(at, v, true);
    at += 2;
  };
  const u32 = (v) => {
    view.setUint32(at, v, true);
    at += 4;
  };
  const raw = (v) => {
    bytes.set(v, at);
    at += v.length;
  };

  // ファイルごとの本体
  for (const entry of entries) {
    entry.offset = at;
    u32(0x04034b50);
    u16(20); // 展開に必要なバージョン
    u16(UTF8_NAME);
    u16(STORE);
    u16(time);
    u16(day);
    u32(entry.crc);
    u32(entry.data.length); // 圧縮後の大きさ。無圧縮なので同じ
    u32(entry.data.length);
    u16(entry.name.length);
    u16(0); // 拡張フィールドなし
    raw(entry.name);
    raw(entry.data);
  }

  // 目次
  const centralAt = at;
  for (const entry of entries) {
    u32(0x02014b50);
    u16(20); // 作成したバージョン
    u16(20);
    u16(UTF8_NAME);
    u16(STORE);
    u16(time);
    u16(day);
    u32(entry.crc);
    u32(entry.data.length);
    u32(entry.data.length);
    u16(entry.name.length);
    u16(0); // 拡張フィールドなし
    u16(0); // コメントなし
    u16(0); // ディスク番号
    u16(0); // 内部属性
    u32(0); // 外部属性
    u32(entry.offset);
    raw(entry.name);
  }

  // 目次の終わり。
  // 目次の大きさは、終端を書き始める前に控えておく。at はこのあと進むので、
  // 書きながら測ると終端そのものを数えてしまう。
  const centralSize2 = at - centralAt;
  u32(0x06054b50);
  u16(0); // ディスク番号
  u16(0); // 目次のあるディスク番号
  u16(entries.length);
  u16(entries.length);
  u32(centralSize2);
  u32(centralAt);
  u16(0); // コメントなし

  return new Blob([buffer], { type: 'application/zip' });
}
