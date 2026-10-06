'use client'

import { useState, type FormEvent } from 'react'

interface InputFormProps {
  onSubmit: (inputs: {
    language: string
    level: string
    length: string
    topic: string
  }) => Promise<void>
  loading?: boolean
}

const LANGUAGES = ['English', 'German', 'Spanish', 'French', 'Korean']
const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
const LENGTHS = ['300', '500', '800']

/**
 * Segmented control: the active option is marked with an accent underline.
 */
function Segmented({
  label,
  options,
  value,
  onChange,
  disabled,
}: Readonly<{
  label: string
  options: readonly string[]
  value: string
  onChange: (v: string) => void
  disabled?: boolean
}>) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-[12px] text-text-dim">{label}</span>
      <div className="flex items-baseline">
        {options.map((option) => (
          <button
            key={option}
            type="button"
            disabled={disabled}
            aria-pressed={value === option}
            onClick={() => onChange(option)}
            className={`border-b-2 px-1.5 pb-0.5 text-[13px] tabular-nums transition-colors disabled:opacity-40 ${
              value === option
                ? 'border-accent font-medium text-foreground'
                : 'border-transparent text-text-dim hover:text-foreground'
            }`}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function InputForm({ onSubmit, loading = false }: InputFormProps) {
  const [language, setLanguage] = useState('German')
  const [level, setLevel] = useState('B2')
  const [length, setLength] = useState('500')
  const [topic, setTopic] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    await onSubmit({ language, level, length, topic })
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border border-border-card bg-card transition-colors focus-within:border-accent"
    >
      <label htmlFor="topic" className="sr-only">
        Topic
      </label>
      <input
        id="topic"
        type="text"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="What do you want to read about?"
        required
        disabled={loading}
        className="w-full bg-transparent px-5 py-4 font-serif text-[21px] text-foreground placeholder:italic placeholder:text-text-dim focus:outline-none disabled:opacity-50"
      />

      <div className="flex flex-wrap items-baseline gap-x-5 gap-y-3 border-t border-border-card px-5 py-3">
        <div className="flex items-baseline gap-2">
          <label htmlFor="language" className="text-[12px] text-text-dim">
            Language
          </label>
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={loading}
            className="border-b-2 border-transparent bg-transparent pb-0.5 text-[13px] text-foreground focus:border-accent focus:outline-none disabled:opacity-40"
          >
            {LANGUAGES.map((l) => (
              <option key={l} value={l} className="bg-card text-foreground">
                {l}
              </option>
            ))}
          </select>
        </div>

        <Segmented label="Level" options={LEVELS} value={level} onChange={setLevel} disabled={loading} />
        <Segmented label="Words" options={LENGTHS} value={length} onChange={setLength} disabled={loading} />

        <button type="submit" disabled={loading} className="btn-primary ml-auto">
          {loading ? 'Generating' : 'Generate'}
        </button>
      </div>
    </form>
  )
}
