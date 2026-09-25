export const DEFAULT_RENDER_BACKEND = 'https://final-thesis-zgwt.onrender.com';

export function getApiBaseUrl(): string {
  if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined' && window.location) {
    const host = window.location.hostname.toLowerCase();
    if (
      host.includes('eddiephung.me') ||
      host.includes('vercel.app') ||
      host.includes('onrender.com') ||
      (host !== 'localhost' && host !== '127.0.0.1' && !host.startsWith('192.168.') && !host.endsWith('.local'))
    ) {
      return DEFAULT_RENDER_BACKEND;
    }
  }
  return '';
}
