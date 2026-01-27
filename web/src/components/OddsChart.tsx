"use client"

import { useState, useEffect } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'

interface HistoryDataPoint {
  web2: number | null
  poly: number | null
  time: string
  timeLabel?: string
}

interface OddsChartProps {
  eventId: string
  eventType: 'championship' | 'daily'
  sportType: string
  teamName?: string
}

// Aggregate data by day - take the last value of each day
function aggregateByDay(data: HistoryDataPoint[]): HistoryDataPoint[] {
  const dayMap = new Map<string, HistoryDataPoint>()

  for (const point of data) {
    const date = new Date(point.time)
    const dayKey = `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
    // Keep the latest value for each day
    dayMap.set(dayKey, point)
  }

  return Array.from(dayMap.values()).sort((a, b) =>
    new Date(a.time).getTime() - new Date(b.time).getTime()
  )
}

export function OddsChart({ eventId, eventType, sportType, teamName }: OddsChartProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<HistoryDataPoint[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isExpanded && data.length === 0) {
      fetchHistory()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isExpanded])

  const fetchHistory = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(
        `/api/history/${encodeURIComponent(eventId)}?type=${eventType}&sport=${sportType}`
      )

      if (!response.ok) {
        throw new Error('Failed to fetch history')
      }

      const result = await response.json()

      if (result.success && result.data && result.data.length > 0) {
        // Aggregate by day for cleaner display
        const aggregated = aggregateByDay(result.data)

        // Format time display (date only, no hours)
        const formattedData = aggregated.map((d: HistoryDataPoint) => ({
          ...d,
          timeLabel: formatTime(d.time)
        }))
        setData(formattedData)
      } else {
        setError('No history data available')
      }
    } catch (err) {
      setError('Failed to load history')
      console.error('[OddsChart] Error:', err)
    } finally {
      setLoading(false)
    }
  }

  // Format as date only (e.g., "Jan 20")
  const formatTime = (isoString: string) => {
    const date = new Date(isoString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    })
  }

  return (
    <div className="mt-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-xs text-[#8b949e] hover:text-[#e6edf3] transition-colors"
      >
        <span>{isExpanded ? '▼' : '▶'}</span>
        <span>Show History</span>
        <span>📉</span>
      </button>

      {isExpanded && (
        <div className="mt-3 bg-[#0d1117] rounded-lg p-3 border border-[#30363d]">
          {loading && (
            <div className="flex items-center justify-center py-8 text-[#8b949e]">
              <span className="animate-pulse">Loading history...</span>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center py-8 text-[#8b949e]">
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && data.length > 0 && (
            <div>
              {teamName && (
                <div className="text-sm text-[#e6edf3] mb-2 font-medium">{teamName}</div>
              )}
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                  <XAxis
                    dataKey="timeLabel"
                    tick={{ fill: '#8b949e', fontSize: 10 }}
                    axisLine={{ stroke: '#30363d' }}
                    tickLine={{ stroke: '#30363d' }}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    domain={['auto', 'auto']}
                    tick={{ fill: '#8b949e', fontSize: 10 }}
                    axisLine={{ stroke: '#30363d' }}
                    tickLine={{ stroke: '#30363d' }}
                    tickFormatter={(value) => `${value}%`}
                    width={45}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#161b22',
                      border: '1px solid #30363d',
                      borderRadius: '8px',
                      color: '#e6edf3'
                    }}
                    labelStyle={{ color: '#8b949e' }}
                    formatter={(value) => [typeof value === 'number' ? `${value.toFixed(1)}%` : 'N/A', '']}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: '12px' }}
                    iconType="line"
                  />
                  <Line
                    type="monotone"
                    dataKey="web2"
                    name="Trad Implied"
                    stroke="#f85149"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, fill: '#f85149' }}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="poly"
                    name="Polymarket"
                    stroke="#58a6ff"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, fill: '#58a6ff' }}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
              <div className="flex justify-center gap-4 mt-2 text-xs">
                <span className="flex items-center gap-1">
                  <span className="inline-block w-3 h-0.5 bg-[#f85149]"></span>
                  <span className="text-[#8b949e]">Trad Implied Probability</span>
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block w-3 h-0.5 bg-[#58a6ff]"></span>
                  <span className="text-[#8b949e]">Polymarket Price</span>
                </span>
              </div>
            </div>
          )}

          {!loading && !error && data.length === 0 && (
            <div className="flex items-center justify-center py-8 text-[#8b949e]">
              <span>No history data yet. Check back after a few updates.</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
