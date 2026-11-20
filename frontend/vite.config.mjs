import {defineConfig} from 'vite';
export default defineConfig({css:{postcss:{plugins:[]}},server:{proxy:{'/api':{target:'http://localhost:8000',rewrite:path=>path.replace(/^\/api/, '')}}}});
