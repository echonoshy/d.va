import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { getNeuralVoices, hasModel, modelDirectory, modelFiles, renderNeuralSegment } from '../server/neural.mjs';

const require = createRequire(import.meta.url);

async function workspace(t) {
  const path = await mkdtemp(join(tmpdir(), 'dva-neural-test-'));
  t.after(() => rm(path, { recursive: true, force: true }));
  return path;
}

test('AISHELL-3 requires the six non-empty regular files in a model directory', async t => {
  const expected = ['model.onnx', 'tokens.txt', 'lexicon.txt', 'phone.fst', 'date.fst', 'number.fst'];
  assert.deepEqual(modelFiles.toSorted(), expected.toSorted());
  const dir = await workspace(t);
  assert.equal(await hasModel(dir), false);
  for (const name of expected) await writeFile(join(dir, name), 'fixture');
  assert.equal(await hasModel(dir), true);
  for (const name of expected) {
    const file = join(dir, name);
    await rm(file);
    assert.equal(await hasModel(dir), false, `missing ${name}`);
    await writeFile(file, '');
    assert.equal(await hasModel(dir), false, `empty ${name}`);
    await rm(file);
    await mkdir(file);
    assert.equal(await hasModel(dir), false, `directory named ${name}`);
    await rm(file, { recursive: true });
    await writeFile(file, 'fixture');
  }
});

test('installed AISHELL-3 renders non-silent, distinct PCM for two Mandarin speakers', { timeout: 120_000 }, async t => {
  if (!await hasModel(modelDirectory())) return t.skip('Optional model is absent. Run npm run model:install to exercise CPU speech synthesis.');
  const dir = await workspace(t);
  const voices = await getNeuralVoices();
  const { readWave } = require('sherpa-onnx-node');
  const fingerprints = [];
  const text = '大家好，欢迎收听今天的播客。我们来聊一聊城市里的声音。';
  for (const id of ['neural:0', 'neural:33']) {
    assert.ok(voices.some(voice => voice.id === id && voice.language === 'zh-CN'));
    const outputPath = join(dir, `speaker-${id.split(':')[1]}.wav`);
    await renderNeuralSegment({ text, voiceId: id, outputPath, signal: t.signal });
    const { samples, sampleRate } = readWave(outputPath);
    assert.ok(samples instanceof Float32Array);
    assert.ok(sampleRate >= 8000 && samples.length > sampleRate);
    let energy = 0;
    for (const sample of samples) energy += sample * sample;
    const rms = Math.sqrt(energy / samples.length);
    assert.ok(rms > 0.005 && rms <= 1, `${id} has invalid or silent PCM (RMS ${rms})`);
    const pcm = Buffer.from(samples.buffer, samples.byteOffset, samples.byteLength);
    fingerprints.push(createHash('sha256').update(pcm).digest('hex'));
    t.diagnostic(`${id}: ${sampleRate} Hz, ${samples.length} samples, RMS ${rms.toFixed(3)}`);
  }
  assert.notEqual(fingerprints[0], fingerprints[1], 'speaker selection produced identical PCM');
});
