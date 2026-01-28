"use client"

import { useState, useEffect } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts'

interface HistoryDataPoint {
  web2: number | null
  poly: number | null
  time: string
  timeLabel?: string
}

interface OddsHistoryCardProps {
  eventId: string
  eventType: 'championship' | 'daily'
  sportType: string
  teamName: string
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

export function OddsHistoryCard({ eventId, eventType, sportType, teamName }: OddsHistoryCardProps) {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<HistoryDataPoint[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId])

  const fetchHistory = async () => {
    setLoading(true)
    setError(null)

    const url = `/api/history/${encodeURIComponent(eventId)}?type=${eventType}&sport=${sportType}`
    console.log('[OddsHistoryCard] Fetching:', url)

    try {
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error('Failed to fetch history')
      }

      const result = await response.json()
      console.log('[OddsHistoryCard] Response:', result.success, 'Data count:', result.data?.length)

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
      console.error('[OddsHistoryCard] Error:', err)
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
    <section className="bg-[#161b22] rounded-xl border border-[#30363d] p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-[#e6edf3] flex items-center gap-2">
          <span>📈</span>
          <span>Odds History</span>
        </h2>
        {data.length > 0 && (
          <span className="text-xs text-[#8b949e]">
            {data.length} data points
          </span>
        )}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12 text-[#8b949e]">
          <span className="animate-pulse">Loading history...</span>
        </div>
      )}

      {error && !loading && (
        <div className="flex items-center justify-center py-12 text-[#8b949e]">
          <span>{error}</span>
        </div>
      )}

      {!loading && !error && data.length > 0 && (
        <div className="bg-[#0d1117] rounded-lg p-4">
          <div className="text-sm text-[#e6edf3] mb-3 font-medium">{teamName}</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
              <XAxis
                dataKey="timeLabel"
                tick={{ fill: '#8b949e', fontSize: 11 }}
                axisLine={{ stroke: '#30363d' }}
                tickLine={{ stroke: '#30363d' }}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fill: '#8b949e', fontSize: 11 }}
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
              <Line
                type="monotone"
                dataKey="web2"
                name="Trad Implied"
                stroke="#d29922"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#d29922' }}
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
          <div className="flex justify-center gap-6 mt-3 text-xs">
            <span className="flex items-center gap-2">
              <span className="inline-block w-4 h-0.5 bg-[#d29922]"></span>
              <span className="text-[#8b949e]">Traditional Odds</span>
            </span>
            <span className="flex items-center gap-2">
              <span className="inline-block w-4 h-0.5 bg-[#58a6ff]"></span>
              <span className="text-[#8b949e]">Polymarket</span>
            </span>
          </div>
        </div>
      )}

      {!loading && !error && data.length === 0 && (
        <div className="flex items-center justify-center py-12 text-[#8b949e]">
          <span>No history data yet. Check back after a few updates.</span>
        </div>
      )}
    </section>
  )
}
