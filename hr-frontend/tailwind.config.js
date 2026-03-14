/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'neo-yellow': '#FFE135',
        'neo-teal': '#00C9B1',
        'neo-coral': '#FF6B6B',
        'neo-blue': '#4D96FF',
        'neo-bg': '#FFFBF0',
        'neo-black': '#0A0A0A',
      },
      boxShadow: {
        neo: '4px 4px 0px 0px #0A0A0A',
        'neo-lg': '6px 6px 0px 0px #0A0A0A',
        'neo-sm': '2px 2px 0px 0px #0A0A0A',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
};
