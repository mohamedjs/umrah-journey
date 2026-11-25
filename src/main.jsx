import { createRoot } from 'react-dom/client';
import './game/hud/hud.css';
import { Game } from './game/Game.jsx';
import { initPWA } from './pwa/pwa.js';

createRoot(document.getElementById('root')).render(<Game />);
initPWA();   // installable + offline (service worker after a few seconds)
