/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        claude: {
          bg: '#F8FAFC',
          sidebar: '#F1F5F9',
          card: '#FFFFFF',
          border: '#E2E8F0',
          hover: '#F1F5F9',
          primary: '#0D9488',     // Nordic Teal / Emerald brand accent
          primaryHover: '#0F766E',
          primaryLight: '#CCFBF1',
          primaryBg: '#F0FDFA',
          text: '#0F172A',
          muted: '#64748B',
        },
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          '"Helvetica Neue"',
          'Arial',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
};
