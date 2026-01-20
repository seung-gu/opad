'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { split } from 'sentence-splitter'
import { Vocabulary } from '@/types/article'

interface MarkdownViewerProps {
  content: string
  language?: string // Target language for dictionary API lookups
  dark?: boolean // If true, use dark mode styles (for dark backgrounds)
  articleId?: string // Article ID for vocabulary
  vocabularies?: Vocabulary[] // Current vocabularies
  onAddVocabulary?: (vocab: Vocabulary) => void // Callback when vocabulary is added
  clickable?: boolean // If false, words are not clickable (default: true)
}

export default function MarkdownViewer({ 
  content, 
  language, 
  dark = false,
  articleId,
  vocabularies = [],
  onAddVocabulary,
  clickable = true
}: MarkdownViewerProps) {
  const [openSpanIds, setOpenSpanIds] = useState<Set<string>>(new Set()) // Track which specific spans are open
  const [wordDefinitions, setWordDefinitions] = useState<Record<string, string>>({}) // Cache API-fetched definitions
  const [loadingWords, setLoadingWords] = useState<Set<string>>(new Set())
  const containerRef = useRef<HTMLDivElement>(null)
  const spanIdCounterRef = useRef<number>(0) // Counter for generating unique span IDs
  const lemmaCacheRef = useRef<Map<string, string>>(new Map()) // Cache word lemmas from LLM: "language:word" -> JSON string of {lemma, definition, related_words}
  const wordToLemmaRef = useRef<Map<string, string>>(new Map()) // Word -> Lemma mapping: "word" -> "lemma" (for finding same lemma variants)
  const loadingWordsRef = useRef<Set<string>>(new Set()) // Synchronous loading state tracking

  // Extract sentence containing the clicked word
  const extractSentence = (wordSpan: HTMLElement): string => {
    // If parent.innerText equals word, it's likely an inline element, go up one more level
    let parent = wordSpan.parentElement
    const word = wordSpan.textContent || ''
    
    if (parent && parent.innerText === word) {
      parent = parent.parentElement
    }
    
    if (!parent) {
      return containerRef.current?.textContent || ''
    }
    
    const text = (parent.textContent || '').replace(/\s+/g, ' ').trim()
    
    try {
      // Use sentence-splitter to split text into sentences
      const result = split(text)
      const sentences = result
        .filter(node => node.type === 'Sentence')
        .map(node => node.raw.trim())
        .filter(s => s)
      
      // Find sentence containing the clicked word
      const found = sentences.find(s => 
        new RegExp(`\\b${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i').test(s)
      )
      
      return found || text
    } catch (error) {
      // Fallback to simple split if sentence-splitter fails
      console.warn('sentence-splitter failed, using fallback:', error)
      const sentences = text.split(/([.!?]+\s+)/).filter(s => s.trim())
      const found = sentences.find(s => new RegExp(`\\b${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i').test(s))
      return found ? found.trim() : text
    }
  }

  // Get word definition and lemma from LLM using sentence context
  const getWordDefinitionFromLLM = async (word: string, sentence: string): Promise<{ lemma: string, definition: string, related_words?: string[] } | null> => {
    if (!language) {
      return null
    }

    // First check word-only cache (same word = same definition, regardless of sentence)
    const wordCacheKey = `${language}:${word.toLowerCase()}`
    if (lemmaCacheRef.current.has(wordCacheKey)) {
      const cached = lemmaCacheRef.current.get(wordCacheKey)
      if (cached) {
        try {
          const { lemma, definition, related_words } = JSON.parse(cached)
          console.log('[Dictionary] Using word-only cache for:', word)
          return { lemma, definition, related_words }
        } catch (e) {
          console.warn('[Dictionary] Failed to parse cached value, clearing cache')
          lemmaCacheRef.current.delete(wordCacheKey)
        }
      }
    }
    
    // Fallback: check sentence-specific cache
    const sentenceCacheKey = `${language}:${word.toLowerCase()}:${sentence.substring(0, 50)}`
    if (lemmaCacheRef.current.has(sentenceCacheKey)) {
      const cached = lemmaCacheRef.current.get(sentenceCacheKey)
      if (cached) {
        try {
          const { lemma, definition, related_words } = JSON.parse(cached)
          console.log('[Dictionary] Using sentence-specific cache for:', word)
          return { lemma, definition, related_words }
        } catch (e) {
          console.warn('[Dictionary] Failed to parse cached value, clearing cache')
          lemmaCacheRef.current.delete(sentenceCacheKey)
        }
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
      const related_words = data.related_words || undefined
      
      if (definition) {
        // Cache: store in both word-only cache and sentence-specific cache
        const wordCacheKey = `${language}:${word.toLowerCase()}`
        const sentenceCacheKey = `${language}:${word.toLowerCase()}:${sentence.substring(0, 50)}`
        const cacheValue = JSON.stringify({ lemma, definition, related_words })
        
        lemmaCacheRef.current.set(wordCacheKey, cacheValue) // Word-only cache (reusable across sentences)
        lemmaCacheRef.current.set(sentenceCacheKey, cacheValue) // Sentence-specific cache
        
        console.log('[Dictionary] Cached definition for:', word, 'lemma:', lemma, 'related_words:', related_words)
        return { lemma, definition, related_words }
      }
      
      return null
    } catch (err) {
      console.error('[Dictionary] LLM error:', err)
      return null
    }
  }

  const handleWordClick = useCallback(async (spanId: string, word: string) => {
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
        try {
          const { lemma } = JSON.parse(cached)
          cachedLemma = lemma
          // Check if we already have definition for this lemma
          if (wordDefinitions[lemma]) {
            console.log('[Dictionary] Using cached definition for lemma:', lemma, 'from word:', word)
            return
          }
        } catch (e) {
          console.warn('[Dictionary] Failed to parse cached value, clearing cache')
          lemmaCacheRef.current.delete(wordCacheKey)
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
        const cacheValue = JSON.stringify({ 
          lemma, 
          definition: result.definition, 
          related_words: result.related_words 
        })
        lemmaCacheRef.current.set(cacheKey, cacheValue)
      }
      
      // Store related_words mapping for all related words
      if (result.related_words && result.related_words.length > 0) {
        result.related_words.forEach(relatedWord => {
          wordToLemmaRef.current.set(relatedWord.toLowerCase(), lemma.toLowerCase())
        })
      }
    } else {
      // Store error using word as key (since we don't have lemma)
      setWordDefinitions(prev => ({
        ...prev,
        [word]: 'Definition not found'
      }))
    }
  }, [language, openSpanIds, wordDefinitions, loadingWords])

  // Make all words clickable (only if clickable prop is true)
  useEffect(() => {
    if (!containerRef.current || !clickable) return

    const processNode = (node: Node) => {
      if (node.nodeType === Node.TEXT_NODE && node.textContent) {
        const text = node.textContent
        const parent = node.parentNode
        
        // Skip if already processed or in code blocks
        if (!parent || parent.nodeName === 'CODE' || parent.nodeName === 'PRE') return
        if (parent instanceof HTMLElement && parent.classList.contains('vocab-word')) return
        
        const fragment = document.createDocumentFragment()
        
        // Helper: make words in text clickable (skip whitespace-only and punctuation-only)
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
              handleWordClick(spanId, part)
            }
            fragment.appendChild(wordSpan)
          } else {
            // Otherwise, just add as text
            fragment.appendChild(document.createTextNode(part))
          }
        })
        
        if (fragment.childNodes.length > 0) {
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
  }, [content, language, handleWordClick, clickable])

  // Update definition visibility when openSpanIds change
  useEffect(() => {
    if (!containerRef.current) return

    const wordSpans = containerRef.current.querySelectorAll('.vocab-word')
    wordSpans.forEach((span) => {
      const word = span.getAttribute('data-word')
      const spanId = span.getAttribute('data-span-id')
      if (!word || !spanId) return
      
      let meaning: string | null = null
      let displayLemma: string = word // Default to word if lemma not found
      
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
            try {
              const { lemma } = JSON.parse(cached)
              displayLemma = lemma
              meaning = wordDefinitions[lemma] || null
            } catch (e) {
              console.warn('[Dictionary] Failed to parse cached value')
            }
          }
        }
      }
      // Fallback: try word directly (for old cache format or errors)
      if (!meaning) {
        meaning = wordDefinitions[word] || null
      }
      
      // Check if word is in vocabulary and add/remove class
      // Compare with lemma, original word, and related_words
      const isInVocabulary = vocabularies.some(
        v => v.lemma.toLowerCase() === displayLemma.toLowerCase() ||
             v.lemma.toLowerCase() === word.toLowerCase() ||
             v.word.toLowerCase() === word.toLowerCase() ||
             (v.related_words && v.related_words.some(rw => rw.toLowerCase() === word.toLowerCase()))
      )
      
      if (isInVocabulary) {
        span.classList.add('vocab-saved')
      } else {
        span.classList.remove('vocab-saved')
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
          // Check if word is already in vocabulary
          const isInVocabulary = vocabularies.some(v => v.lemma.toLowerCase() === displayLemma.toLowerCase())
          const sentence = extractSentence(span as HTMLElement)
          
          // Get related_words from wordDefinitions (stored when word was clicked)
          // We need to find the related_words for this lemma
          let relatedWords: string[] | undefined = undefined
          // Try to find related_words from wordToLemmaRef and lemmaCacheRef
          const wordCacheKey = language ? `${language}:${word.toLowerCase()}` : null
          if (wordCacheKey && lemmaCacheRef.current.has(wordCacheKey)) {
            const cached = lemmaCacheRef.current.get(wordCacheKey)
            if (cached) {
              try {
                const { related_words } = JSON.parse(cached)
                relatedWords = related_words
              } catch (e) {
                // Ignore parse error
              }
            }
          }
          
          // Create definition HTML with vocabulary button
          let defHtml = `<strong>${displayLemma}</strong>: ${meaning}`
          
          if (articleId && onAddVocabulary) {
            const relatedWordsStr = relatedWords ? JSON.stringify(relatedWords).replace(/"/g, '&quot;') : ''
            if (isInVocabulary) {
              defHtml += ` <button class="vocab-btn vocab-remove" data-word="${word}" data-lemma="${displayLemma}" data-definition="${meaning}" data-sentence="${sentence.replace(/"/g, '&quot;')}" data-related-words="${relatedWordsStr}" style="margin-left: 6px; padding: 1px 4px; font-size: 0.7rem; background: #ef4444; color: white; border: none; border-radius: 3px; cursor: pointer; min-width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center;" title="Remove from vocabulary">−</button>`
            } else {
              defHtml += ` <button class="vocab-btn vocab-add" data-word="${word}" data-lemma="${displayLemma}" data-definition="${meaning}" data-sentence="${sentence.replace(/"/g, '&quot;')}" data-related-words="${relatedWordsStr}" style="margin-left: 6px; padding: 1px 4px; font-size: 0.7rem; background: #10b981; color: white; border: none; border-radius: 3px; cursor: pointer; min-width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center;" title="Add to vocabulary">+</button>`
            }
          }
          
          defSpan.innerHTML = defHtml
          
          // Attach click handlers to vocabulary buttons
          const addBtn = defSpan.querySelector('.vocab-add')
          const removeBtn = defSpan.querySelector('.vocab-remove')
          
          if (addBtn) {
            addBtn.addEventListener('click', async (e) => {
              e.stopPropagation()
              const btn = e.target as HTMLElement
              const word = btn.getAttribute('data-word') || ''
              const lemma = btn.getAttribute('data-lemma') || ''
              const definition = btn.getAttribute('data-definition') || ''
              const sentence = btn.getAttribute('data-sentence') || ''
              const relatedWordsStr = btn.getAttribute('data-related-words') || ''
              let relatedWords: string[] | undefined = undefined
              if (relatedWordsStr) {
                try {
                  relatedWords = JSON.parse(relatedWordsStr.replace(/&quot;/g, '"'))
                } catch (e) {
                  // Ignore parse error
                }
              }
              
              try {
                const response = await fetch('/api/vocabularies', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    article_id: articleId,
                    word,
                    lemma,
                    definition,
                    sentence,
                    language,
                    related_words: relatedWords
                  })
                })
                
                if (response.ok) {
                  const newVocab = await response.json()
                  onAddVocabulary?.(newVocab)
                }
              } catch (error) {
                console.error('Failed to add vocabulary:', error)
              }
            })
          }
          
          if (removeBtn) {
            removeBtn.addEventListener('click', async (e) => {
              e.stopPropagation()
              const btn = e.target as HTMLElement
              const lemma = btn.getAttribute('data-lemma') || ''
              
              const vocab = vocabularies.find(v => v.lemma.toLowerCase() === lemma.toLowerCase())
              if (vocab) {
                try {
                  const response = await fetch(`/api/vocabularies/${vocab.id}`, {
                    method: 'DELETE'
                  })
                  
                  if (response.ok) {
                    // Remove from vocabularies list (parent component will handle)
                    // We'll trigger a re-render by updating state
                    window.dispatchEvent(new CustomEvent('vocabulary-removed', { detail: vocab.id }))
                  }
                } catch (error) {
                  console.error('Failed to remove vocabulary:', error)
                }
              }
            })
          }
        }
        
        // Insert definition after the word
        span.parentNode?.insertBefore(defSpan, afterWord)
        
        // Restore what was after the word to after the definition
        if (afterWord) {
          span.parentNode?.insertBefore(afterWord, defSpan.nextSibling)
        }
      }
    })
  }, [openSpanIds, wordDefinitions, loadingWords, vocabularies, articleId, onAddVocabulary, language])

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

