import {createHash, timingSafeEqual} from 'node:crypto';
import { serveStudio, serveLegacy, stopStudio } from './studio.mjs';
import { createServer } from 'node:http';
import { createReadStream } from 'node:fs';
import { mkdtemp, realpath, rm, stat, writeFile } from 'node:fs/promises';
import { isIP } from 'node:net';
import { tmpdir } from 'node:os';
import { dirname, extname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { pipeline } from 'node:stream/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const MIB = 1024 * 1024;
const MAX_MUSIC = 20 * MIB;
const LIMITS = { render: 2, script: 4, voices: 8 };
const TIMEOUTS = { render: 180_000, script: 60_000, voices: 30_000 };
const STATIC_TYPES = {
  '.md': 'text/plain; charset=utf-8', '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.webmanifest': 'application/manifest+json',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp',
  '.ico': 'image/x-icon', '.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf',
};

class HttpError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

function json(res, status, value) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(value));
}

async function readLimited(stream, limit, status, message) {
  const chunks = [];
  let size = 0;
  // Keep the HTTP socket writable so a chunked upload can receive a 413 response.
  const source = stream.iterator?.({ destroyOnReturn: false }) ?? stream;
  for await (const chunk of source) {
    size += chunk.length;
    if (size > limit) throw new HttpError(status, message);
    chunks.push(chunk);
  }
  return Buffer.concat(chunks, size);
}

async function readBody(req, limit) {
  const message = '请求内容过大，请缩短文稿或使用较小的音乐文件。';
  if (Number(req.headers['content-length']) > limit) throw new HttpError(413, message);
  return readLimited(req, limit, 413, message);
}

function parseJSON(value, message) {
  try { return JSON.parse(value); } catch { throw new HttpError(400, message); }
}

function validateSegments(segments) {
  if (!Array.isArray(segments) || !segments.length || segments.length > 40) {
    throw new HttpError(400, '脚本需要包含 1 到 40 段对话。');
  }
  let length = 0;
  return segments.map(segment => {
    if (!segment || !['A', 'B'].includes(segment.role) || typeof segment.text !== 'string') {
      throw new HttpError(400, '每段对话需要 A 或 B 角色和文本。');
    }
    const text = segment.text.trim();
    const characters = [...text].length;
    length += characters;
    if (!characters || characters > 1200 || length > 8000) {
      throw new HttpError(400, '每段需填写 1 到 1200 字，全文最多 8000 字。');
    }
    return { role: segment.role, text };
  });
}

async function generateScript(topic, { apiKey, model, fetchImpl, signal }) {
  if (!apiKey) throw new HttpError(503, '未配置 DEEPSEEK_API_KEY。你可以手动编辑脚本并生成音频。');
  const response = await fetchImpl('https://api.deepseek.com/chat/completions', {
    method: 'POST', redirect: 'error', signal,
    headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model, response_format: { type: 'json_object' }, max_tokens: 3000,
      messages: [
        { role: 'system', content: '请围绕用户的主题创作中文双人播客对话。A 是主持人，B 是嘉宾，内容简洁自然，适合朗读。只返回 JSON，格式示例：{"segments":[{"role":"A","text":"今天我们聊什么？"},{"role":"B","text":"我们从一个故事说起。"}]}。输出 4 到 12 段，每段不超过 150 字。' },
        { role: 'user', content: topic },
      ],
    }),
  });
  if (!response.ok) {
    await response.body?.cancel();
    if ([401, 403].includes(response.status)) throw new HttpError(502, 'DeepSeek 拒绝了服务端密钥，请检查 DEEPSEEK_API_KEY。');
    if (response.status === 429) throw new HttpError(503, 'DeepSeek 暂时繁忙，请稍后重试。');
    throw new HttpError(502, 'DeepSeek 暂时无法生成脚本。你可以重试或手动编辑。');
  }
  try {
    const raw = await readLimited(response.body, 256 * 1024, 502, 'DeepSeek 响应过大。');
    const content = JSON.parse(raw).choices?.[0]?.message?.content;
    return validateSegments(JSON.parse(content).segments);
  } catch (error) {
    if (signal.aborted) throw error;
    throw new HttpError(502, 'DeepSeek 未返回可用的对话脚本，请重试或手动编辑。');
  }
}

function getField(form, name) {
  const values = form.getAll(name);
  if (values.length !== 1 || typeof values[0] !== 'string') {
    throw new HttpError(400, `表单需要一个 ${name} 文本字段。`);
  }
  return parseJSON(values[0], `表单字段 ${name} 需要有效的 JSON。`);
}

