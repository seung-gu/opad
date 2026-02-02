'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { split } from 'sentence-splitter'
import { Vocabulary } from '@/types/article'
import { fetchWithAuth } from '@/lib/api'

// Data attribute constants to avoid duplication
const DATA_ATTR = {
  WORD: 'data-word',
  SPAN_ID: 'data-span-id',
  LEMMA: 'data-lemma',
  DEFINITION: 'data-definition',
  SENTENCE: 'data-sentence',
  RELATED_WORDS: 'data-related-words',
  POS: 'data-pos',
  GENDER: 'data-gender',
  CONJUGATIONS: 'data-conjugations',
  LEVEL: 'data-level',
  PROCESSED: 'data-processed',
} as const

// CSS class constants
const CSS_CLASS = {
  VOCAB_SAVED: 'vocab-saved',
  VOCAB_WORD: 'vocab-word',
  USER_CLICKABLE: 'user-clickable',
} as const

// Helper: Escape HTML to prevent XSS (module-level for stable reference)
function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

interface MarkdownViewerProps {
  content: string
  language?: string // Target language for dictionary API lookups
  dark?: boolean // If true, use dark mode styles (for dark backgrounds)
  articleId?: string // Article ID for vocabulary
  vocabularies?: Vocabulary[] // Current vocabularies
  onAddVocabulary?: (vocab: Vocabulary) => void // Callback when vocabulary is added
  onTokenUsageUpdate?: () => void // Callback to refresh token usage after dictionary search
  clickable?: boolean // If false, words are not clickable (default: true)
}

