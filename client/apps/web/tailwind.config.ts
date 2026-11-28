import type { Config } from 'tailwindcss'

const config: Config = {
  presets: [require('../../libs/tailwind-preset.cjs')],
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  safelist: [
    // CEFR level colors - dark theme versions
    'bg-card',
    'text-text-dim',
    'bg-good/20',
    'text-good',
    'bg-accent-warn/20',
    'text-accent-warn',
    'bg-accent-danger/20',
    'text-accent-danger',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-sans)', 'Noto Sans KR', 'sans-serif'],
        serif: ['var(--font-serif)', 'Newsreader', 'Georgia', 'serif'],
        mono: ['var(--font-mono)', 'JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
export default config
