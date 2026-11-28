import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import './fonts.css'
import './globals.css'
import { AuthProvider } from '@/contexts/AuthContext'

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
    <html lang="en">
      <body className="bg-background text-foreground font-sans">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}

