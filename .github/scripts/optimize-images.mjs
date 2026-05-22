// Pre-build: для каждой картинки в public/images/ генерим .webp рядом.
// Сами .webp гитигнорятся — пересоздаются на каждой сборке.
import { readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const ROOT = 'public/images';
const EXTS = new Set(['.jpg', '.jpeg', '.png']);
const QUALITY = 82;

async function walk(dir) {
  const out = [];
  let entries;
  try {
    entries = await readdir(dir);
  } catch (e) {
    if (e.code === 'ENOENT') return out;
    throw e;
  }
  for (const name of entries) {
    const full = path.join(dir, name);
    const st = await stat(full);
    if (st.isDirectory()) out.push(...await walk(full));
    else out.push(full);
  }
  return out;
}

const files = await walk(ROOT);
let generated = 0;
for (const f of files) {
  const ext = path.extname(f).toLowerCase();
  if (!EXTS.has(ext)) continue;
  const webp = f.replace(/\.(jpg|jpeg|png)$/i, '.webp');
  try {
    await stat(webp);
    continue; // уже есть
  } catch {}
  try {
    await sharp(f).webp({ quality: QUALITY }).toFile(webp);
    console.log(`[webp] ${path.relative(ROOT, webp)}`);
    generated += 1;
  } catch (e) {
    console.error(`[webp] FAILED ${f}: ${e.message}`);
  }
}
console.log(`[webp] generated ${generated} file(s)`);
