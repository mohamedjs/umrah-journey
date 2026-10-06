import { createRoot } from 'react-dom/client';
import './game/hud/hud.css';
import { Game } from './game/Game.jsx';

createRoot(document.getElementById('root')).render(<Game />);
