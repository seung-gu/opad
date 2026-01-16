'use client'

import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownViewerProps {
  content: string
  dark?: boolean // If true, use dark mode styles (for dark backgrounds)
}

export default function MarkdownViewer({ content, dark = false }: MarkdownViewerProps) {
  const [definitions, setDefinitions] = useState<Record<string, boolean>>({})
  const containerRef = useRef<HTMLDivElement>(null)
  const wordsMapRef = useRef<Map<string, string>>(new Map())

  const handleWordClick = (word: string, meaning: string) => {
    setDefinitions(prev => ({
      ...prev,
      [word]: !prev[word]
    }))
  }

  // Find and process [word:meaning] pattern
  const hasWordPattern = /\[([^\]]+):([^\]]+)\]/.test(content)
  
  // Convert [word:meaning] pattern to clickable elements after markdown rendering
  useEffect(() => {
    if (!containerRef.current || !hasWordPattern) return

    wordsMapRef.current.clear()

    const processNode = (node: Node) => {
      if (node.nodeType === Node.TEXT_NODE && node.textContent) {
        const text = node.textContent
        const regex = /\[([^\]]+):([^\]]+)\]/g
        const matches = Array.from(text.matchAll(regex))
        
        if (matches.length > 0) {
          const parent = node.parentNode
          if (!parent || parent.nodeName === 'CODE' || parent.nodeName === 'PRE') return

          const fragment = document.createDocumentFragment()
          let lastIndex = 0

          matches.forEach((match) => {
            if (match.index === undefined) return

            // Add previous text
            if (match.index > lastIndex) {
              fragment.appendChild(document.createTextNode(text.substring(lastIndex, match.index)))
            }

            const word = match[1]
            const meaning = match[2]
            wordsMapRef.current.set(word, meaning)

            // Create word span
            const wordSpan = document.createElement('span')
            wordSpan.className = 'vocab-word'
            wordSpan.textContent = word
            wordSpan.setAttribute('data-word', word)
            wordSpan.setAttribute('data-meaning', meaning)
            wordSpan.onclick = (e) => {
              e.stopPropagation()
              handleWordClick(word, meaning)
            }
            fragment.appendChild(wordSpan)

            lastIndex = (match.index || 0) + match[0].length
          })

          // Add remaining text
          if (lastIndex < text.length) {
            fragment.appendChild(document.createTextNode(text.substring(lastIndex)))
          }

          parent.replaceChild(fragment, node)
        }
      } else {
        // Recursively process child nodes
        const children = Array.from(node.childNodes)
        children.forEach(child => {
          if (child.nodeName !== 'SCRIPT' && child.nodeName !== 'STYLE') {
            processNode(child)
          }
        })
      }
    }

    processNode(containerRef.current)
  }, [content, hasWordPattern])

  // Update definition visibility when definitions change
  useEffect(() => {
    if (!containerRef.current) return

    const wordSpans = containerRef.current.querySelectorAll('.vocab-word')
    wordSpans.forEach((span) => {
      const word = span.getAttribute('data-word')
      const meaning = span.getAttribute('data-meaning')
      if (!word || !meaning) return

      const isVisible = definitions[word] || false
      
      // Remove existing definition
      const existingDef = span.nextElementSibling
      if (existingDef && existingDef.classList.contains('word-definition')) {
        existingDef.remove()
      }

      // Add new definition
      if (isVisible) {
        const defSpan = document.createElement('span')
        defSpan.className = 'word-definition'
        defSpan.innerHTML = `<strong>${word}</strong>: ${meaning}`
        span.parentNode?.insertBefore(defSpan, span.nextSibling)
      }
    })
  }, [definitions])

  const className = dark
    ? "prose prose-invert max-w-none text-slate-100 prose-headings:text-white prose-p:text-slate-100 prose-strong:text-white prose-li:text-slate-100 prose-ul:text-slate-100 prose-ol:text-slate-100 prose-a:text-emerald-400 prose-a:no-underline hover:prose-a:text-emerald-300 prose-code:text-emerald-300 prose-pre:bg-slate-800 prose-blockquote:text-slate-200 prose-blockquote:border-slate-600"
    : "prose max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900 prose-li:text-gray-700 prose-ul:text-gray-700 prose-ol:text-gray-700 prose-a:text-blue-600 prose-a:no-underline hover:prose-a:text-blue-800 prose-code:text-emerald-700 prose-pre:bg-gray-100 prose-blockquote:text-gray-600 prose-blockquote:border-gray-300"

  return (
    <div className={className} style={dark ? { color: '#f1f5f9' } : undefined} ref={containerRef}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}

