/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{js,jsx,ts,tsx}', './components/**/*.{js,jsx,ts,tsx}'],
  presets: [require('nativewind/preset'), require('../../libs/tailwind-preset.cjs')],
  theme: {
    extend: {},
  },
  plugins: [],
};
