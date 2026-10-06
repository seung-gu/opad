'use client'

import { useState, FormEvent } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import Link from 'next/link'

export default function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    // Form validation
    if (!email || !password) {
      setError('Email and password are required')
      return
    }

    if (!email.includes('@')) {
      setError('Please enter a valid email address')
      return
    }

    setLoading(true)

    try {
      await login(email, password)
      // Redirect is handled by AuthContext
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
        <Link href="/" className="text-[13px] text-text-dim transition-colors hover:text-accent">
          One story a day
        </Link>

        <h1 className="mt-10 font-serif text-[34px] leading-tight text-text-strong">Sign in</h1>
        <p className="mt-2 text-[14px] text-text-dim">
          New here?{' '}
          <Link href="/register" className="text-accent">
            Create an account
          </Link>
        </p>

        <form className="mt-10 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="border-l-2 border-accent-danger pl-4">
              <p className="text-[12px] font-medium text-accent-danger">Error</p>
              <p className="mt-0.5 text-[14px] text-foreground">{error}</p>
            </div>
          )}

          <div className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-[12px] text-text-dim">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                className="mt-1 w-full border-b border-border-card bg-transparent py-2 text-[15px] text-foreground transition-colors placeholder:text-text-dim focus:border-accent focus:outline-none disabled:opacity-50"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-[12px] text-text-dim">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                className="mt-1 w-full border-b border-border-card bg-transparent py-2 text-[15px] text-foreground transition-colors placeholder:text-text-dim focus:border-accent focus:outline-none disabled:opacity-50"
              />
            </div>
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </main>
    </div>
  )
}
