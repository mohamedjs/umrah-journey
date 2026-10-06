import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base './' so the built prototype runs from any sub-path (e.g. Apache at /old/umrah-journey/dist/)
export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    target: 'es2022', chunkSizeWarningLimit: 900,
    rolldownOptions: { output: { codeSplitting: { groups: [
      { name: 'three', test: /node_modules[\\/]three[\\/]/, priority: 20 },
      { name: 'react', test: /node_modules[\\/](react|react-dom|scheduler|@react-three[\\/]fiber|zustand|its-fine|suspend-react|react-use-measure|use-sync-external-store)[\\/]/, priority: 10 },
    ] } } },
  },
});
