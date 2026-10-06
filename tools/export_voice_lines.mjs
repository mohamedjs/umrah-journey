// Writes tools/voice_lines.json from src/game/content.js (same format as the Quran game:
// [{ id, enc, speaker, text }]) so tools/openrouter_tts_lines.py can voice every line.
//   npm run voice-lines
import fs from 'node:fs';
import { allLines } from '../src/game/content.js';

const lines = allLines().map(l => ({ id: l.id, enc: l.id.split('/')[0], speaker: l.who, text: l.text }));
const seen = new Set(), out = lines.filter(l => !seen.has(l.id) && seen.add(l.id));
fs.writeFileSync(new URL('./voice_lines.json', import.meta.url), JSON.stringify(out, null, 1) + '\n');
console.log(`tools/voice_lines.json: ${out.length} lines (${[...new Set(out.map(l => l.speaker))].join(', ')})`);
