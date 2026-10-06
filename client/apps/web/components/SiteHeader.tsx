'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

const NAV = [
  { label: 'Articles', href: '/articles' },
  { label: 'Vocabulary', href: '/vocabulary' },
  { label: 'Usage', href: '/usage' },
]

/**
 * Masthead shared by every page.
 *
 * `title` fills the left slot; the home page leaves it out because its hero
 * already carries the name.
 */
export default function SiteHeader({ title }: Readonly<{ title?: string }>) {
  const pathname = usePathname()
  const { isAuthenticated, user, logout } = useAuth()

  return (
    <header className="border-b-[3px] border-double border-border-card">
      <div
        className={`mx-auto flex max-w-5xl flex-wrap items-baseline gap-y-2 px-6 py-5 ${
          title ? 'justify-between' : 'justify-end'
        }`}
      >
        {title && (
          <Link href="/" className="font-serif text-[17px] italic text-text-dim transition-colors hover:text-accent">
            {title}
          </Link>
        )}

        <nav className="flex flex-wrap items-baseline justify-end gap-x-5 gap-y-1 text-[13px]">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`whitespace-nowrap transition-colors hover:text-accent ${
                pathname === item.href ? 'text-accent' : 'text-text-dim'
              }`}
            >
              {item.label}
            </Link>
          ))}
          {isAuthenticated ? (
            <span className="flex items-baseline gap-3 whitespace-nowrap">
              <span className="text-foreground">{user?.name || user?.email}</span>
              <button type="button" onClick={logout} className="text-text-dim transition-colors hover:text-accent">
                Sign out
              </button>
            </span>
          ) : (
            <Link href="/login" className="whitespace-nowrap text-accent">
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  )
}