export default function MarkdownViewer({
  content,
  language,
  dark = false,
  articleId,
  vocabularies = [],
  onAddVocabulary,
  onTokenUsageUpdate,
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

  // Helper: Get word meaning and lemma from cache
  const getWordMeaning = useCallback((word: string): { meaning: string | null, displayLemma: string } => {
    let meaning: string | null = null
    let displayLemma: string = word

    if (wordToLemmaRef.current.has(word.toLowerCase())) {
      const lemma = wordToLemmaRef.current.get(word.toLowerCase())
      if (lemma) {
        displayLemma = lemma
        meaning = wordDefinitions[lemma] || null
      }
    }

    if (!meaning) {
      const wordCacheKey = language ? `${language}:${word.toLowerCase()}` : null
      if (wordCacheKey && lemmaCacheRef.current.has(wordCacheKey)) {
        const cached = lemmaCacheRef.current.get(wordCacheKey)
        if (cached) {
          try {
            const { lemma } = JSON.parse(cached)
            displayLemma = lemma
            meaning = wordDefinitions[lemma] || null
          } catch {
            console.warn('[Dictionary] Failed to parse cached value')
          }
        }
      }
    }

    if (!meaning) {
      meaning = wordDefinitions[word] || null
    }

    return { meaning, displayLemma }
  }, [language, wordDefinitions])

  // Helper: Get related words from cache
  const getRelatedWords = useCallback((word: string): string[] | undefined => {
    const wordCacheKey = language ? `${language}:${word.toLowerCase()}` : null
    if (wordCacheKey && lemmaCacheRef.current.has(wordCacheKey)) {
      const cached = lemmaCacheRef.current.get(wordCacheKey)
      if (cached) {
        try {
          const { related_words } = JSON.parse(cached)
          return related_words
        } catch {
          // Ignore parse error
        }
      }
    }
    return undefined
  }, [language])

  // Helper: Create vocabulary button HTML
  const createVocabularyButtonHTML = useCallback((
    word: string,
    lemma: string,
    definition: string,
    sentence: string,
    relatedWords: string[] | undefined,
    spanId: string,
    isInVocabulary: boolean,
    pos?: string,
    gender?: string,
    conjugations?: { present?: string, past?: string, perfect?: string },
    level?: string
  ): string => {
    // Escape all user-provided content to prevent XSS
    const wordEscaped = escapeHtml(word)
    const lemmaEscaped = escapeHtml(lemma)
    const definitionEscaped = escapeHtml(definition)
    const relatedWordsStr = relatedWords ? JSON.stringify(relatedWords).replace(/"/g, '&quot;') : ''
    const sentenceEscaped = escapeHtml(sentence).replace(/"/g, '&quot;')
    const posStr = pos ? escapeHtml(pos) : ''
    const genderStr = gender ? escapeHtml(gender) : ''
    const conjugationsStr = conjugations ? JSON.stringify(conjugations).replace(/"/g, '&quot;') : ''
    const levelStr = level ? escapeHtml(level) : ''
    const spanIdEscaped = escapeHtml(spanId)
    const baseStyle = 'margin-left: 6px; padding: 1px 4px; font-size: 0.7rem; color: var(--bg); border: none; border-radius: 3px; cursor: pointer; min-width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center;'

    if (isInVocabulary) {
      const style = `${baseStyle} background: var(--danger);`
      return ` <button class="vocab-btn vocab-remove" data-word="${wordEscaped}" data-lemma="${lemmaEscaped}" data-definition="${definitionEscaped}" data-sentence="${sentenceEscaped}" data-related-words="${relatedWordsStr}" data-span-id="${spanIdEscaped}" data-pos="${posStr}" data-gender="${genderStr}" data-conjugations="${conjugationsStr}" data-level="${levelStr}" style="${style}" title="Remove from vocabulary">−</button>`
    } else {
      const style = `${baseStyle} background: var(--vocab);`
      return ` <button class="vocab-btn vocab-add" data-word="${wordEscaped}" data-lemma="${lemmaEscaped}" data-definition="${definitionEscaped}" data-sentence="${sentenceEscaped}" data-related-words="${relatedWordsStr}" data-span-id="${spanIdEscaped}" data-pos="${posStr}" data-gender="${genderStr}" data-conjugations="${conjugationsStr}" data-level="${levelStr}" style="${style}" title="Add to vocabulary">+</button>`
    }
  }, [])

  // Helper: Handle add vocabulary button click
  const handleAddVocabularyClick = useCallback(async (btn: HTMLElement) => {
    const word = btn.getAttribute(DATA_ATTR.WORD) || ''
    const lemma = btn.getAttribute('data-lemma') || ''
    const definition = btn.getAttribute('data-definition') || ''
    const sentence = btn.getAttribute('data-sentence') || ''
    const relatedWordsStr = btn.getAttribute('data-related-words') || ''
    const spanId = btn.getAttribute(DATA_ATTR.SPAN_ID) || ''
    const pos = btn.getAttribute('data-pos') || undefined
    const gender = btn.getAttribute('data-gender') || undefined
    const conjugationsStr = btn.getAttribute('data-conjugations') || ''
    const level = btn.getAttribute('data-level') || undefined

    let relatedWords: string[] | undefined = undefined
    if (relatedWordsStr) {
      try {
        relatedWords = JSON.parse(relatedWordsStr.replace(/&quot;/g, '"'))
      } catch {
        // Ignore parse error
      }
    }

    let conjugations: { present?: string, past?: string, perfect?: string } | undefined = undefined
    if (conjugationsStr) {
      try {
        conjugations = JSON.parse(conjugationsStr.replace(/&quot;/g, '"'))
      } catch {
        // Ignore parse error
      }
    }

    try {
      const response = await fetchWithAuth('/api/dictionary/vocabularies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          article_id: articleId,
          word,
          lemma,
          definition,
          sentence,
          language,
          related_words: relatedWords,
          span_id: spanId || undefined,
          pos: pos || undefined,
          gender: gender || undefined,
          conjugations: conjugations || undefined,
          level: level || undefined
        })
      })

      if (response.ok) {
        const newVocab = await response.json()
        onAddVocabulary?.(newVocab)
      }
    } catch (error) {
      console.error('Failed to add vocabulary:', error)
    }
  }, [articleId, language, onAddVocabulary])

  // Helper: Handle remove vocabulary button click
  const handleRemoveVocabularyClick = useCallback(async (btn: HTMLElement) => {
    const lemma = btn.getAttribute('data-lemma') || ''
    const vocab = vocabularies.find(v => v.lemma.toLowerCase() === lemma.toLowerCase())
    
    if (vocab) {
      try {
        const response = await fetchWithAuth(`/api/dictionary/vocabularies/${vocab.id}`, {
          method: 'DELETE'
        })

        if (response.ok) {
          globalThis.dispatchEvent(new CustomEvent('vocabulary-removed', { detail: vocab.id }))
        }
      } catch (error) {
        console.error('Failed to remove vocabulary:', error)
      }
    }
  }, [vocabularies])

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
      
      // Find sentence containing the clicked word (use includes for Korean/Unicode support)
      const found = sentences.find(s =>
        s.toLowerCase().includes(word.toLowerCase())
      )

      return found || text
    } catch (error) {
      // Fallback to simple split if sentence-splitter fails
      console.warn('sentence-splitter failed, using fallback:', error)
      // Use non-greedy pattern to avoid ReDoS
      const sentences = text.split(/([.!?]\s*)/).filter(s => s.trim())
      const found = sentences.find(s => s.toLowerCase().includes(word.toLowerCase()))
      return found ? found.trim() : text
    }
  }

  // Get word definition and lemma from LLM using sentence context
  const getWordDefinitionFromLLM = async (word: string, sentence: string): Promise<{
    lemma: string,
    definition: string,
    related_words?: string[],
    pos?: string,
    gender?: string,
    conjugations?: { present?: string, past?: string, perfect?: string },
    level?: string
  } | null> => {
    if (!language) {
      return null
    }

    // First check word-only cache (same word = same definition, regardless of sentence)
    const wordCacheKey = `${language}:${word.toLowerCase()}`
    if (lemmaCacheRef.current.has(wordCacheKey)) {
      const cached = lemmaCacheRef.current.get(wordCacheKey)
      if (cached) {
        try {
          const { lemma, definition, related_words, pos, gender, conjugations, level } = JSON.parse(cached)
          // Debug: console.log('[Dictionary] Using word-only cache for:', word)
          return { lemma, definition, related_words, pos, gender, conjugations, level }
        } catch {
          console.warn('[Dictionary] Failed to parse cached value, clearing cache')
          lemmaCacheRef.current.delete(wordCacheKey)
        }
      }
    }

    try {
      // Debug: console.log('[Dictionary] Sending search request:', { word, language, articleId })
      const response = await fetchWithAuth('/api/dictionary/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sentence: sentence,
          word: word,
          language: language,
          article_id: articleId
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error('[Dictionary] LLM API error:', response.status, errorText)
        return null
      }

      const data = await response.json()
      // Debug: console.log('[Dictionary] LLM response:', data)

      if (data.error) {
        console.error('[Dictionary] LLM API returned error:', data.error)
        return null
      }

      const lemma = data.lemma?.trim() || word
      const definition = data.definition?.trim()
      const related_words = data.related_words || undefined
      const pos = data.pos || undefined
      const gender = data.gender || undefined
      const conjugations = data.conjugations || undefined
      const level = data.level || undefined

      if (definition) {
        // Cache: store word-only cache (same word = same definition, regardless of sentence)
        const wordCacheKey = `${language}:${word.toLowerCase()}`
        const cacheValue = JSON.stringify({ lemma, definition, related_words, pos, gender, conjugations, level })

        lemmaCacheRef.current.set(wordCacheKey, cacheValue)

        // Refresh token usage after successful dictionary search
        onTokenUsageUpdate?.()

        // Debug: console.log('[Dictionary] Cached definition for:', word, 'lemma:', lemma, 'pos:', pos, 'gender:', gender, 'level:', level)
        return { lemma, definition, related_words, pos, gender, conjugations, level }
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
    if (lemmaCacheRef.current.has(wordCacheKey)) {
      const cached = lemmaCacheRef.current.get(wordCacheKey)
      if (cached) {
        try {
          const { lemma } = JSON.parse(cached)
          // Check if we already have definition for this lemma
          if (wordDefinitions[lemma]) {
            // Debug: console.log('[Dictionary] Using cached definition for lemma:', lemma, 'from word:', word)
            return
          }
        } catch {
          console.warn('[Dictionary] Failed to parse cached value, clearing cache')
          lemmaCacheRef.current.delete(wordCacheKey)
        }
      }
    }
    
    // Try to find lemma from wordToLemmaRef (if this word was mapped before)
    if (wordToLemmaRef.current.has(word.toLowerCase())) {
      const lemma = wordToLemmaRef.current.get(word.toLowerCase())
      if (lemma && wordDefinitions[lemma]) {
        // Debug: console.log('[Dictionary] Using cached definition for lemma:', lemma, 'from word mapping:', word)
        return
      }
    }
    
    // If already cached by word (fallback for old cache format)
    if (wordDefinitions[word]) {
      // Debug: console.log('[Dictionary] Using cached definition for:', word, wordDefinitions[word])
      return
    }
    
    // If already loading, don't fetch again (check ref for synchronous check)
    if (loadingWordsRef.current.has(word)) {
      // Debug: console.log('[Dictionary] Already loading:', word)
      return
    }
    
    // Debug: console.log('[Dictionary] Fetching definition for:', word, 'Current cache:', Object.keys(wordDefinitions))
    
    // Mark as loading immediately (synchronous)
    loadingWordsRef.current.add(word)
    setLoadingWords(prev => new Set(prev).add(word))
    
    // Find the span element to extract sentence
    const spanElement = containerRef.current?.querySelector(`[data-span-id="${spanId}"]`) as HTMLElement
    const sentence = spanElement ? extractSentence(spanElement) : ''
    
    // Debug: console.log('[Dictionary] Extracted sentence:', sentence)
    
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
      // Preserve lemma capitalization (important for German nouns: Hund, not hund)
      wordToLemmaRef.current.set(word.toLowerCase(), lemma)
      
      // Note: lemmaCacheRef is already set in getWordDefinitionFromLLM, no need to set again here
      
      // Store related_words mapping for all related words
      if (result.related_words && result.related_words.length > 0) {
        result.related_words.forEach(relatedWord => {
          wordToLemmaRef.current.set(relatedWord.toLowerCase(), lemma)
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

  // Store handleWordClick ref for event delegation (avoid stale closure)
  const handleWordClickRef = useRef(handleWordClick)
  useEffect(() => {
    handleWordClickRef.current = handleWordClick
  }, [handleWordClick])

  // Make all words clickable (only if clickable prop is true)
  useEffect(() => {
    if (!containerRef.current || !clickable) return

    /**
     * Skip if already processed (component remounts on content change via key prop).
     *
     * Parent components use key={`${articleId}-${content.length}`} to force remount
     * when content changes, ensuring this processing logic runs with clean DOM state.
     *
     * See: src/web/app/articles/[id]/page.tsx:266
     */
    if (containerRef.current.getAttribute(DATA_ATTR.PROCESSED) === 'true') {
      return
    }

    const processNode = (node: Node) => {
      if (node.nodeType === Node.TEXT_NODE && node.textContent) {
        const text = node.textContent
        const parent = node.parentNode

        // Skip if already processed or in code blocks
        if (!parent || parent.nodeName === 'CODE' || parent.nodeName === 'PRE') return
        if (parent instanceof HTMLElement && parent.classList.contains('vocab-word')) return

        const fragment = document.createDocumentFragment()

        // Helper: make words in text clickable (skip whitespace-only and punctuation-only)
        // Note: hyphen (-) is NOT included so "long-standing" stays as one word
        // Punctuation: basic + curly quotes (U+201C-201D, U+2018-2019) + dashes (U+2013-2014)
        const punctuationPattern = /(\s+|[.,;:!?()[\]{}]+|[\u201C\u201D\u2018\u2019]+|[\u2013\u2014]+)/
        const parts = text.split(punctuationPattern)

        parts.forEach(part => {
          if (!part) return

          // If it's whitespace, punctuation, or standalone hyphen, just add as text
          if (/^(\s+|[.,;:!?()[\]{}]+|[\u201C\u201D\u2018\u2019]+|[\u2013\u2014]+|-+)$/.test(part)) {
            fragment.appendChild(document.createTextNode(part))
            return
          }

          // Make word clickable (already filtered whitespace/punctuation above)
          const spanId = `vocab-${spanIdCounterRef.current++}`
          const wordSpan = document.createElement('span')
          wordSpan.textContent = part
          wordSpan.setAttribute(DATA_ATTR.WORD, part)
          wordSpan.setAttribute(DATA_ATTR.SPAN_ID, spanId)
          if ((parent as HTMLElement).tagName === 'P') {
            wordSpan.className = 'vocab-word user-clickable'
          }
          fragment.appendChild(wordSpan)
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
    containerRef.current.setAttribute(DATA_ATTR.PROCESSED, 'true')
  }, [content, clickable, articleId, onAddVocabulary])

  // Event delegation for word clicks (avoids stale closure issues)
  useEffect(() => {
    const container = containerRef.current
    if (!container || !clickable) return

    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (target.classList.contains('vocab-word') && target.classList.contains('user-clickable')) {
        e.preventDefault()  // Prevent any default browser behavior
        e.stopPropagation()
        const spanId = target.getAttribute(DATA_ATTR.SPAN_ID)
        const word = target.getAttribute(DATA_ATTR.WORD)
        if (spanId && word) {
          handleWordClickRef.current(spanId, word)
        }
      }
    }

    container.addEventListener('click', handleClick)
    return () => {
      container.removeEventListener('click', handleClick)
    }
  }, [clickable])

  // Vocabulary highlighting: highlight vocabularies based on span_id and related_words
  useEffect(() => {
    if (!containerRef.current) return
    
    // Remove all vocab-saved classes first
    containerRef.current.querySelectorAll('.vocab-saved').forEach(el => {
      el.classList.remove(CSS_CLASS.VOCAB_SAVED)
    })
    
    // Process each vocabulary
    vocabularies.forEach(v => {
      if (!v.span_id || !v.related_words || v.related_words.length === 0) return
      
      const spanId = v.span_id
      
      // Find the clicked word's span by span_id
      const clickedSpan = containerRef.current!.querySelector(`[data-span-id="${spanId}"]`) as HTMLElement
      if (!clickedSpan) return
      
      // Get all vocab-word spans in container, in DOM order
      const allSpans = Array.from(containerRef.current!.querySelectorAll('.vocab-word')) as HTMLElement[]
      
      // Find clicked span index
      const clickedIndex = allSpans.findIndex(span => span.getAttribute(DATA_ATTR.SPAN_ID) === spanId)
      if (clickedIndex === -1) return
      
      // Find clicked word's index in related_words array
      const clickedWord = clickedSpan.getAttribute(DATA_ATTR.WORD)
      if (!clickedWord) return
      
      const clickedWordIndex = v.related_words.findIndex(w => w.toLowerCase() === clickedWord.toLowerCase())
      if (clickedWordIndex === -1) return
      
      // Color clicked word first
      clickedSpan.classList.add(CSS_CLASS.VOCAB_SAVED)
      
      // Find words to the left (before clicked word in related_words)
      // Search backwards from clickedIndex
      for (let i = clickedWordIndex - 1; i >= 0; i--) {
        const targetWord = v.related_words[i]
        let found = false
        
        // Search backwards from clickedIndex
        for (let j = clickedIndex - 1; j >= 0; j--) {
          const span = allSpans[j]
          const word = span.getAttribute(DATA_ATTR.WORD)
          
          if (word && word.toLowerCase() === targetWord.toLowerCase()) {
            span.classList.add(CSS_CLASS.VOCAB_SAVED)
            found = true
            break
          }
        }
        
        if (!found) break // If we can't find a word, stop searching
      }
      
      // Find words to the right (after clicked word in related_words)
      // Search forwards from clickedIndex
      for (let i = clickedWordIndex + 1; i < v.related_words.length; i++) {
        const targetWord = v.related_words[i]
        let found = false
        
        // Search forwards from clickedIndex
        for (let j = clickedIndex + 1; j < allSpans.length; j++) {
          const span = allSpans[j]
          const word = span.getAttribute(DATA_ATTR.WORD)
          
          if (word && word.toLowerCase() === targetWord.toLowerCase()) {
            span.classList.add(CSS_CLASS.VOCAB_SAVED)
            found = true
            break
          }
        }
        
        if (!found) break // If we can't find a word, stop searching
      }
    })
  }, [vocabularies])

  // Update definition visibility when openSpanIds change
  useEffect(() => {
    if (!containerRef.current) return
    
    // Remove definitions for spans that are no longer open
    containerRef.current.querySelectorAll('.word-definition').forEach(defSpan => {
      const prevSpan = defSpan.previousElementSibling as HTMLElement
      if (prevSpan && prevSpan.classList.contains('vocab-word')) {
        const spanId = prevSpan.getAttribute(DATA_ATTR.SPAN_ID)
        if (spanId && !openSpanIds.has(spanId)) {
          const afterDef = defSpan.nextSibling
          defSpan.remove()
          if (afterDef) {
            prevSpan.parentNode?.insertBefore(afterDef, prevSpan.nextSibling)
          }
        }
      }
    })
    
    // Add definitions for open spans
    openSpanIds.forEach(spanId => {
      const span = containerRef.current!.querySelector(`[data-span-id="${spanId}"]`) as HTMLElement
      if (!span) return
      
      const word = span.getAttribute(DATA_ATTR.WORD)
      if (!word) return
      
      const { meaning, displayLemma } = getWordMeaning(word)
      const isLoading = loadingWords.has(word) || loadingWordsRef.current.has(word)
      
      // Remove existing definition if it exists
      const existingDef = span.nextElementSibling
      if (existingDef && existingDef.classList.contains('word-definition')) {
        const afterDef = existingDef.nextSibling
        existingDef.remove()
        if (afterDef) {
          span.parentNode?.insertBefore(afterDef, span.nextSibling)
        }
      }
      
      // Only show if loading or has meaning
      if (isLoading || meaning) {
        const afterWord = span.nextSibling
        const defSpan = document.createElement('span')
        defSpan.className = 'word-definition'
        
        if (isLoading && !meaning) {
          // Use DOM methods instead of innerHTML to prevent XSS
          const strong = document.createElement('strong')
          strong.textContent = word
          const em = document.createElement('em')
          em.textContent = 'Loading...'
          defSpan.appendChild(strong)
          defSpan.appendChild(document.createTextNode(': '))
          defSpan.appendChild(em)
        } else if (meaning) {
          const isInVocabulary = vocabularies.some(v => v.lemma.toLowerCase() === displayLemma.toLowerCase())
          const sentence = extractSentence(span)
          const relatedWords = getRelatedWords(word)

          // Get additional fields from cache
          const wordCacheKey = language ? `${language}:${word.toLowerCase()}` : null
          let pos: string | undefined
          let gender: string | undefined
          let conjugations: { present?: string, past?: string, perfect?: string } | undefined
          let level: string | undefined

          if (wordCacheKey && lemmaCacheRef.current.has(wordCacheKey)) {
            const cached = lemmaCacheRef.current.get(wordCacheKey)
            if (cached) {
              try {
                const parsedCache = JSON.parse(cached)
                pos = parsedCache.pos
                gender = parsedCache.gender
                conjugations = parsedCache.conjugations
                level = parsedCache.level
              } catch {
                // Ignore parse error
              }
            }
          }

          // Use DOM methods instead of innerHTML to prevent XSS
          const strong = document.createElement('strong')
          strong.textContent = displayLemma
          defSpan.appendChild(strong)
          defSpan.appendChild(document.createTextNode(': ' + meaning))

          if (articleId && onAddVocabulary) {
            const buttonHtml = createVocabularyButtonHTML(word, displayLemma, meaning, sentence, relatedWords, spanId, isInVocabulary, pos, gender, conjugations, level)
            // Create a temporary container to parse the button HTML
            const tempDiv = document.createElement('div')
            tempDiv.innerHTML = buttonHtml.trim()  // trim() to remove leading space
            const button = tempDiv.firstElementChild  // Use firstElementChild, not firstChild
            if (button) {
              defSpan.appendChild(button)
            }
          }
          
          const addBtn = defSpan.querySelector('.vocab-add')
          const removeBtn = defSpan.querySelector('.vocab-remove')
          
          if (addBtn) {
            addBtn.addEventListener('click', (e) => {
              e.stopPropagation()
              handleAddVocabularyClick(e.currentTarget as HTMLElement)
            })
          }
          
          if (removeBtn) {
            removeBtn.addEventListener('click', (e) => {
              e.stopPropagation()
              handleRemoveVocabularyClick(e.currentTarget as HTMLElement)
            })
          }
        }
        
        span.parentNode?.insertBefore(defSpan, afterWord)

        if (afterWord) {
          span.parentNode?.insertBefore(afterWord, defSpan.nextSibling)
        }
      }
    })
  }, [openSpanIds, wordDefinitions, loadingWords, vocabularies, articleId, onAddVocabulary, language, getWordMeaning, getRelatedWords, createVocabularyButtonHTML, handleAddVocabularyClick, handleRemoveVocabularyClick])

  const className = dark
    ? "prose prose-invert max-w-none text-foreground prose-headings:text-accent prose-headings:font-mono prose-p:text-foreground prose-strong:text-text-strong prose-li:text-foreground prose-ul:text-foreground prose-ol:text-foreground prose-a:text-vocab prose-a:no-underline hover:prose-a:text-vocab/80 prose-code:text-vocab prose-code:font-mono prose-pre:bg-card-hover prose-blockquote:text-text-dim prose-blockquote:border-border-card"
    : "prose max-w-none prose-headings:text-foreground prose-p:text-foreground prose-strong:text-text-strong prose-li:text-foreground prose-ul:text-foreground prose-ol:text-foreground prose-a:text-accent prose-a:no-underline hover:prose-a:text-accent/80 prose-code:text-vocab prose-pre:bg-card-hover prose-blockquote:text-text-dim prose-blockquote:border-border-card"

  return (
    <div className={className} ref={containerRef}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}

