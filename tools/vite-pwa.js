// Tiny PWA build step (copied from «رحلة مع القرآن»; no Workbox).
// On `vite build` it emits next to index.html:
//   sw.js                 src/pwa/sw.js + the precache list (every file of THIS build + public/)
//   manifest.webmanifest  (from public/, copied by Vite as usual)
// All URLs are relative, so the same dist/ works at /old/umrah-journey/dist/ and on Railway
// The unused Remix Icon font formats (eot/svg/ttf/woff — browsers load the woff2) are left out.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const SKIP = [/^assets\/remixicon-.*\.(eot|svg|ttf|woff)$/, /^assets\/draco_/, /(^|\/)\.[^/]+$/, /\.map$/, /^precache-report\.json$/];   // browsers only load the woff2 icon font; canonical draco lives in public/draco/
const OPTIONAL = [
  /^audio\/(?!manifest\.json)/,
  /^icons\/(?!icon-192)/,
  /^models\/env\/(?!kaaba|haram_mataf|maqam)/,
  /^models\/characters\/(?!player|mentor|crowd)/,
];   // cached in background / fetched at runtime if they fail during install
const md5 = buf => crypto.createHash('md5').update(buf).digest('hex').slice(0, 10);

function walk(dir, base = dir, out = []) {
  for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, f.name);
    if (f.isDirectory()) walk(p, base, out); else out.push(path.relative(base, p).split(path.sep).join('/'));
  }
  return out;
}

export default function pwa({ swSource = 'src/pwa/sw.js' } = {}) {
  let config;
  return {
    name: 'umrah-journey-pwa',
    apply: 'build', enforce: 'post',          // after Vite has emitted index.html
    configResolved(c) { config = c; },
    generateBundle(_, bundle) {
      const files = new Map();
      for (const [name, item] of Object.entries(bundle)) {
        const src = item.type === 'chunk' ? item.code : item.source;
        files.set(name, { size: Buffer.byteLength(src), rev: md5(src) });
      }
      if (config.publicDir && fs.existsSync(config.publicDir)) {
        for (const rel of walk(config.publicDir)) {
          if (files.has(rel)) continue;
          const buf = fs.readFileSync(path.join(config.publicDir, rel));
          files.set(rel, { size: buf.length, rev: md5(buf) });
        }
      }
      const list = [...files].filter(([u]) => !SKIP.some(re => re.test(u)) && u !== 'sw.js')
        .map(([url, { size, rev }]) => ({ url, rev, size, core: !OPTIONAL.some(re => re.test(url)) }))
        .sort((a, b) => (a.core === b.core ? a.url.localeCompare(b.url) : a.core ? -1 : 1));
      const version = md5(JSON.stringify(list.map(e => e.url + e.rev)));
      const total = list.reduce((a, e) => a + e.size, 0), core = list.filter(e => e.core).reduce((a, e) => a + e.size, 0);
      const sw = `self.__VERSION = ${JSON.stringify(version)};\nself.__PRECACHE = ${JSON.stringify(list)};\n` + fs.readFileSync(path.resolve(config.root, swSource), 'utf8');
      this.emitFile({ type: 'asset', fileName: 'sw.js', source: sw });
      this.emitFile({ type: 'asset', fileName: 'precache-report.json', source: JSON.stringify({ version, files: list.length, bytes: total, coreBytes: core }, null, 1) });
      config.logger.info(`\n[pwa] sw.js ${version}: precache ${list.length} files, ${(total / 1048576).toFixed(1)} MB (core ${(core / 1048576).toFixed(1)} MB)`);
    },
  };
}
