import type { Config } from 'tailwindcss'

const config: Config = {
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
      colors: {
        // Background
        background: 'var(--bg)',
        card: 'var(--card)',
        'card-hover': 'var(--card-hover)',
        'border-card': 'var(--card-border)',

        // Accent
        accent: {
          DEFAULT: 'var(--accent)',
          warn: 'var(--warn)',
          danger: 'var(--danger)',
        },

        // Text
        foreground: 'var(--text)',
        'text-dim': 'var(--text-dim)',
        'text-strong': 'var(--strong)',
        'btn-text': 'var(--btn-text)',

        // Status
        good: 'var(--good)',
        weak: 'var(--weak)',
        vocab: 'var(--vocab)',
        system: 'var(--system)',
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'Noto Sans KR', 'sans-serif'],
        mono: ['var(--font-mono)', 'JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
export default config
