import { execFile } from 'node:child_process';
import { createWriteStream } from 'node:fs';
import { mkdtemp, open, rename, rm, writeFile } from 'node:fs/promises';
import { basename, dirname, join, resolve } from 'node:path';
import { Readable, Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { promisify } from 'node:util';
import { getNeuralVoices, renderNeuralSegment } from './neural.mjs';

const execute = promisify(execFile);
const maxSegmentBytes = 48 * 1024 * 1024;

function deadline(signal, ms) {
  const timeout = AbortSignal.timeout(ms);
  return signal ? AbortSignal.any([signal, timeout]) : timeout;
}

function audioError(message, cause) {
  return Object.assign(new Error(message, { cause }), { publicMessage: message });
}

async function run(command, args, signal) {
  signal.throwIfAborted();
  try {
    const { stdout } = await execute(command, args, {
      signal, killSignal: 'SIGKILL', maxBuffer: 512 * 1024, windowsHide: true,
    });
    return stdout;
  } catch (cause) {
    signal.throwIfAborted();
    const tool = command === (process.env.FFMPEG_PATH || 'ffmpeg') ? 'FFmpeg' : basename(command);
    let message = `${tool} 处理音频失败，请检查语音或背景音乐是否可播放。`;
    if (cause.code === 'ENOENT' || cause.code === 'EACCES') {
      message = tool === 'FFmpeg' ? '无法启动 FFmpeg，请安装 FFmpeg 或将 FFMPEG_PATH 设为可执行文件路径。'
        : `无法启动 ${tool}，请安装系统语音引擎或配置本地模型。`;
    }
    throw Object.assign(audioError(message, cause), { code: cause.code });
  }
}

function apiVoices() {
  apiUrl();
  const voices = (process.env.DVA_TTS_VOICES || 'alloy,onyx').split(',').map(s => s.trim()).filter(Boolean);
  if (!voices.length) throw audioError('请在 DVA_TTS_VOICES 中填写至少一个语音服务支持的声线 ID。');
  return [...new Set(voices)].map(name => ({ id: `api:${name}`, name, language: 'und', engine: 'api' }));
}

async function systemVoices(signal) {
  if (process.platform === 'darwin') {
    const lines = await run('say', ['-v', '?'], signal);
    const voices = [];
    for (const line of lines.split('\n')) {
      const match = line.match(/^(.+?)\s+([a-z]{2,3}[_-][A-Za-z_0-9-]+)\s+#/);
      if (match) {
        const name = match[1].trim();
        voices.push({ id: `say:${name}`, name, language: match[2].replaceAll('_', '-'), engine: 'say' });
      }
    }
    return voices;
  }
  for (const engine of ['espeak-ng', 'espeak']) {
    let lines;
    try {
      lines = await run(engine, ['--voices'], signal);
    } catch (error) {
      if (error.code === 'ENOENT') continue;
      throw error;
    }
    const voices = [];
    const languages = new Set();
    for (const line of lines.split('\n')) {
      // eSpeak columns start with priority, language, age/gender and voice name.
      const match = line.match(/^\s*\d+\s+([\w-]+)\s+\S+\s+(\S+)/);
      if (!match) continue;
      const [, language, label] = match;
      if (languages.has(language)) continue;
      languages.add(language);
      const name = label.replaceAll('_', ' ');
      voices.push({ id: `${engine}:${language}`, name, language, engine });
      voices.push({ id: `${engine}:${language}+f3`, name: `${name} (F3)`, language, engine });
    }
    return voices;
  }
  return [];
}

function rank(voice) {
  if (/^(zh-CN|zh$|cmn)/i.test(voice.language)) return /^Tingting/i.test(voice.name) ? 0 : 1;
  if (/^(zh|yue)/i.test(voice.language)) return 2;
  return /^en\b/i.test(voice.language) ? 3 : 4;
}

export async function getVoices({ signal } = {}) {
  signal?.throwIfAborted();
  if (process.env.DVA_TTS_BASE_URL) return apiVoices();
  const neural = await getNeuralVoices().catch(cause => {
    throw audioError('无法加载中文语音模型，请检查 DVA_MODEL_DIR 并运行 npm run model:install。', cause);
  });
  let local;
  try {
    local = await systemVoices(deadline(signal, 10_000));
  } catch (error) {
    signal?.throwIfAborted();
    if (!neural.length) throw error;
    local = [];
  }
  const unique = [...new Map(local.map(voice => [voice.id, voice])).values()];
  return [...neural, ...unique.sort((a, b) => rank(a) - rank(b))];
}

function apiUrl() {
  try {
    const base = new URL(process.env.DVA_TTS_BASE_URL);
    if (['http:', 'https:'].includes(base.protocol) && !base.search && !base.hash) {
      return new URL('audio/speech', base.href.replace(/\/+$/, '') + '/');
    }
  } catch { /* Report a configuration hint without disclosing the supplied URL. */ }
  throw audioError('DVA_TTS_BASE_URL 需要有效的 HTTP(S) 地址，例如 http://127.0.0.1:8000/v1。');
}

async function fetchSpeech(text, voice, outputPath, signal) {
  const url = apiUrl();
  const headers = { 'Content-Type': 'application/json' };
  if (process.env.DVA_TTS_API_KEY) headers.Authorization = `Bearer ${process.env.DVA_TTS_API_KEY}`;
  let response;
  try {
    response = await fetch(url, {
      method: 'POST', headers, signal, redirect: 'error',
      body: JSON.stringify({ model: process.env.DVA_TTS_MODEL || 'tts-1', input: text, voice, response_format: 'wav' }),
    });
  } catch {
    signal.throwIfAborted();
    throw audioError('无法连接语音服务，请检查 DVA_TTS_BASE_URL。');
  }
  if (!response.ok || !response.body) {
    await response.body?.cancel();
    throw audioError(`语音服务请求失败（HTTP ${response.status}），请检查模型、声线和服务端密钥。`);
  }
  let bytes = 0;
  const limit = new Transform({
    transform(chunk, encoding, callback) {
      bytes += chunk.length;
      if (bytes > maxSegmentBytes) callback(audioError('语音服务返回的音频过大，请缩短单段对白。'));
      else callback(null, chunk);
    },
  });
  await pipeline(Readable.fromWeb(response.body), limit, createWriteStream(outputPath, { mode: 0o600 }), { signal });
}

async function synthesize(text, voice, directory, signal) {
  const wav = join(directory, 'speech.wav');
  if (voice.id.startsWith('neural:')) {
    try { await renderNeuralSegment({ text, voiceId: voice.id, outputPath: wav, signal }); }
    catch (cause) {
      signal.throwIfAborted();
      throw audioError('本地中文语音合成失败，请检查模型文件并确认对白包含中文。', cause);
    }
    return wav;
  }
  if (voice.engine === 'api') {
    await fetchSpeech(text, voice.name, wav, signal);
    return wav;
  }
  const input = join(directory, 'speech.txt');
  await writeFile(input, text, 'utf8');
  if (voice.engine === 'say') {
    const aiff = join(directory, 'speech.aiff');
    await run('say', ['-v', voice.name, '-o', aiff, '-f', input], signal);
    return aiff;
  }
  const name = voice.id.slice(voice.engine.length + 1);
  await run(voice.engine, ['-b', '1', '-v', name, '-w', wav, '-f', input], signal);
  return wav;
}

// Pin the demuxer for uploaded music and provider responses. A playlist cannot
// make FFmpeg read a URL or an unrelated local file through format autodetection.
async function audioInput(file) {
  const handle = await open(file, 'r');
  const head = Buffer.alloc(16);
  try { await handle.read(head, 0, head.length, 0); }
  finally { await handle.close(); }
  const tag = head.toString('latin1');
  let format;
  if (/^(RIFF|RF64)....WAVE/s.test(tag)) format = 'wav';
  else if (/^FORM....(?:AIFF|AIFC)/s.test(tag)) format = 'aiff';
  else if (tag.startsWith('ID3')) format = 'mp3';
  else if (head[0] === 0xff && (head[1] & 0xe0) === 0xe0) format = (head[1] & 0x06) ? 'mp3' : 'aac';
  else if (tag.startsWith('OggS')) format = 'ogg';
  else if (tag.startsWith('fLaC')) format = 'flac';
  else if (tag.slice(4, 8) === 'ftyp') format = 'mov';
  else if (head.readUInt32BE() === 0x1a45dfa3) format = 'matroska';
  else throw audioError('音频格式无法识别，请使用 MP3、WAV、M4A、AAC、Ogg、FLAC、AIFF 或 WebM');
  return ['-protocol_whitelist', 'file', '-f', format, '-i', file];
}

export async function renderPodcast({ segments, voices, musicPath, outputPath, signal: parentSignal }) {
  const signal = deadline(parentSignal, 180_000);
  if (!Array.isArray(segments) || !segments.length || segments.length > 40) throw new Error('播客需要 1–40 段对白');
  const available = new Map((await getVoices({ signal })).map(voice => [voice.id, voice]));
  let length = 0;
  for (const part of segments) {
    if (!['A', 'B'].includes(part?.role) || typeof part.text !== 'string' || !part.text.trim()) throw new Error('对白需要 A/B 角色和非空文本');
    const count = [...part.text].length;
    length += count;
    if (count > 1200 || length > 8000) throw new Error('对白长度超过限制');
    if (!available.has(voices?.[part.role])) throw new Error(`角色 ${part.role} 的声线不可用`);
  }
  const ffmpeg = process.env.FFMPEG_PATH || 'ffmpeg';
  await run(ffmpeg, ['-version'], signal);
  const musicInput = musicPath ? await audioInput(resolve(musicPath)) : null;
  const baseArgs = ['-nostdin', '-hide_banner', '-loglevel', 'error', '-abort_on', 'empty_output', '-y'];
  const destination = resolve(outputPath);
  const directory = await mkdtemp(join(dirname(destination), '.dva-audio-'));
  try {
    const playlist = [];
    for (const [index, part] of segments.entries()) {
      signal.throwIfAborted();
      const source = await synthesize(part.text, available.get(voices[part.role]), directory, signal);
      const track = `segment-${index}.wav`;
      await run(ffmpeg, [...baseArgs, ...await audioInput(source), '-map', '0:a:0', '-ac', '1', '-ar', '24000',
        '-c:a', 'pcm_s16le', join(directory, track)], signal);
      await rm(source);
      playlist.push(`file '${track}'`);
    }
    const list = join(directory, 'segments.txt');
    await writeFile(list, playlist.join('\n') + '\n');
    const args = [...baseArgs, '-protocol_whitelist', 'file', '-f', 'concat', '-safe', '1', '-i', list];
    if (musicInput) {
      args.push('-stream_loop', '-1', ...musicInput, '-filter_complex',
        '[1:a:0]volume=0.10[music];[0:a:0][music]amix=inputs=2:duration=first:normalize=0[out]', '-map', '[out]');
    } else args.push('-map', '0:a:0');
    const mp3 = join(directory, 'podcast.mp3');
    await run(ffmpeg, [...args, '-map_metadata', '-1', '-map_chapters', '-1', '-ac', '1', '-ar', '24000',
      '-c:a', 'libmp3lame', '-b:a', '96k', mp3], signal);
    signal.throwIfAborted();
    await rename(mp3, destination);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}
