'use client'

import { useState, useEffect } from 'react'
import MarkdownViewer from '@/components/MarkdownViewer'

export default function Home() {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Try to fetch from public folder first (works on Vercel)
    // Fallback to API route for local development
    fetch('/adapted_reading_material.md')
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
        fetch('/api/article')
          .then(res => res.text())
          .then(text => {
            setContent(text)
            setLoading(false)
          })
          .catch(() => {
            setContent('# No article found\n\n**For local development:**\nRun: `crewai run` in the opad project\n\n**For Vercel deployment:**\nCopy the output file to web/public/adapted_reading_material.md')
            setLoading(false)
          })
      })
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">OPAD Reading Materials</h1>
      <MarkdownViewer content={content} />
    </main>
  )
}

