import {execFile} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createReadStream, createWriteStream} from 'node:fs';
import {mkdir, mkdtemp, readdir, rename, rm, stat} from 'node:fs/promises';
import path from 'node:path';
import {Readable} from 'node:stream';
import {pipeline} from 'node:stream/promises';
import {promisify} from 'node:util';
import {hasModel, modelDirectory, modelFiles, modelName} from '../server/neural.mjs';

const url = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/' + modelName + '.tar.bz2';
const expectedHash = 'ab468db3a3308cdd861495e0db2f25d79418a0c00639f74944c7cdf5dd8c6ec1';
const expectedSize = 31559701;
const destination = modelDirectory();
const fileHashes = {
  'model.onnx': '5511d651b7840c0a93a6bbfd4afd070a2c7f39ca1ec3ff2ecd73191519bbb852',
  'tokens.txt': '50b45a7b7de1752fd3c7b4755661c285f1547f59186eca2281089a81307ad953',
  'lexicon.txt': 'ab2e61d357551e7b24ddd965d924aca784c20165ff58c150794e539c6b5e9e35',
  'phone.fst': '1ac2b6fa56b1442320c4de7db08353bab8963a2b57f365eebcdd3a2d3562f8d7',
  'date.fst': 'eb8aa079ae3cb81d8f4404992f39d61a0cb990947512b5b8d1e54d1f6980e718',
  'number.fst': '743f402181fcfebf76cc2f0546b71fa26476e626fbe4e460fb7b4c3a7a8bd5bd',
};

async function sha256(file) {
  const hash = createHash('sha256');
  for await (const chunk of createReadStream(file)) hash.update(chunk);
  return hash.digest('hex');
}

async function installed() {
  if (await hasModel(destination)) {
    const hashes = await Promise.all(modelFiles.map(file => sha256(path.join(destination, file))));
    if (modelFiles.every((file, i) => hashes[i] === fileHashes[file])) return true;
  }
  try {
    if ((await readdir(destination)).length > 0) {
      throw new Error('模型目录不完整或校验失败。请先备份并移开该目录，或将 DVA_MODEL_DIR 指向空目录：' + destination);
    }
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  return false;
}

async function install(archivePath) {
  if (await installed()) {
    console.log('已安装中文多人语音模型：' + destination);
    return;
  }
  const parent = path.dirname(destination);
  await mkdir(parent, {recursive: true});
  const staging = await mkdtemp(path.join(parent, '.dva-model-'));
  try {
    let archive = archivePath;
    if (!archive) {
      archive = path.join(staging, 'model.tar.bz2');
      console.log('正在从 sherpa-onnx 官方发布下载中文语音模型（约 30 MiB）…');
      const response = await fetch(url, {signal: AbortSignal.timeout(15 * 60 * 1000)});
      if (!response.ok || !response.body) throw new Error('模型下载失败，HTTP ' + response.status);
      await pipeline(Readable.fromWeb(response.body), createWriteStream(archive, {flags: 'wx'}));
    }
    if ((await stat(archive)).size !== expectedSize) throw new Error('模型包长度不匹配。请重新下载官方压缩包。');
    if (await sha256(archive) !== expectedHash) throw new Error('模型包 SHA-256 不匹配。请重新下载官方压缩包。');
    const members = modelFiles.map(file => modelName + '/' + file);
    await promisify(execFile)('tar', ['-xjf', path.resolve(archive), '-C', staging, ...members]);
    const unpacked = path.join(staging, modelName);
    if (!await hasModel(unpacked)) throw new Error('模型包缺少所需文件。');
    try {
      await rename(unpacked, destination);
    } catch (error) {
      if (!await installed()) throw error;
    }
    console.log('中文多人语音模型已就绪：' + destination);
  } finally {
    await rm(staging, {recursive: true, force: true});
  }
}

try {
  await install(process.argv[2]);
} catch (error) {
  console.error('安装失败：' + error.message);
  process.exitCode = 1;
}
