import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  safelist: [
    // CEFR level colors from getLevelColor()
    'bg-gray-100',
    'text-gray-600',
    'bg-green-100',
    'text-green-700',
    'bg-yellow-100',
    'text-yellow-700',
    'bg-red-100',
    'text-red-700',
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
export default config

