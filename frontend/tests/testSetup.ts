import '@testing-library/jest-dom/vitest';

if (typeof window !== 'undefined') {
  if (typeof window.URL.createObjectURL === 'undefined') {
    window.URL.createObjectURL = () => `blob:mock-url-${Math.random()}`;
  }
  if (typeof window.URL.revokeObjectURL === 'undefined') {
    window.URL.revokeObjectURL = () => {};
  }
}
