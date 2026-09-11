import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#172331',
        canvas: '#f7f6f2',
        muted: '#697481',
        line: '#d8dde1',
        selected: '#e9eef2',
        ready: '#2f6f5e',
        warning: '#b47a28',
        blocked: '#9b3f36'
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Source Serif 4', 'Georgia', 'serif']
      },
      boxShadow: {
        surface: '0 2px 10px rgba(23, 35, 49, 0.06)'
      }
    }
  },
  plugins: []
} satisfies Config;
