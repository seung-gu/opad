'use client'

import { useState, useEffect } from 'react'
import MarkdownViewer from '@/components/MarkdownViewer'
import InputForm from '@/components/InputForm'

export default function Home() {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [showForm, setShowForm] = useState(false)

  const loadContent = () => {
    setLoading(true)
    // Add timestamp to bypass cache
    const timestamp = new Date().getTime()
    // Try to fetch from public folder first (works on Vercel)
    // Fallback to API route for local development
    fetch(`/adapted_reading_material.md?v=${timestamp}`)
      .then(res => {
        if (res.ok) {
          return res.text()
        }
        throw new Error('File not found in public folder')
      })
      .then(text => {
        setContent(text)
        setLoading(false)
      })
      .catch(() => {
        // Fallback: Try API route (for local development)
        fetch(`/api/article?t=${timestamp}`)
          .then(res => res.text())
          .then(text => {
            setContent(text)
            setLoading(false)
          })
          .catch(() => {
            setContent('# No article found\n\nClick "Generate New Article" to create one.')
            setLoading(false)
          })
      })
  }

  useEffect(() => {
    loadContent()
  }, [])

  const handleGenerate = async (inputs: {
    language: string
    level: string
    length: string
    topic: string
  }) => {
    setGenerating(true)
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(inputs),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to generate article')
      }

      // Show success message
      alert('Article generation started! It will take a few minutes. The page will refresh automatically when ready.')

      // Poll for updated content (every 30 seconds)
      const pollInterval = setInterval(() => {
        loadContent()
      }, 30000)

      // Stop polling after 10 minutes
      setTimeout(() => {
        clearInterval(pollInterval)
        setGenerating(false)
      }, 600000)

    } catch (error: any) {
      alert(`Error: ${error.message}`)
      setGenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">OPAD Reading Materials</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
        >
          {showForm ? 'Hide Form' : 'Generate New Article'}
        </button>
      </div>

      {showForm && (
        <div className="mb-8">
          <InputForm onSubmit={handleGenerate} loading={generating} />
        </div>
      )}

      {generating && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
          <p className="text-blue-800">
            ⏳ Generating article... This may take a few minutes. The page will update automatically when ready.
          </p>
        </div>
      )}

      <MarkdownViewer content={content} />
    </main>
  )
}

