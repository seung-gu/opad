'use client'

import { useState, useEffect } from 'react'
import MarkdownViewer from '@/components/MarkdownViewer'

export default function Home() {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // output 폴더의 마크다운 파일 읽기
    fetch('/api/article')
      .then(res => res.text())
      .then(text => {
        setContent(text)
        setLoading(false)
      })
      .catch(() => {
        setContent('# No article found\n\nPlease run the crewAI to generate an article first.')
        setLoading(false)
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

