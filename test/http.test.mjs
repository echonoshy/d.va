import test from 'node:test';
import assert from 'node:assert/strict';
import { access, mkdir, mkdtemp, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import { get } from 'node:http';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { createAppServer } from '../server/index.mjs';

const voices = [{ id: 'voice-a', name: '平静', language: 'zh', engine: 'test' }];
const script = [{ role: 'A', text: '你好。' }, { role: 'B', text: '我们开始吧。' }];
const sample = Buffer.from('ID3 podcast fixture');

async function fixture(t, options = {}) {
  const root = await mkdtemp(join(tmpdir(), 'dva-http-test-'));
  const audio = { getVoices: async () => voices, renderPodcast: async ({ outputPath }) => writeFile(outputPath, sample) };
  const server = createAppServer({ distDir: root, bindHost: '127.0.0.1', audio, apiKey: '', ...options });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(async () => {
    const closed = new Promise(resolve => server.close(resolve));
    server.closeAllConnections();
    await closed;
    await rm(root, { recursive: true, force: true });
  });
  return { root, origin: `http://127.0.0.1:${server.address().port}` };
}

function scriptPost({ topic = '月球', ...options } = {}) {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ topic }), ...options };
}

function renderForm(segments = script, selected = { A: 'voice-a', B: 'voice-a' }) {
  const form = new FormData();
  form.append('script', JSON.stringify(segments));
  form.append('voices', JSON.stringify(selected));
  return form;
}

async function waitUntilRemoved(path) {
  for (let n = 0; n < 50; n++) {
    try { await access(path); } catch (error) { if (error.code === 'ENOENT') return; throw error; }
    await delay(10);
  }
  assert.fail(`Temporary directory still exists: ${path}`);
}

test('lists voices and allows manual rendering without a script provider', async t => {
  let directory;
  const audio = {
    getVoices: async () => voices,
    async renderPodcast({ segments, voices: selected, musicPath, outputPath, signal }) {
      assert.deepEqual(segments, script);
      assert.deepEqual(selected, { A: 'voice-a', B: 'voice-a' });
      assert.equal(signal.aborted, false);
      assert.equal(await readFile(musicPath, 'utf8'), 'local upload');
      directory = dirname(outputPath);
      assert.equal(dirname(musicPath), directory);
      await writeFile(outputPath, sample);
    },
  };
  const { origin } = await fixture(t, { audio });
  assert.deepEqual(await (await fetch(`${origin}/api/voices`)).json(), { voices, scriptAvailable: false });
  const noKey = await fetch(`${origin}/api/script`, scriptPost());
  assert.equal(noKey.status, 503);
  assert.match((await noKey.json()).error, /DEEPSEEK_API_KEY/);
  const form = renderForm();
  form.append('music', new Blob(['local upload'], { type: 'audio/wav' }), 'theme.wav');
  const response = await fetch(`${origin}/api/render`, { method: 'POST', body: form });
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('content-type'), 'audio/mpeg');
  assert.deepEqual(Buffer.from(await response.arrayBuffer()), sample);
  await waitUntilRemoved(directory);
});

test('calls the configured DeepSeek model and validates structured responses', async t => {
  let calls = 0;
  const fetchImpl = async (url, init) => {
    assert.equal(url, 'https://api.deepseek.com/chat/completions');
    assert.equal(init.headers.Authorization, 'Bearer test-only');
    const body = JSON.parse(init.body);
    assert.equal(body.model, 'fixture');
    assert.equal(body.messages[1].content, '月球');
    assert.equal(body.response_format.type, 'json_object');
    const content = calls++ === 0 ? JSON.stringify({ segments: script }) : '{"segments":[]}';
    return Response.json({ choices: [{ message: { content } }] });
  };
  const { origin } = await fixture(t, { apiKey: 'test-only', model: 'fixture', fetchImpl });
  assert.equal((await (await fetch(`${origin}/api/voices`)).json()).scriptAvailable, true);
  const good = await fetch(`${origin}/api/script`, scriptPost());
  assert.equal(good.status, 200);
  assert.deepEqual(await good.json(), { segments: script });
  const bad = await fetch(`${origin}/api/script`, scriptPost());
  assert.equal(bad.status, 502);
  assert.match((await bad.json()).error, /脚本/);
});