async function readRenderRequest(req) {
  const type = req.headers['content-type'] ?? '';
  if (!/^multipart\/form-data\s*;/i.test(type)) throw new HttpError(415, '请使用 multipart/form-data 提交音频任务。');
  const body = await readBody(req, MAX_MUSIC + 128 * 1024);
  let form;
  try { form = await new Response(body, { headers: { 'Content-Type': type } }).formData(); }
  catch { throw new HttpError(400, '无法读取上传表单，请重新选择文件。'); }
  const segments = validateSegments(getField(form, 'script'));
  const voices = getField(form, 'voices');
  if (!voices || typeof voices !== 'object' || Array.isArray(voices)) throw new HttpError(400, '请选择发言人的声音。');
  const files = form.getAll('music');
  if (files.length > 1 || (files.length && (typeof files[0] === 'string' || !files[0].size))) {
    throw new HttpError(400, '请上传一个非空的背景音乐文件。');
  }
  const music = files[0];
  if (music?.size > MAX_MUSIC) throw new HttpError(413, '背景音乐文件最多 20 MiB。');
  if (music && !music.type.startsWith('audio/')) {
    const accepted = ((!music.type || music.type === 'application/octet-stream') &&
      /\.(mp3|wav|m4a|mp4|aac|flac|oga|ogg|opus|aiff?|webm)$/i.test(music.name)) ||
      (music.type === 'video/mp4' && /\.(m4a|mp4)$/i.test(music.name)) ||
      (music.type === 'video/webm' && /\.webm$/i.test(music.name));
    if (!accepted) throw new HttpError(415, '请选择 MP3、WAV、M4A 等音频文件，或含音轨的 MP4、WebM 文件。');
  }
  return { segments, voices, music };
}

