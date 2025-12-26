'use client'

import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function MarkdownViewer({ content }: { content: string }) {
  const [definitions, setDefinitions] = useState<Record<string, boolean>>({})
  const containerRef = useRef<HTMLDivElement>(null)
  const wordsMapRef = useRef<Map<string, string>>(new Map())

  const handleWordClick = (word: string, meaning: string) => {
    setDefinitions(prev => ({
      ...prev,
      [word]: !prev[word]
    }))
  }

  // [word:meaning] 패턴을 찾아서 처리
  const hasWordPattern = /\[([^\]]+):([^\]]+)\]/.test(content)
  
  // 마크다운 렌더링 후 [word:meaning] 패턴을 클릭 가능한 요소로 변환
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

            // 이전 텍스트 추가
            if (match.index > lastIndex) {
              fragment.appendChild(document.createTextNode(text.substring(lastIndex, match.index)))
            }

            const word = match[1]
            const meaning = match[2]
            wordsMapRef.current.set(word, meaning)

            // 단어 span
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

          // 마지막 텍스트 추가
          if (lastIndex < text.length) {
            fragment.appendChild(document.createTextNode(text.substring(lastIndex)))
          }

          parent.replaceChild(fragment, node)
        }
      } else {
        // 자식 노드 재귀 처리
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

  // definitions 변경 시 정의 표시/숨김 업데이트
  useEffect(() => {
    if (!containerRef.current) return

    const wordSpans = containerRef.current.querySelectorAll('.vocab-word')
    wordSpans.forEach((span) => {
      const word = span.getAttribute('data-word')
      const meaning = span.getAttribute('data-meaning')
      if (!word || !meaning) return

      const isVisible = definitions[word] || false
      
      // 기존 정의 제거
      const existingDef = span.nextElementSibling
      if (existingDef && existingDef.classList.contains('word-definition')) {
        existingDef.remove()
      }

      // 새 정의 추가
      if (isVisible) {
        const defSpan = document.createElement('span')
        defSpan.className = 'word-definition'
        defSpan.innerHTML = `<strong>${word}</strong>: ${meaning}`
        span.parentNode?.insertBefore(defSpan, span.nextSibling)
      }
    })
  }, [definitions])

  return (
    <div className="prose max-w-none" ref={containerRef}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}

