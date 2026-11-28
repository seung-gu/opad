/** @type {import('tailwindcss').Config} */
module.exports = {
  theme: {
    extend: {
      colors: {
        background: 'var(--bg)',
        card: 'var(--card)',
        'card-hover': 'var(--card-hover)',
        'border-card': 'var(--card-border)',

        accent: {
          DEFAULT: 'var(--accent)',
          warn: 'var(--warn)',
          danger: 'var(--danger)',
        },

        foreground: 'var(--text)',
        'text-dim': 'var(--text-dim)',
        'text-strong': 'var(--strong)',
        'btn-text': 'var(--btn-text)',

        good: 'var(--good)',
        weak: 'var(--weak)',
        vocab: 'var(--vocab)',
        system: 'var(--system)',
      },
    },
  },
};