async function render(req, res, audio, signal) {
  const { segments, voices, music } = await readRenderRequest(req);
  signal.throwIfAborted();
  const available = new Set((await audio.getVoices({ signal })).map(voice => voice.id));
  if (!available.size) throw new HttpError(503, '没有可用的语音引擎，请先安装或配置播客声音。');
  const selected = {};
  for (const role of new Set(segments.map(segment => segment.role))) {
    if (!available.has(voices[role])) throw new HttpError(400, `角色 ${role} 的声音不可用，请重新选择。`);
    selected[role] = voices[role];
  }
  const directory = await mkdtemp(join(tmpdir(), 'dva-render-'));
  try {
    const outputPath = join(directory, 'podcast.mp3');
    const musicPath = music ? join(directory, 'music') : undefined;
    if (music) await writeFile(musicPath, Buffer.from(await music.arrayBuffer()), { signal });
    signal.throwIfAborted();
    await audio.renderPodcast({ segments, voices: selected, musicPath, outputPath, signal });
    signal.throwIfAborted();
    const { size } = await stat(outputPath);
    if (!size || size > 64 * MIB) throw new HttpError(502, '合成音频为空或过大，请缩短脚本后重试。');
    res.writeHead(200, { 'Content-Type': 'audio/mpeg', 'Content-Length': size,
      'Content-Disposition': 'attachment; filename="podcast.mp3"', 'Cache-Control': 'no-store' });
    await pipeline(createReadStream(outputPath), res, { signal });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

async function serveStatic(req, res, pathname, distDir) {
  if (!['GET', 'HEAD'].includes(req.method)) throw new HttpError(405, '请求方法不受支持。');
  const name = pathname === '/' ? 'index.html' : pathname.slice(1);
  if (name.split('/').some(part => part.startsWith('.')) || /[\\\0]/.test(name)) throw new HttpError(404, '文件不存在。');
  let path, size;
  try {
    const root = await realpath(distDir);
    path = await realpath(resolve(root, name));
    const local = relative(root, path);
    if (local === '..' || local.startsWith(`..${sep}`) || isAbsolute(local)) throw new Error();
    const file = await stat(path);
    if (!file.isFile()) throw new Error();
    size = file.size;
  } catch { throw new HttpError(404, pathname === '/' ? '尚未构建网页，请先运行 npm run build。' : '文件不存在。'); }
  // esbuild uses an eight-character base32 hash. Fixed bundle names must revalidate.
  const fingerprinted = name.startsWith('assets/') && /[.-](?:[0-9a-fA-F]{8,64}|[A-Z2-7]{8})\.[a-z0-9]+$/.test(name);
  res.writeHead(200, { 'Content-Type': STATIC_TYPES[extname(path)] ?? 'application/octet-stream', 'Content-Length': size,
    'Cache-Control': fingerprinted ? 'public, max-age=31536000, immutable' : 'no-cache' });
  if (req.method === 'HEAD') res.end();
  else await pipeline(createReadStream(path), res);
}

function isLoopback(hostname) {
  const host = hostname.toLowerCase().replace(/^\[|\]$/g, '').replace(/\.$/, '');
  return host === 'localhost' || host === '::1' || (isIP(host) === 4 && host.startsWith('127.'));
}

function checkApiOrigin(req, bindHost) {
  let host;
  try { host = new URL(`http://${req.headers.host ?? ''}`); } catch { /* Handled below. */ }
  if (!host || host.username || host.password || host.pathname !== '/' || host.search || host.hash) {
    throw new HttpError(400, '请求主机名无效。');
  }
  if (isLoopback(bindHost) && !isLoopback(host.hostname)) {
    throw new HttpError(403, '本地服务仅接受回环主机名。');
  }
  if (req.headers.origin) {
    let origin;
    try { origin = new URL(req.headers.origin); } catch { /* Reject opaque origins. */ }
    if (!origin || !['http:', 'https:'].includes(origin.protocol) ||
        origin.host !== new URL(`${origin.protocol}//${req.headers.host}`).host) {
      throw new HttpError(403, '仅允许同源页面使用此接口。');
    }
  }
  if (req.headers['sec-fetch-site'] === 'cross-site') throw new HttpError(403, '仅允许同源页面使用此接口。');
}

export function createAppServer({ distDir = join(ROOT, 'dist'), bindHost = process.env.HOST || '127.0.0.1', apiKey = process.env.DEEPSEEK_API_KEY?.trim(),
  model = process.env.DEEPSEEK_MODEL || 'deepseek-flash', fetchImpl = fetch, audio, timeouts = TIMEOUTS } = {}) {
  const active = { render: 0, script: 0, voices: 0 };
  const server = createServer({ requestTimeout: 45_000, headersTimeout: 15_000 }, async (req, res) => {
    res.setHeader('X-Content-Type-Options', 'nosniff');
    let slot, timer;
    const controller = new AbortController();
    res.once('close', () => { if (!res.writableEnded) controller.abort(); });
    try {
      let pathname;
      try { pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname); }
      catch { throw new HttpError(400, '请求路径无效。'); }
      if (process.env.DVA_AUTH) {
        const digest = value => createHash('sha256').update(value).digest();
        const expected = 'Basic ' + Buffer.from(process.env.DVA_AUTH).toString('base64');
        if (!timingSafeEqual(digest(req.headers.authorization || ''), digest(expected))) {
          res.setHeader('WWW-Authenticate', 'Basic realm="D.Va"');
          return json(res,401,{error:'请输入工作室的用户名和密码。'});
        }
      }
      if (process.env.DVA_ENABLE_API === '1' && (/^\/v[12]\//.test(pathname) || ['/docs','/openapi.json'].includes(pathname))) {
        checkApiOrigin(req,bindHost);
        return await serveLegacy(req,res,readBody);
      }
      if (!pathname.startsWith('/api/')) return await serveStatic(req, res, pathname, distDir);
      checkApiOrigin(req, bindHost);
      if (pathname === '/api/capabilities' && req.method === 'GET') return json(res, 200, {
        scriptAvailable: Boolean(apiKey), externalVoices: Boolean(process.env.DVA_TTS_BASE_URL)
      });
      if (pathname.startsWith('/api/studio/')) {
        try { await serveStudio(req, res, pathname, readBody); }
        catch (error) {
          if (res.headersSent) { res.destroy(); return; }
          if (error instanceof HttpError) throw error;
          return json(res, 503, { error: '语音工作台服务无法连接，请确认已运行 uv sync --frozen，并查看服务日志。' });
        }
        return;
      }
      const route = pathname.slice(5);
      if (!Object.hasOwn(LIMITS, route)) throw new HttpError(404, '接口不存在。');
      if (req.method !== (route === 'voices' ? 'GET' : 'POST')) throw new HttpError(405, '请求方法不受支持。');
      if (active[route] >= LIMITS[route]) throw new HttpError(429, '服务正在处理其他请求，请稍后重试。');
      active[route]++; slot = route;
      timer = setTimeout(() => controller.abort(new Error('timeout')), timeouts[route]);
      const { signal } = controller;
      if (route === 'script') {
        if (!/^application\/json(?:\s*;|$)/i.test(req.headers['content-type'] ?? '')) throw new HttpError(415, '请以 JSON 提交播客主题。');
        const topic = parseJSON(await readBody(req, 8192), '需要有效的 JSON。')?.topic;
        if (typeof topic !== 'string' || !topic.trim() || [...topic.trim()].length > 500) throw new HttpError(400, '请输入 1 到 500 字的播客主题。');
        const segments = await generateScript(topic.trim(), { apiKey, model, fetchImpl, signal });
        return json(res, 200, { segments });
      }
      const engine = audio ?? await import('./audio.mjs');
      if (route === 'voices') return json(res, 200, { voices: await engine.getVoices({ signal }), scriptAvailable: Boolean(apiKey) });
      await render(req, res, engine, signal);
    } catch (err) {
      if (res.destroyed) return;
      if (res.headersSent) { res.destroy(); return; }
      if (controller.signal.aborted) return json(res, 504, { error: '请求超时，请稍后重试或缩短脚本。' });
      const status = err instanceof HttpError ? err.status : 502;
      if (status === 413) res.setHeader('Connection', 'close');
      let message = '暂时无法完成请求，请检查服务配置后重试。';
      if (err instanceof HttpError) message = err.message;
      else if (['voices', 'render'].includes(slot) && typeof err?.publicMessage === 'string') message = err.publicMessage;
      json(res, status, { error: message });
    } finally {
      clearTimeout(timer);
      if (slot) active[slot]--;
    }
  });
  return server;
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  const port = Number(process.env.PORT || 8787);
  const host = process.env.HOST || '127.0.0.1';
  process.once("exit", stopStudio);
  for (const sig of ["SIGINT","SIGTERM"]) process.once(sig, () => { stopStudio(); process.exit(0); });
  createAppServer().listen(port, host, function () {
    console.log(`D.va listening on http://${host.includes(':') ? `[${host}]` : host}:${this.address().port}`);
  });
}
