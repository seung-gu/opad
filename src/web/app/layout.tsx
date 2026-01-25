import type { Metadata } from 'next'
import './globals.css'
import { AuthProvider } from '@/contexts/AuthContext'

export const metadata: Metadata = {
  title: 'OPAD - Reading Materials',
  description: 'Educational reading materials for language learners',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-white text-gray-900">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}

