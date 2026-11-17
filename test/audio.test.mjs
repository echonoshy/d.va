import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { promisify } from 'node:util';
import { getVoices, renderPodcast } from '../server/audio.mjs';
import { createAppServer } from '../server/index.mjs';

const execute = promisify(execFile);
const ffmpeg = process.env.FFMPEG_PATH || 'ffmpeg';

async function workspace(t) {
  const directory = await mkdtemp(join(tmpdir(), 'dva-audio-test-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  return directory;
}

function env(t, name, value) {
  const previous = process.env[name];
  if (value === undefined) delete process.env[name]; else process.env[name] = value;
  t.after(() => {
    if (previous === undefined) delete process.env[name]; else process.env[name] = previous;
  });
}

async function hasFFmpeg(t) {
  try { await execute(ffmpeg, ['-version']); return true; }
  catch (error) {
    if (error.code !== 'ENOENT') throw error;
    t.skip('FFmpeg is required for audio integration tests');
    return false;
  }
}

async function decode(file) {
  const { stdout } = await execute(ffmpeg, ['-loglevel', 'error', '-i', file, '-ac', '1',
    '-ar', '24000', '-f', 's16le', '-'], { encoding: 'buffer', maxBuffer: 16 * 1024 * 1024 });
  return stdout;
}

test('two system voices produce distinct speech; turns concatenate and short music loops', async t => {
  if (!await hasFFmpeg(t)) return;
  env(t, 'DVA_TTS_BASE_URL', undefined);
  env(t, 'DVA_MODEL_DIR', undefined);
  const found = (await getVoices()).filter(v => /^(say|espeak(-ng)?)$/.test(v.engine));
  if (found.length < 2) return t.skip('two native voices are required');
  const [first, second] = found;
  const text = /^zh|^cmn/.test(first.language) ? '大家好，欢迎收听今天的节目。' : 'Hello, welcome to our show.';
  const directory = await workspace(t);
  const voices = { A: first.id, B: second.id };
  const segments = [{ role: 'A', text }, { role: 'B', text }];
  const a = join(directory, 'a.mp3'), b = join(directory, 'b.mp3');
  await Promise.all([a, b].map((outputPath, i) =>
    renderPodcast({ voices, segments: [segments[i]], outputPath })));
  const [audioA, audioB] = await Promise.all([decode(a), decode(b)]);
  for (const pcm of [audioA, audioB]) {
    assert.ok(pcm.length > 12_000 && pcm.some(byte => byte !== 0));
  }
  assert.notDeepEqual(audioA, audioB);
  const plain = join(directory, 'plain.mp3'), mixed = join(directory, 'mixed.mp3');
  const music = join(directory, 'music');
  await execute(ffmpeg, ['-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=310:duration=0.1',
    '-f', 'wav', music]);
  await renderPodcast({ voices, segments, outputPath: plain });
  await renderPodcast({ voices, segments, musicPath: music, outputPath: mixed });
  const [dry, wet] = await Promise.all([decode(plain), decode(mixed)]);
  // Allow a few speech-engine timing differences between invocations.
  assert.ok(Math.abs(dry.length - audioA.length - audioB.length) < 12_000);
  assert.ok(Math.abs(wet.length - dry.length) < 12_000);
  assert.notDeepEqual(dry, wet);
  assert.deepEqual((await readdir(directory)).sort(), ['a.mp3', 'b.mp3', 'mixed.mp3', 'music', 'plain.mp3']);
});

test('compatible API receives each selected voice, failures and cancellation preserve the prior output', async t => {
  if (!await hasFFmpeg(t)) return;
  const directory = await workspace(t);
  const fixture = join(directory, 'fixture.wav');
  const samples = {};
  for (const [voice, frequency] of [['host', 200], ['guest', 800]]) {
    await execute(ffmpeg, ['-y', '-loglevel', 'error', '-f', 'lavfi', '-i', `sine=frequency=${frequency}:duration=0.15`, fixture]);
    samples[voice] = await readFile(fixture);
  }
  const calls = [];
  let status = 200, onHold;
  const provider = createServer(async (req, res) => {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const body = JSON.parse(Buffer.concat(chunks));
    calls.push({ url: req.url, authorization: req.headers.authorization, ...body });
    if (onHold) { onHold(); return; }
    res.writeHead(status, { 'content-type': 'audio/wav' }).end(samples[body.voice]);
  });
  await new Promise(resolve => provider.listen(0, '127.0.0.1', resolve));
  t.after(() => { provider.closeAllConnections(); return new Promise(resolve => provider.close(resolve)); });
  env(t, 'DVA_TTS_BASE_URL', `http://127.0.0.1:${provider.address().port}/v1`);
  env(t, 'DVA_TTS_VOICES', 'host,guest');
  env(t, 'DVA_TTS_API_KEY', 'test-key');
  env(t, 'DVA_TTS_MODEL', 'local-model');
  const [a, b] = await getVoices();
  const outputPath = join(directory, 'podcast.mp3');
  const job = {
    segments: [{ role: 'A', text: 'Hello.' }, { role: 'B', text: 'Good morning.' }],
    voices: { A: a.id, B: b.id }, outputPath,
  };
  await renderPodcast(job);
  assert.deepEqual(calls.map(c => [c.input, c.voice]), [['Hello.', 'host'], ['Good morning.', 'guest']]);
  assert.ok(calls.every(c => c.url === '/v1/audio/speech' && c.authorization === 'Bearer test-key'
    && c.model === 'local-model' && c.response_format === 'wav'));
  const original = await readFile(outputPath);
  const pcm = await decode(outputPath);
  function countCycles(start) {
    let count = 0;
    for (let i = start; i < start + 2400; i++) {
      if (pcm.readInt16LE(2 * i) <= 0 && pcm.readInt16LE(2 * i + 2) > 0) count++;
    }
    return count;
  }
  // The first 0.1-second window contains the host's 200 Hz test fixture,
  // the next window the guest's 800 Hz fixture, even after MP3 encoding.
  assert.ok(Math.abs(countCycles(480) - 20) <= 1);
  assert.ok(Math.abs(countCycles(4080) - 80) <= 1);
  await assert.rejects(renderPodcast({ ...job, voices: { A: 'missing' } }), /声线不可用/);
  const musicPath = join(directory, 'bad-music');
  await writeFile(musicPath, 'this is a text file');
  await assert.rejects(renderPodcast({ ...job, musicPath }), /音频格式/);
  status = 503;
  await assert.rejects(renderPodcast(job), /HTTP 503/);
  const controller = new AbortController();
  const received = new Promise(resolve => { onHold = resolve; });
  const pending = renderPodcast({ ...job, signal: controller.signal });
  await received;
  controller.abort();
  await assert.rejects(pending, { name: 'AbortError' });
  assert.deepEqual(await readFile(outputPath), original);
  assert.deepEqual((await readdir(directory)).sort(), ['bad-music', 'fixture.wav', 'podcast.mp3']);
});

test('HTTP reports actionable model-directory and missing-FFmpeg configuration errors', async t => {
  const directory = await workspace(t);
  env(t, 'DVA_MODEL_DIR', join(directory, 'missing-model'));
  env(t, 'DVA_TTS_BASE_URL', undefined);
  const app = createAppServer();
  await new Promise(resolve => app.listen(0, '127.0.0.1', resolve));
  t.after(() => { app.closeAllConnections(); return new Promise(resolve => app.close(resolve)); });
  const url = `http://127.0.0.1:${app.address().port}/api`;
  const listing = await fetch(url + '/voices');
  assert.equal(listing.status, 502);
  assert.match((await listing.json()).error, /DVA_MODEL_DIR/);
  // A missing encoder is detected before sending content to a remote model.
  process.env.DVA_TTS_BASE_URL = 'http://127.0.0.1:1/v1';
  env(t, 'DVA_TTS_VOICES', 'host,guest');
  env(t, 'FFMPEG_PATH', join(directory, 'missing-ffmpeg'));
  const payload = new FormData();
  payload.set('script', JSON.stringify([{ role: 'A', text: '一' }, { role: 'B', text: '二' }]));
  payload.set('voices', JSON.stringify({ A: 'api:host', B: 'api:guest' }));
  const result = await fetch(url + '/render', { method: 'POST', body: payload });
  assert.equal(result.status, 502);
  assert.match((await result.json()).error, /FFMPEG_PATH/);
});
