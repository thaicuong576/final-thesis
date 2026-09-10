import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: './tests/testSetup.ts',
    css: true,
    globals: true
  }
});
