'use client'

import { useState } from 'react'

interface InputFormProps {
  onSubmit: (inputs: {
    language: string
    level: string
    length: string
    topic: string
  }) => Promise<void>
  loading?: boolean
}

export default function InputForm({ onSubmit, loading = false }: InputFormProps) {
  const [language, setLanguage] = useState('German')
  const [level, setLevel] = useState('B2')
  const [length, setLength] = useState('500')
  const [topic, setTopic] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSubmit({ language, level, length, topic })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 p-6 border border-border-card rounded-lg bg-card shadow-lg">
      <div>
        <label className="block text-sm font-medium mb-2 text-foreground">Language</label>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="w-full px-3 py-2 border border-border-card rounded-md bg-card-hover text-foreground focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent"
          required
          disabled={loading}
        >
          <option value="English">English</option>
          <option value="German">German</option>
          <option value="Spanish">Spanish</option>
          <option value="French">French</option>
          <option value="Korean">Korean</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2 text-foreground">Level</label>
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          className="w-full px-3 py-2 border border-border-card rounded-md bg-card-hover text-foreground focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent"
          required
          disabled={loading}
        >
          <option value="A1">A1</option>
          <option value="A2">A2</option>
          <option value="B1">B1</option>
          <option value="B2">B2</option>
          <option value="C1">C1</option>
          <option value="C2">C2</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2 text-foreground">Length (words)</label>
        <input
          type="number"
          value={length}
          onChange={(e) => setLength(e.target.value)}
          className="w-full px-3 py-2 border border-border-card rounded-md bg-card-hover text-foreground focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent"
          min="100"
          max="2000"
          required
          disabled={loading}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2 text-foreground">Topic</label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          className="w-full px-3 py-2 border border-border-card rounded-md bg-card-hover text-foreground focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent placeholder:text-text-dim"
          placeholder="Enter your topic"
          required
          disabled={loading}
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="btn-outline btn-generate w-full"
      >
        {loading ? 'Generating...' : 'Generate Reading Material'}
      </button>
    </form>
  )
}
