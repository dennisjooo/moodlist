'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface RemixItem {
  id: number
  name: string
  remix_type: string
  remix_generation: number
  created_at: string
  track_count: number
}

interface RemixHistoryProps {
  playlistId: number
}

const REMIX_TYPE_ICONS: Record<string, string> = {
  energy: '⚡',
  mood: '😊',
  tempo: '🎵',
  genre: '🎸',
  danceability: '💃',
}

const REMIX_TYPE_COLORS: Record<string, string> = {
  energy: 'from-yellow-400 to-orange-500',
  mood: 'from-pink-400 to-rose-500',
  tempo: 'from-blue-400 to-indigo-500',
  genre: 'from-purple-400 to-indigo-500',
  danceability: 'from-green-400 to-emerald-500',
}

export function RemixHistory({ playlistId }: RemixHistoryProps) {
  const [remixes, setRemixes] = useState<RemixItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRemixes()
  }, [playlistId])

  const loadRemixes = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await fetch(`/api/playlists/${playlistId}/remixes`)
      if (!response.ok) throw new Error('Failed to load remixes')
      const data = await response.json()
      setRemixes(data.remixes || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load remixes')
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return <div className="py-4 text-center text-sm text-gray-500">Loading remixes...</div>
  }

  if (error) {
    return <div className="py-4 text-center text-sm text-red-600">{error}</div>
  }

  if (!remixes || remixes.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center">
        <p className="text-sm text-gray-600">
          No remixes created yet. Try creating one!
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="mb-4 font-semibold text-gray-900">
        Remixes ({remixes.length})
      </h3>

      <div className="space-y-3">
        {remixes.map((remix) => (
          <Link
            key={remix.id}
            href={`/playlist/${remix.id}`}
            className="block rounded-lg border border-gray-200 p-3 transition-all hover:border-gray-300 hover:bg-gray-50"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-lg">
                    {REMIX_TYPE_ICONS[remix.remix_type] || '🔄'}
                  </span>
                  <h4 className="font-medium text-gray-900">{remix.name}</h4>
                </div>

                <div className="mt-1 flex items-center gap-2">
                  <span
                    className={`inline-block rounded-full bg-gradient-to-r ${
                      REMIX_TYPE_COLORS[remix.remix_type] ||
                      'from-gray-400 to-gray-500'
                    } px-2 py-1 text-xs font-semibold text-white`}
                  >
                    {remix.remix_type.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs text-gray-600">
                    Gen {remix.remix_generation} • {remix.track_count} tracks
                  </span>
                </div>

                <p className="mt-2 text-xs text-gray-500">
                  Created {new Date(remix.created_at).toLocaleDateString()}
                </p>
              </div>

              <div className="flex-shrink-0 text-right text-sm text-gray-400">
                <svg
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
