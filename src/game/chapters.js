import { buildHome, homeLayout } from './scenes/home.js';
import { buildAirport, airportLayout } from './scenes/airport.js';
import { buildPlane, planeLayout } from './scenes/plane.js';
import { buildMakkah, makkahLayout } from './scenes/makkah.js';
import { buildMataf, matafLayout } from './mataf.js';
import { buildMasa, masaLayout } from './masa.js';
import { createHome } from './rites/home.js';
import { createAirport } from './rites/airport.js';
import { createPlane } from './rites/plane.js';
import { createMakkah } from './rites/makkah.js';
import { createTawaf } from './rites/tawaf.js';
import { createSai } from './rites/sai.js';

// The journey in order. `n` is the chapter number shown in the HUD (CLAUDE.md list numbering;
// chapter 6 — the two rak'ahs and Zamzam — is played at the end of the tawaf scene).
export const CHAPTERS = [
  { id: 'home',    n: 1, title: 'البيت',            sub: 'جهّز شنطة العمرة',                         icon: 'ri-home-heart-line',   build: buildHome,    layout: homeLayout,    rites: createHome },
  { id: 'airport', n: 2, title: 'المطار',           sub: 'الكاونتر ثم البوابة',                      icon: 'ri-luggage-cart-line', build: buildAirport, layout: airportLayout, rites: createAirport },
  { id: 'plane',   n: 3, title: 'الطيارة والميقات', sub: 'الإحرام والنية والتلبية',                  icon: 'ri-plane-line',        build: buildPlane,   layout: planeLayout,   rites: createPlane },
  { id: 'makkah',  n: 4, title: 'مكة',              sub: 'الفندق ثم باب المسجد الحرام',               icon: 'ri-building-2-line',   build: buildMakkah,  layout: makkahLayout,  rites: createMakkah },
  { id: 'tawaf',   n: 5, title: 'الطواف',           sub: 'سبعة أشواط، ثم ركعتان خلف المقام وزمزم',   icon: 'ri-loop-left-line',    build: buildMataf,   layout: matafLayout,   rites: createTawaf },
  { id: 'sai',     n: 7, title: 'السعي',            sub: 'سبعة أشواط بين الصفا والمروة',             icon: 'ri-walk-line',         build: buildMasa,    layout: masaLayout,    rites: createSai },
];
export const chapterById = id => CHAPTERS.find(c => c.id === id);
