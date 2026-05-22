import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://ramen-necklace.github.io',
  base: '/botse-apocrypha',
  trailingSlash: 'ignore',
  build: {
    format: 'directory',
  },
});
