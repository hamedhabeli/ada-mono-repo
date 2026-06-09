/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slate: { 900: '#0f172a', 800: '#1e293b' },
        neural: '#06b6d4',   // Cyan برای Gemini
        symbolic: '#10b981', // Emerald برای Z3
        error: '#e11d48',    // Crimson برای تناقض
        oracle: '#f59e0b',   // Amber برای کاربر
      }
    },
  },
  plugins: [],
}