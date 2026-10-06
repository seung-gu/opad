'use client'

import { useState, FormEvent } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import Link from 'next/link'

export default function RegisterPage() {
  const { register } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    // Form validation
    if (!name || !email || !password || !confirmPassword) {
      setError('All fields are required')
      return
    }

    if (!email.includes('@')) {
      setError('Please enter a valid email address')
      return
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setLoading(true)

    try {
      await register(email, password, name)
      // Redirect is handled by AuthContext
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed')
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

        <h1 className="mt-10 font-serif text-[34px] leading-tight text-text-strong">Create an account</h1>
        <p className="mt-2 text-[14px] text-text-dim">
          Already have one?{' '}
          <Link href="/login" className="text-accent">
            Sign in
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
              <label htmlFor="name" className="block text-[12px] text-text-dim">
                Full name
              </label>
              <input
                id="name"
                name="name"
                type="text"
                autoComplete="name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={loading}
                className="mt-1 w-full border-b border-border-card bg-transparent py-2 text-[15px] text-foreground transition-colors placeholder:text-text-dim focus:border-accent focus:outline-none disabled:opacity-50"
              />
            </div>
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
                Password (at least 8 characters)
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                className="mt-1 w-full border-b border-border-card bg-transparent py-2 text-[15px] text-foreground transition-colors placeholder:text-text-dim focus:border-accent focus:outline-none disabled:opacity-50"
              />
            </div>
            <div>
              <label htmlFor="confirmPassword" className="block text-[12px] text-text-dim">
                Confirm password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={loading}
                className="mt-1 w-full border-b border-border-card bg-transparent py-2 text-[15px] text-foreground transition-colors placeholder:text-text-dim focus:border-accent focus:outline-none disabled:opacity-50"
              />
            </div>
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>
      </main>
    </div>
  )
}
