'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownViewerProps {
  content: string
  language?: string // Target language for dictionary API lookups
  dark?: boolean // If true, use dark mode styles (for dark backgrounds)
}

export default function MarkdownViewer({ content, language, dark = false }: MarkdownViewerProps) {
  const [openSpanIds, setOpenSpanIds] = useState<Set<string>>(new Set()) // Track which specific spans are open
  const [wordDefinitions, setWordDefinitions] = useState<Record<string, string>>({}) // Cache API-fetched definitions
  const [loadingWords, setLoadingWords] = useState<Set<string>>(new Set())
  const containerRef = useRef<HTMLDivElement>(null)
  const wordsMapRef = useRef<Map<string, string>>(new Map()) // Agent-provided [word:definition]
  const spanIdCounterRef = useRef<number>(0) // Counter for generating unique span IDs
  const lemmaCacheRef = useRef<Map<string, string>>(new Map()) // Cache word lemmas from LLM: "language:word" -> "lemma|||definition"
  const wordToLemmaRef = useRef<Map<string, string>>(new Map()) // Word -> Lemma mapping: "word" -> "lemma" (for finding same lemma variants)
  const loadingWordsRef = useRef<Set<string>>(new Set()) // Synchronous loading state tracking

  // Extract sentence containing the clicked word
  const extractSentence = (wordSpan: HTMLElement): string => {
    // Find the parent paragraph or closest text container
    let parent = wordSpan.parentElement
    while (parent && !['P', 'LI', 'DIV', 'ARTICLE'].includes(parent.tagName)) {
      parent = parent.parentElement
    }
    
    if (!parent) {
      // Fallback: get text from the entire container
      return containerRef.current?.textContent || ''
    }
    
    // Get text content of the paragraph, removing extra whitespace
    const text = parent.textContent || ''
    // Clean up: remove extra spaces and newlines
    return text.replace(/\s+/g, ' ').trim()
  }

  // Get word definition and lemma from LLM using sentence context
  const getWordDefinitionFromLLM = async (word: string, sentence: string): Promise<{ lemma: string, definition: string } | null> => {
    if (!language) {
      return null
    }

    // First check word-only cache (same word = same definition, regardless of sentence)
    const wordCacheKey = `${language}:${word.toLowerCase()}`
    if (lemmaCacheRef.current.has(wordCacheKey)) {
      const cached = lemmaCacheRef.current.get(wordCacheKey)
      if (cached) {
        const [lemma, definition] = cached.split('|||')
        console.log('[Dictionary] Using word-only cache for:', word)
        return { lemma, definition }
      }
    }
    
    // Fallback: check sentence-specific cache
    const sentenceCacheKey = `${language}:${word.toLowerCase()}:${sentence.substring(0, 50)}`
    if (lemmaCacheRef.current.has(sentenceCacheKey)) {
      const cached = lemmaCacheRef.current.get(sentenceCacheKey)
      if (cached) {
        const [lemma, definition] = cached.split('|||')
        console.log('[Dictionary] Using sentence-specific cache for:', word)
        return { lemma, definition }
      }
    }
    
    try {
      const response = await fetch('/api/openai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sentence: sentence,
          word: word,
          language: language
        })
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('[Dictionary] LLM API error:', response.status, errorText)
        return null
      }
      
      const data = await response.json()
      console.log('[Dictionary] LLM response:', data)
      
      if (data.error) {
        console.error('[Dictionary] LLM API returned error:', data.error)
        return null
      }
      
      const lemma = data.lemma?.trim() || word
      const definition = data.definition?.trim()
      
      if (definition) {
        // Cache: store in both word-only cache and sentence-specific cache
        const wordCacheKey = `${language}:${word.toLowerCase()}`
        const sentenceCacheKey = `${language}:${word.toLowerCase()}:${sentence.substring(0, 50)}`
        const cacheValue = `${lemma}|||${definition}`
        
        lemmaCacheRef.current.set(wordCacheKey, cacheValue) // Word-only cache (reusable across sentences)
        lemmaCacheRef.current.set(sentenceCacheKey, cacheValue) // Sentence-specific cache
        
        console.log('[Dictionary] Cached definition for:', word, 'lemma:', lemma)
        return { lemma, definition }
      }
      
      return null
    } catch (err) {
      console.error('[Dictionary] LLM error:', err)
      return null
    }
  }

  const handleWordClick = useCallback(async (spanId: string, word: string, meaning?: string) => {
    // Toggle this specific span
    const isOpening = !openSpanIds.has(spanId)
    setOpenSpanIds(prev => {
      const next = new Set(prev)
      if (next.has(spanId)) {
        next.delete(spanId)
      } else {
        next.add(spanId)
      }
      return next
    })
    
    // If meaning is provided (agent-provided word), we're done
    if (meaning) {
      return
    }
    
    // If closing, no need to fetch
    if (!isOpening) {
      return
    }
    
    // First, try to find lemma from cache for this specific word
    const wordCacheKey = `${language}:${word.toLowerCase()}`
    let cachedLemma: string | null = null
    if (lemmaCacheRef.current.has(wordCacheKey)) {
      const cached = lemmaCacheRef.current.get(wordCacheKey)
      if (cached) {
        const [lemma] = cached.split('|||')
        cachedLemma = lemma
        // Check if we already have definition for this lemma
        if (wordDefinitions[lemma]) {
          console.log('[Dictionary] Using cached definition for lemma:', lemma, 'from word:', word)
          return
        }
      }
    }
    
    // Try to find lemma from wordToLemmaRef (if this word was mapped before)
    if (wordToLemmaRef.current.has(word.toLowerCase())) {
      const lemma = wordToLemmaRef.current.get(word.toLowerCase())
      if (lemma && wordDefinitions[lemma]) {
        console.log('[Dictionary] Using cached definition for lemma:', lemma, 'from word mapping:', word)
        return
      }
    }
    
    // If already cached by word (fallback for old cache format)
    if (wordDefinitions[word]) {
      console.log('[Dictionary] Using cached definition for:', word, wordDefinitions[word])
      return
    }
    
    // If already loading, don't fetch again (check ref for synchronous check)
    if (loadingWordsRef.current.has(word)) {
      console.log('[Dictionary] Already loading:', word)
      return
    }
    
    console.log('[Dictionary] Fetching definition for:', word, 'Current cache:', Object.keys(wordDefinitions))
    
    // Mark as loading immediately (synchronous)
    loadingWordsRef.current.add(word)
    setLoadingWords(prev => new Set(prev).add(word))
    
    // Find the span element to extract sentence
    const spanElement = containerRef.current?.querySelector(`[data-span-id="${spanId}"]`) as HTMLElement
    const sentence = spanElement ? extractSentence(spanElement) : ''
    
    console.log('[Dictionary] Extracted sentence:', sentence)
    
    // Get definition and lemma from LLM using sentence context
    const result = await getWordDefinitionFromLLM(word, sentence)
    
    loadingWordsRef.current.delete(word)
    setLoadingWords(prev => {
      const next = new Set(prev)
      next.delete(word)
      return next
    })
    
    if (result) {
      // Store definition using LEMMA as key (so different word forms with same lemma share the same definition)
      const lemma = result.lemma || word
      setWordDefinitions(prev => ({
        ...prev,
        [lemma]: result.definition  // Use lemma as key, not word
      }))
      
      // Store word -> lemma mapping (so we can find same lemma variants later)
      wordToLemmaRef.current.set(word.toLowerCase(), lemma.toLowerCase())
      
      // Also store in lemmaCacheRef for backward compatibility
      if (lemma.toLowerCase() !== word.toLowerCase()) {
        const cacheKey = `${language}:${word.toLowerCase()}`
        lemmaCacheRef.current.set(cacheKey, `${lemma}|||${result.definition}`)
      }
    } else {
      // Store error using word as key (since we don't have lemma)
      setWordDefinitions(prev => ({
        ...prev,
        [word]: 'Definition not found'
      }))
    }
  }, [language, openSpanIds, wordDefinitions, loadingWords])

  // Convert [word:meaning] pattern to clickable elements AND make all other words clickable
  useEffect(() => {
    if (!containerRef.current) return

    wordsMapRef.current.clear()

    const processNode = (node: Node) => {
      if (node.nodeType === Node.TEXT_NODE && node.textContent) {
        const text = node.textContent
        const parent = node.parentNode
        
        // Skip if already processed or in code blocks
        if (!parent || parent.nodeName === 'CODE' || parent.nodeName === 'PRE') return
        if (parent instanceof HTMLElement && parent.classList.contains('vocab-word')) return
        
        const regex = /\[([^\]]+):([^\]]+)\]/g
        const matches = Array.from(text.matchAll(regex))
        
        const fragment = document.createDocumentFragment()
        let lastIndex = 0

        // Process [word:definition] patterns
        if (matches.length > 0) {
          matches.forEach((match) => {
            if (match.index === undefined) return

            // Add previous text (make words clickable)
            if (match.index > lastIndex) {
              const prevText = text.substring(lastIndex, match.index)
              appendClickableWords(prevText, fragment)
            }

            const word = match[1]
            const meaning = match[2]
            wordsMapRef.current.set(word, meaning)

            // Create agent-provided word span
            const spanId = `vocab-${spanIdCounterRef.current++}`
            const wordSpan = document.createElement('span')
            wordSpan.className = 'vocab-word agent-provided'
            wordSpan.textContent = word
            wordSpan.setAttribute('data-word', word)
            wordSpan.setAttribute('data-meaning', meaning)
            wordSpan.setAttribute('data-span-id', spanId)
            wordSpan.onclick = (e) => {
              e.stopPropagation()
              handleWordClick(spanId, word, meaning)
            }
            fragment.appendChild(wordSpan)

            lastIndex = (match.index || 0) + match[0].length
          })

          // Add remaining text (make words clickable)
          if (lastIndex < text.length) {
            const remainingText = text.substring(lastIndex)
            appendClickableWords(remainingText, fragment)
          }

          parent.replaceChild(fragment, node)
        } else {
          // No [word:definition] patterns, make all words clickable
          appendClickableWords(text, fragment)
          if (fragment.childNodes.length > 0) {
            parent.replaceChild(fragment, node)
          }
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

    // Helper: make words in text clickable (skip whitespace-only and punctuation-only)
    const appendClickableWords = (text: string, fragment: DocumentFragment) => {
      // Split by whitespace and punctuation, but keep them in the output
      const parts = text.split(/(\s+|[.,;:!?()[\]{}""''—–-]+)/)
      
      parts.forEach(part => {
        if (!part) return
        
        // If it's whitespace or punctuation, just add as text
        if (/^(\s+|[.,;:!?()[\]{}""''—–-]+)$/.test(part)) {
          fragment.appendChild(document.createTextNode(part))
          return
        }
        
        // If it's a word (alphanumeric), make it clickable
        if (/[a-zA-Z0-9]/.test(part)) {
          const spanId = `vocab-${spanIdCounterRef.current++}`
          const wordSpan = document.createElement('span')
          wordSpan.className = 'vocab-word user-clickable'
          wordSpan.textContent = part
          wordSpan.setAttribute('data-word', part)
          wordSpan.setAttribute('data-span-id', spanId)
          wordSpan.onclick = (e) => {
            e.stopPropagation()
            handleWordClick(spanId, part) // No meaning provided (API fetch)
          }
          fragment.appendChild(wordSpan)
        } else {
          // Otherwise, just add as text
          fragment.appendChild(document.createTextNode(part))
        }
      })
    }

    processNode(containerRef.current)
  }, [content, language])

  // Update definition visibility when openSpanIds change
  useEffect(() => {
    if (!containerRef.current) return

    const wordSpans = containerRef.current.querySelectorAll('.vocab-word')
    wordSpans.forEach((span) => {
      const word = span.getAttribute('data-word')
      const spanId = span.getAttribute('data-span-id')
      if (!word || !spanId) return
      
      const isAgentProvided = span.classList.contains('agent-provided')
      let meaning: string | null = null
      let displayLemma: string = word // Default to word if lemma not found
      
      if (isAgentProvided) {
        meaning = span.getAttribute('data-meaning')
      } else {
        // Try to find lemma from wordToLemmaRef first
        if (wordToLemmaRef.current.has(word.toLowerCase())) {
          const lemma = wordToLemmaRef.current.get(word.toLowerCase())
          if (lemma) {
            displayLemma = lemma
            meaning = wordDefinitions[lemma] || null
          }
        }
        // Fallback: try lemmaCacheRef
        if (!meaning) {
          const wordCacheKey = language ? `${language}:${word.toLowerCase()}` : null
          if (wordCacheKey && lemmaCacheRef.current.has(wordCacheKey)) {
            const cached = lemmaCacheRef.current.get(wordCacheKey)
            if (cached) {
              const [lemma] = cached.split('|||')
              displayLemma = lemma
              meaning = wordDefinitions[lemma] || null
            }
          }
        }
        // Fallback: try word directly (for old cache format or errors)
        if (!meaning) {
          meaning = wordDefinitions[word] || null
        }
      }
      
      const isVisible = openSpanIds.has(spanId)
      const isLoading = loadingWords.has(word) && isVisible
      
      // Remove existing definition
      const existingDef = span.nextElementSibling
      if (existingDef && existingDef.classList.contains('word-definition')) {
        // Save what comes after the definition
        const afterDef = existingDef.nextSibling
        existingDef.remove()
        // Restore what was after the definition to after the word
        if (afterDef) {
          span.parentNode?.insertBefore(afterDef, span.nextSibling)
        }
      }

      // Add new definition or loading indicator
      if (isVisible || isLoading) {
        // Save what comes after the word
        const afterWord = span.nextSibling
        
        const defSpan = document.createElement('span')
        defSpan.className = 'word-definition'
        
        if (isLoading) {
          defSpan.innerHTML = `<strong>${word}</strong>: <em>Loading...</em>`
        } else if (meaning) {
          defSpan.innerHTML = `<strong>${displayLemma}</strong>: ${meaning}`
        }
        
        // Insert definition after the word
        span.parentNode?.insertBefore(defSpan, afterWord)
        
        // Restore what was after the word to after the definition
        if (afterWord) {
          span.parentNode?.insertBefore(afterWord, defSpan.nextSibling)
        }
      }
    })
  }, [openSpanIds, wordDefinitions, loadingWords])

  const className = dark
    ? "prose prose-invert max-w-none text-white prose-headings:text-white prose-p:text-white prose-strong:text-white prose-li:text-white prose-ul:text-white prose-ol:text-white prose-a:text-emerald-400 prose-a:no-underline hover:prose-a:text-emerald-300 prose-code:text-emerald-300 prose-pre:bg-slate-800 prose-blockquote:text-white prose-blockquote:border-slate-600"
    : "prose max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900 prose-li:text-gray-700 prose-ul:text-gray-700 prose-ol:text-gray-700 prose-a:text-blue-600 prose-a:no-underline hover:prose-a:text-blue-800 prose-code:text-emerald-700 prose-pre:bg-gray-100 prose-blockquote:text-gray-600 prose-blockquote:border-gray-300"

  return (
    <div className={className} style={dark ? { color: '#ffffff' } : undefined} ref={containerRef}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}

