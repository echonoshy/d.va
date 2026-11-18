import {build} from 'esbuild';
import {cp, mkdir, rm} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const out = path.join(root, 'dist');
await rm(out, {recursive: true, force: true});
await mkdir(path.join(out, 'assets'), {recursive: true});
await build({
  absWorkingDir: root,
  entryPoints: ['web/src/main.tsx'],
  outfile: 'dist/assets/app.js',
  bundle: true,
  format: 'esm',
  jsx: 'automatic',
  target: ['es2022'],
  minify: true,
  define: {'process.env.NODE_ENV': '"production"'},
  loader: {'.woff2': 'file', '.png': 'file', '.webp': 'file'},
  assetNames: '[name]-[hash]',
  legalComments: 'eof',
  logLevel: 'info',
});
await cp(path.join(root, 'web/index.html'), path.join(out, 'index.html'));

await mkdir(path.join(out, "docs"), {recursive: true});
await cp(path.join(root, "docs/5518052-parity.md"), path.join(out, "docs/5518052-parity.md"));
await cp(path.join(root, "LICENSE"), path.join(out, "LICENSE"));
