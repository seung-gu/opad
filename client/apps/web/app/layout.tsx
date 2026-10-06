import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import { Noto_Sans_KR, JetBrains_Mono, Newsreader } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/contexts/AuthContext'

const notoSansKR = Noto_Sans_KR({
  subsets: ['latin'],
  weight: ['300', '400', '600', '700'],
  variable: '--font-sans',
  display: 'swap',
})

const newsreader = Newsreader({
  subsets: ['latin'],
  weight: ['300', '400', '500'],
  style: ['normal', 'italic'],
  variable: '--font-serif',
  display: 'swap',
  fallback: ['Georgia', 'serif'],
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '600', '700'],
  variable: '--font-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'One story a day',
  description: 'Educational reading materials for language learners',
}

export default function RootLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <html lang="en" className={`${notoSansKR.variable} ${newsreader.variable} ${jetbrainsMono.variable}`}>
      <body className="bg-background text-foreground font-sans">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}

