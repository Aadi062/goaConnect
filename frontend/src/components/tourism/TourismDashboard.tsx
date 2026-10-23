import React, { useState } from 'react'
import { useTravelAssistant, usePlaces } from '../../hooks/useTourism'
import type { AgentTaskResult, Place } from '../../types'

function PlaceCard({ place }: { place: Place }) {
  return (
    <div className="bg-amber-900/20 border border-amber-700/40 rounded-lg p-4 hover:border-amber-500/60 transition-colors">
      <div className="flex items-start justify-between">
        <h3 className="font-medium text-amber-100">{place.name}</h3>
        {place.is_verified && (
          <span className="text-xs text-green-400 font-mono ml-2 shrink-0">✓ verified</span>
        )}
      </div>
      {place.name_konkani && (
        <p className="text-xs text-amber-400/70 mt-0.5 italic">{place.name_konkani}</p>
      )}
      <div className="flex gap-2 mt-2 flex-wrap">
        <span className="text-xs bg-amber-800/40 text-amber-300 px-2 py-0.5 rounded">{place.category}</span>
        {place.district && (
          <span className="text-xs text-amber-500">{place.district}</span>
        )}
      </div>
      {place.description && (
        <p className="text-sm text-amber-200/70 mt-2 line-clamp-2">{place.description}</p>
      )}
      {place.source_citations?.length ? (
        <p className="text-xs text-amber-600 mt-2">
          📚 {place.source_citations.length} citation(s)
        </p>
      ) : null}
    </div>
  )
}

export default function TourismDashboard() {
  const [query, setQuery] = useState('')
  const [days, setDays] = useState(3)
  const [budget, setBudget] = useState(10000)
  const [result, setResult] = useState<AgentTaskResult | null>(null)
  const { data: places, isLoading: placesLoading } = usePlaces()
  const assistant = useTravelAssistant()

  const handleQuery = async () => {
    const res = await assistant.mutateAsync({
      task_type: 'travel_query',
      payload: { query, days, budget_inr: budget },
    })
    setResult(res)
  }

  const handleItinerary = async () => {
    const res = await assistant.mutateAsync({
      task_type: 'itinerary',
      payload: { days, budget_inr: budget, group_size: 2 },
    })
    setResult(res)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-950 via-orange-950 to-slate-950 p-4 text-slate-100">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-amber-300">🌴 GoaConnect AI Travel Assistant</h1>
          <p className="text-amber-500/70 text-sm mt-1">Beaches · Heritage · Culture · Cuisine · Community</p>
        </div>

        {/* Search Bar */}
        <div className="bg-amber-900/20 border border-amber-700/40 rounded-xl p-6 mb-6">
          <div className="flex gap-3 mb-4">
            <input
              className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500"
              placeholder="Ask anything about Goa… beaches, heritage, food, festivals"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleQuery()}
            />
            <button
              onClick={handleQuery}
              disabled={!query || assistant.isPending}
              className="px-5 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
            >
              {assistant.isPending ? '…' : 'Ask'}
            </button>
          </div>
          <div className="flex gap-6 text-sm">
            <label className="flex items-center gap-2 text-amber-300">
              Days:
              <input
                type="number" min={1} max={14} value={days}
                onChange={e => setDays(Number(e.target.value))}
                className="w-16 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-center text-slate-100"
              />
            </label>
            <label className="flex items-center gap-2 text-amber-300">
              Budget ₹:
              <input
                type="number" min={1000} step={1000} value={budget}
                onChange={e => setBudget(Number(e.target.value))}
                className="w-28 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-slate-100"
              />
            </label>
            <button
              onClick={handleItinerary}
              className="ml-auto text-xs text-amber-400 hover:text-amber-200 underline"
            >
              Generate Itinerary →
            </button>
          </div>
        </div>

        {/* AI Response */}
        {result && (
          <div className="bg-amber-900/20 border border-amber-600/40 rounded-xl p-6 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-amber-300">AI Response</h3>
              <span className="text-xs text-amber-600 font-mono">
                confidence: {Math.round(result.confidence * 100)}%
              </span>
            </div>

            {/* Travel query result */}
            {result.result?.response && (
              <p className="text-amber-100 text-sm leading-relaxed">{result.result.response as string}</p>
            )}

            {/* Itinerary result */}
            {result.result?.itinerary && (
              <div className="mt-4 space-y-3">
                {(result.result.itinerary as Array<{day: number; theme: string; places: string[]; estimated_cost_inr: number}>).map(day => (
                  <div key={day.day} className="bg-slate-900/40 rounded-lg p-3">
                    <p className="text-amber-400 font-medium text-sm">Day {day.day}: {day.theme}</p>
                    <p className="text-xs text-slate-300 mt-1">{day.places.join(' → ')}</p>
                    <p className="text-xs text-amber-600 mt-1">Est. ₹{day.estimated_cost_inr}/person</p>
                  </div>
                ))}
              </div>
            )}

            {/* Recommendations */}
            {result.result?.recommendations && (
              <div className="flex flex-wrap gap-2 mt-3">
                {(result.result.recommendations as string[]).map(r => (
                  <span key={r} className="text-xs bg-amber-800/40 text-amber-300 px-3 py-1 rounded-full">{r}</span>
                ))}
              </div>
            )}

            {/* Citations */}
            {(result.result?.source_citations as string[])?.length > 0 && (
              <div className="mt-3 pt-3 border-t border-amber-800/40">
                <p className="text-xs text-amber-600 mb-1">Sources:</p>
                {(result.result.source_citations as string[]).map(c => (
                  <p key={c} className="text-xs text-amber-700">{c}</p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Places Grid */}
        <div>
          <h2 className="text-lg font-medium text-amber-300 mb-4">Explore Goa</h2>
          {placesLoading ? (
            <div className="text-center text-amber-600 py-8">Loading places…</div>
          ) : !places?.length ? (
            <div className="text-center text-amber-700 py-8">
              No places yet — add places via the API or database seed
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {places.map(p => <PlaceCard key={p.id} place={p} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
