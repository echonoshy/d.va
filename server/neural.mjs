import {fork} from 'node:child_process';
import {stat} from 'node:fs/promises';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

export const modelName = 'vits-icefall-zh-aishell3';
export const modelFiles = ['model.onnx', 'tokens.txt', 'lexicon.txt', 'phone.fst', 'date.fst', 'number.fst'];

const modulePath = fileURLToPath(import.meta.url);
const require = createRequire(import.meta.url);
const speakerIds = [0, 1, 18, 33, 66, 88, 120, 150];

export function modelDirectory() {
  return path.resolve(process.env.DVA_MODEL_DIR || fileURLToPath(new URL('../models/' + modelName, import.meta.url)));
}

export async function hasModel(directory) {
  try {
    const files = await Promise.all(modelFiles.map(name => stat(path.join(directory, name))));
    return files.every(file => file.isFile() && file.size > 0);
  } catch (error) {
    if (error.code === 'ENOENT' || error.code === 'ENOTDIR') return false;
    throw error;
  }
}

export async function getNeuralVoices() {
  try {
    if (!await hasModel(modelDirectory())) throw new Error('Missing or empty model files');
    require('sherpa-onnx-node');
  } catch (error) {
    if (process.env.DVA_MODEL_DIR) {
      throw new Error('无法加载 DVA_MODEL_DIR 指定的中文模型或当前平台的 sherpa-onnx 组件。', {cause: error});
    }
    return [];
  }
  return speakerIds.map(id => ({
    id: 'neural:' + id, name: '普通话 ' + String(id + 1).padStart(3, '0'),
    language: 'zh-CN', engine: 'AISHELL-3',
  }));
}

export function renderNeuralSegment({text, voiceId, outputPath, signal}) {
  const match = /^neural:(\d+)$/.exec(voiceId);
  if (!match || !speakerIds.includes(Number(match[1]))) throw new Error('未找到所选中文音色。');
  signal?.throwIfAborted();
  // Isolate native inference so cancellation can stop CPU work immediately.
  return new Promise((resolve, reject) => {
    const child = fork(modulePath, ['--synthesize'], {
      execArgv: [], stdio: ['ignore', 'ignore', 'pipe', 'ipc'], signal, killSignal: 'SIGKILL',
    });
    let diagnostic = '';
    child.stderr.setEncoding('utf8').on('data', part => { diagnostic = (diagnostic + part).slice(-2000); });
    child.once('error', reject);
    child.once('close', code => {
      if (code === 0) resolve();
      else reject(new Error('本地中文模型合成失败。', {cause: new Error(diagnostic)}));
    });
    child.send({text, speaker: Number(match[1]), outputPath}, error => {
      if (error) reject(error);
    });
  });
}

if (process.argv[1] === modulePath && process.argv[2] === '--synthesize' && process.send) {
  process.once('message', ({text, speaker, outputPath}) => {
    try {
      const sherpa = require('sherpa-onnx-node');
      const file = name => path.join(modelDirectory(), name);
      const tts = new sherpa.OfflineTts({
        model: {vits: {model: file('model.onnx'), tokens: file('tokens.txt'), lexicon: file('lexicon.txt')},
          numThreads: 2, provider: 'cpu', debug: false},
        maxNumSentences: 1,
        ruleFsts: modelFiles.filter(name => name.endsWith('.fst')).map(file).join(','),
      });
      const audio = tts.generate({text, generationConfig: new sherpa.GenerationConfig({sid: speaker, speed: 1.0})});
      if (!audio.samples.length) throw new Error('未产生语音。');
      if (!sherpa.writeWave(outputPath, {samples: audio.samples, sampleRate: audio.sampleRate})) {
        throw new Error('无法写入合成音频。');
      }
    } catch (error) {
      console.error(error.message);
      process.exitCode = 1;
    } finally {
      // Node 22.12 still has IPC callbacks queued when the message handler returns.
      setImmediate(() => {
        if (process.connected) process.disconnect();
      });
    }
  });
}
