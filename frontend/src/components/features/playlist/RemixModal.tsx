'use client'

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface RemixOption {
  type: string
  name: string
  description: string
  parameters: Record<string, any>
}

interface RemixModalProps {
  isOpen: boolean
  onClose: () => void
  playlistId: number
  playlistName: string
  onRemixCreated?: (remixData: any) => void
  onStartWorkflow?: (moodPrompt: string, remixData: any) => void
}

const REMIX_TYPES: Record<string, { icon: string; color: string }> = {
  energy: { icon: '⚡', color: 'from-yellow-400 to-orange-500' },
  mood: { icon: '😊', color: 'from-pink-400 to-rose-500' },
  tempo: { icon: '🎵', color: 'from-blue-400 to-indigo-500' },
  genre: { icon: '🎸', color: 'from-purple-400 to-indigo-500' },
  danceability: { icon: '💃', color: 'from-green-400 to-emerald-500' },
}

export function RemixModal({
  isOpen,
  onClose,
  playlistId,
  playlistName,
  onRemixCreated,
  onStartWorkflow,
}: RemixModalProps) {
  const [remixOptions, setRemixOptions] = useState<RemixOption[]>([])
  const [selectedRemixType, setSelectedRemixType] = useState<string | null>(null)
  const [remixParameters, setRemixParameters] = useState<Record<string, any>>({})
  const [customMood, setCustomMood] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load remix options when modal opens
  useEffect(() => {
    if (isOpen) {
      loadRemixOptions()
    }
  }, [isOpen])

  const loadRemixOptions = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await fetch(`/api/playlists/${playlistId}/remix-options`)
      if (!response.ok) throw new Error('Failed to load remix options')
      const data = await response.json()
      setRemixOptions(data.remix_types || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load remix options')
    } finally {
      setIsLoading(false)
    }
  }

  const handleRemixTypeSelect = (type: string) => {
    setSelectedRemixType(type)
    const option = remixOptions.find((o) => o.type === type)
    if (option && option.parameters) {
      const initialParams: Record<string, any> = {}
      Object.entries(option.parameters).forEach(([key, param]) => {
        if (param.default !== undefined) {
          initialParams[key] = param.default
        }
      })
      setRemixParameters(initialParams)
    }
  }

  const handleParameterChange = (paramKey: string, value: any) => {
    setRemixParameters((prev) => ({
      ...prev,
      [paramKey]: value,
    }))
  }

  const handleCreateRemix = async () => {
    if (!selectedRemixType) return

    try {
      setIsLoading(true)
      setError(null)

      const response = await fetch(`/api/playlists/${playlistId}/create-remix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          remix_type: selectedRemixType,
          remix_parameters: remixParameters,
          custom_mood: customMood || undefined,
        }),
      })

      if (!response.ok) throw new Error('Failed to create remix')
      const remixData = await response.json()

      onRemixCreated?.(remixData)
      if (onStartWorkflow) {
        onStartWorkflow(remixData.mood_prompt, remixData)
      }

      // Reset and close
      setSelectedRemixType(null)
      setRemixParameters({})
      setCustomMood('')
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create remix')
    } finally {
      setIsLoading(false)
    }
  }

  const selectedOption = remixOptions.find((o) => o.type === selectedRemixType)

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create Remix</DialogTitle>
          <DialogDescription>
            Create a variation of "{playlistName}" with different parameters
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="rounded-md bg-red-50 p-4 text-sm text-red-800">
            {error}
          </div>
        )}

        {isLoading && !remixOptions.length ? (
          <div className="py-8 text-center">Loading remix options...</div>
        ) : (
          <div className="space-y-6">
            {/* Remix Type Selection */}
            <div>
              <h3 className="mb-3 font-semibold text-gray-900">
                Choose Remix Type
              </h3>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {remixOptions.map((option) => (
                  <button
                    key={option.type}
                    onClick={() => handleRemixTypeSelect(option.type)}
                    disabled={isLoading}
                    className={`group relative overflow-hidden rounded-lg p-4 text-left transition-all ${
                      selectedRemixType === option.type
                        ? 'ring-2 ring-blue-500 ring-offset-2'
                        : 'border border-gray-200 hover:border-gray-300'
                    } disabled:opacity-50`}
                  >
                    {/* Background gradient */}
                    <div
                      className={`absolute inset-0 bg-gradient-to-br ${
                        REMIX_TYPES[option.type]?.color || 'from-gray-400 to-gray-500'
                      } opacity-0 transition-opacity group-hover:opacity-10`}
                    />

                    {/* Content */}
                    <div className="relative z-10">
                      <div className="text-2xl">
                        {REMIX_TYPES[option.type]?.icon || '🎵'}
                      </div>
                      <h4 className="mt-2 font-semibold text-gray-900">
                        {option.name}
                      </h4>
                      <p className="mt-1 text-xs text-gray-600">
                        {option.description}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Parameter Controls */}
            {selectedOption && (
              <div className="space-y-4">
                <h3 className="font-semibold text-gray-900">
                  {selectedOption.name} Parameters
                </h3>

                {Object.entries(selectedOption.parameters).map(([paramKey, param]) => (
                  <div key={paramKey}>
                    <label className="block text-sm font-medium text-gray-700">
                      {paramKey.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())}
                    </label>

                    {param.type === 'slider' ? (
                      <div className="mt-2 space-y-2">
                        <input
                          type="range"
                          min={param.min}
                          max={param.max}
                          step={param.step}
                          value={remixParameters[paramKey] || param.default}
                          onChange={(e) =>
                            handleParameterChange(paramKey, Number(e.target.value))
                          }
                          disabled={isLoading}
                          className="w-full"
                        />
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-500">
                            {param.min} {param.unit}
                          </span>
                          <span className="text-sm font-semibold text-gray-900">
                            {remixParameters[paramKey] || param.default} {param.unit}
                          </span>
                          <span className="text-xs text-gray-500">
                            {param.max} {param.unit}
                          </span>
                        </div>
                      </div>
                    ) : param.type === 'select' ? (
                      <select
                        value={remixParameters[paramKey] || param.default}
                        onChange={(e) => handleParameterChange(paramKey, e.target.value)}
                        disabled={isLoading}
                        className="mt-2 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      >
                        {param.options?.map((option: string) => (
                          <option key={option} value={option}>
                            {option.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())}
                          </option>
                        ))}
                      </select>
                    ) : null}
                  </div>
                ))}
              </div>
            )}

            {/* Custom Mood Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Custom Mood (Optional)
              </label>
              <textarea
                value={customMood}
                onChange={(e) => setCustomMood(e.target.value)}
                placeholder="Override the default remix prompt..."
                disabled={isLoading}
                rows={3}
                className="mt-2 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={handleCreateRemix}
                disabled={!selectedRemixType || isLoading}
              >
                {isLoading ? 'Creating...' : 'Create Remix'}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
