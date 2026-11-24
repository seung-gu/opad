/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./app/**/*.{js,jsx,ts,tsx}', './components/**/*.{js,jsx,ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        background: '#100f0e',
        card: '#171614',
        'card-hover': '#1f1d1a',
        'border-card': '#2d2a25',
        accent: {
          DEFAULT: '#c75b3f',
          warn: '#b08a4a',
          danger: '#a8392e',
        },
        foreground: '#d9d3c7',
        'text-dim': '#8b8478',
        'text-strong': '#efeae0',
        'btn-text': '#faf7f1',
        good: '#6f8f7d',
        weak: '#b08a4a',
        vocab: '#c75b3f',
        system: '#c75b3f',
      },
    },
  },
  plugins: [],
};
