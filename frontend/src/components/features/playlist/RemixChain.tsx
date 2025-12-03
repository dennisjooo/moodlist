'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface RemixChainItem {
  id: number
  name: string
  mood_prompt: string
  is_remix: boolean
  remix_type?: string
  remix_generation: number
  created_at: string
}

interface RemixChainProps {
  playlistId: number
}

const REMIX_TYPE_ICONS: Record<string, string> = {
  energy: '⚡',
  mood: '😊',
  tempo: '🎵',
  genre: '🎸',
  danceability: '💃',
}

export function RemixChain({ playlistId }: RemixChainProps) {
  const [chain, setChain] = useState<RemixChainItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRemixChain()
  }, [playlistId])

  const loadRemixChain = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await fetch(`/api/playlists/${playlistId}/remix-chain`)
      if (!response.ok) throw new Error('Failed to load remix chain')
      const data = await response.json()
      setChain(data.remix_chain || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load remix chain')
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return <div className="py-4 text-center text-sm text-gray-500">Loading version history...</div>
  }

  if (error) {
    return <div className="py-4 text-center text-sm text-red-600">{error}</div>
  }

  if (!chain || chain.length === 0) {
    return null
  }

  if (chain.length === 1 && !chain[0].is_remix) {
    return null
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
      <h3 className="mb-4 font-semibold text-gray-900">Version History</h3>

      <div className="space-y-0">
        {chain.map((item, index) => (
          <div key={item.id} className="relative flex">
            {/* Timeline line */}
            {index < chain.length - 1 && (
              <div className="absolute left-4 top-12 h-4 w-0.5 bg-gray-300" />
            )}

            {/* Timeline dot */}
            <div className="relative z-10 mr-4 flex flex-col items-center">
              <div
                className={`flex h-9 w-9 items-center justify-center rounded-full ${
                  item.is_remix
                    ? 'bg-gradient-to-br from-purple-400 to-indigo-500 text-white'
                    : 'bg-blue-500 text-white'
                } flex-shrink-0 text-sm font-semibold`}
              >
                {item.is_remix ? (
                  <span>{REMIX_TYPE_ICONS[item.remix_type || 'remix'] || '🔄'}</span>
                ) : (
                  <span>✓</span>
                )}
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 py-2 pb-4">
              <Link
                href={`/playlist/${item.id}`}
                className="block hover:underline"
              >
                <h4 className="font-medium text-gray-900">{item.name}</h4>
              </Link>

              {item.is_remix && item.remix_type && (
                <p className="mt-1 text-xs text-gray-600">
                  <span className="inline-block rounded-full bg-purple-100 px-2 py-1 text-purple-800">
                    {item.remix_type.replace(/_/g, ' ')} Remix
                  </span>
                </p>
              )}

              <p className="mt-1 text-sm text-gray-600 line-clamp-2">
                {item.mood_prompt}
              </p>

              <p className="mt-1 text-xs text-gray-500">
                {new Date(item.created_at).toLocaleDateString()} •{' '}
                Generation {item.remix_generation}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