test('rejects invalid forms, unavailable voices, oversized bodies and cross-site submissions', async t => {
  const { origin } = await fixture(t);
  const invalidMusic = renderForm();
  invalidMusic.set('music', 'path/to/local/file');
  const cases = [
    ['/render', { method: 'POST', body: renderForm([]) }, 400],
    ['/render', { method: 'POST', body: renderForm([{ role: 'C', text: '错误' }]) }, 400],
    ['/render', { method: 'POST', body: renderForm(script, { A: 'unknown', B: 'voice-a' }) }, 400],
    ['/render', { method: 'POST', body: invalidMusic }, 400],
    ['/render', { method: 'POST', body: 'unsupported' }, 415],
    ['/script', scriptPost({ topic: 'x'.repeat(501) }), 400],
    ['/script', scriptPost({ body: 'x'.repeat(9000) }), 413],
    ['/script', scriptPost({ headers: { Origin: 'https://example.org', 'Content-Type': 'application/json' } }), 403],
    ['/voices', { method: 'POST' }, 405],
  ];
  for (const [path, init, status] of cases) {
    const response = await fetch(`${origin}/api${path}`, init);
    assert.equal(response.status, status, path);
    assert.equal(typeof (await response.json()).error, 'string');
  }
});

test('releases aborted renders and removes temporary uploads after a timeout', async t => {
  let directory;
  const audio = {
    getVoices: async () => voices,
    async renderPodcast({ outputPath, signal }) {
      directory = dirname(outputPath);
      await delay(10_000, null, { signal });
    },
  };
  const { origin } = await fixture(t, { audio, timeouts: { render: 400, voices: 1000, script: 1000 } });
  const response = await fetch(`${origin}/api/render`, { method: 'POST', body: renderForm() });
  assert.equal(response.status, 504);
  await waitUntilRemoved(directory);
});

test('limits concurrent renders and admits new work once a render finishes', async t => {
  const ready = Promise.withResolvers();
  const gate = Promise.withResolvers();
  const directories = [];
  let started = 0;
  const audio = {
    getVoices: async () => voices,
    async renderPodcast({ outputPath }) {
      directories.push(dirname(outputPath));
      if (++started === 2) ready.resolve();
      await gate.promise;
      await writeFile(outputPath, sample);
    },
  };
  const { origin } = await fixture(t, { audio });
  const send = () => fetch(`${origin}/api/render`, { method: 'POST', body: renderForm() });
  const first = send(), second = send();
  try {
    await ready.promise;
    assert.equal((await send()).status, 429);
  } finally { gate.resolve(); }
  for (const response of await Promise.all([first, second])) {
    assert.equal(response.status, 200);
    await response.arrayBuffer();
  }
  await Promise.all(directories.map(waitUntilRemoved));
  assert.equal((await send()).status, 200);
});

test('returns public voice-engine diagnostics while hiding internal error details', async t => {
  const failure = new Error('sensitive internal path');
  failure.publicMessage = '请安装 FFmpeg 后重新启动。';
  const audio = { getVoices: async () => { throw failure; } };
  const { origin } = await fixture(t, { audio });
  const response = await fetch(`${origin}/api/voices`);
  assert.equal(response.status, 502);
  assert.deepEqual(await response.json(), { error: failure.publicMessage });
  delete failure.publicMessage;
  const hidden = await fetch(`${origin}/api/voices`);
  assert.doesNotMatch((await hidden.json()).error, /sensitive/);
});

test('accepts only local API hosts by default and respects an explicit deployment bind host', async t => {
  function statusWithHost(origin, host) {
    return new Promise((resolve, reject) => {
      get(`${origin}/api/voices`, { headers: { Host: host, Origin: `http://${host}` } }, res => {
        res.resume();
        resolve(res.statusCode);
      }).on('error', reject);
    });
  }
  const local = await fixture(t);
  assert.equal(await statusWithHost(local.origin, 'localhost:5173'), 200);
  assert.equal(await statusWithHost(local.origin, 'studio.example.test'), 403);
  const deployment = await fixture(t, { bindHost: '0.0.0.0' });
  assert.equal(await statusWithHost(deployment.origin, 'studio.example.test'), 200);
});

test('serves built assets and refuses symlinks outside the distribution directory', async t => {
  const { root, origin } = await fixture(t);
  await writeFile(join(root, 'index.html'), '<main>播客</main>');
  await mkdir(join(root, 'assets'));
  for (const filename of ['app.js', 'app.css', 'chunk-8a64f19c.js', 'font-Q7AMN2RX.woff2']) await writeFile(join(root, 'assets', filename), 'test');
  await symlink(process.execPath, join(root, 'outside'));
  const page = await fetch(origin);
  assert.match(page.headers.get('content-type'), /text\/html/);
  assert.equal(await page.text(), '<main>播客</main>');
  assert.equal((await fetch(`${origin}/outside`)).status, 404);
  const head = await fetch(origin, { method: 'HEAD' });
  assert.equal(await head.text(), '');
  assert.equal((await fetch(`${origin}/missing.js`)).status, 404);
  for (const filename of ['app.js', 'app.css']) {
    const response = await fetch(`${origin}/assets/${filename}`);
    assert.equal(response.headers.get('cache-control'), 'no-cache');
  }
  for (const filename of ['chunk-8a64f19c.js', 'font-Q7AMN2RX.woff2']) {
    const hashed = await fetch(`${origin}/assets/${filename}`);
    assert.match(hashed.headers.get('cache-control'), /immutable/);
  }
});
