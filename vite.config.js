import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import pwa from './tools/vite-pwa.js';

// Default base './' works on Railway (/) and local sub-paths (e.g. /old/umrah-journey/dist/);
// GitHub Pages builds with VITE_BASE=/umrah-journey/.
export default defineConfig({
  base: process.env.VITE_BASE || './',
  plugins: [react(), pwa()],   // tools/vite-pwa.js emits sw.js (offline play) with this build's precache list
  build: {
    target: 'es2022', chunkSizeWarningLimit: 900,
    rolldownOptions: { output: { codeSplitting: { groups: [
      { name: 'three', test: /node_modules[\\/]three[\\/]/, priority: 20 },
      { name: 'react', test: /node_modules[\\/](react|react-dom|scheduler|@react-three[\\/]fiber|zustand|its-fine|suspend-react|react-use-measure|use-sync-external-store)[\\/]/, priority: 10 },
    ] } } },
  },
});
