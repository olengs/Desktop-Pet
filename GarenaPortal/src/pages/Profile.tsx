import { useState } from 'react'
import { getAveragedProfile, getPlayedGames } from '../data/gameProfiles'
import { useAuth } from '../auth'

const SIZE = 400
const CENTER = SIZE / 2
const MAX_RADIUS = 120
const LABEL_RADIUS = 152
const RING_STEPS = [0.25, 0.5, 0.75, 1]
const SCALE_MAX = 10

function pointOnAxis(index: number, total: number, radius: number) {
  const angle = -Math.PI / 2 + (index * 2 * Math.PI) / total
  return {
    x: CENTER + Math.cos(angle) * radius,
    y: CENTER + Math.sin(angle) * radius,
    angle,
  }
}

function labelAnchor(angle: number): 'start' | 'middle' | 'end' {
  const cos = Math.cos(angle)
  if (cos > 0.15) return 'start'
  if (cos < -0.15) return 'end'
  return 'middle'
}

function Profile() {
  const { username } = useAuth()
  const games = getPlayedGames()
  const [selectedGame, setSelectedGame] = useState(games[0])
  const [hovered, setHovered] = useState<string | null>(null)
  const profile = getAveragedProfile(selectedGame)

  return (
    <section className="px-8 py-8 text-left">
      <h1>Profile{username ? ` · ${username}` : ''}</h1>
      <p style={{ color: 'var(--text)' }}>Playstyle by game, based on your recent matches.</p>

      <div className="mt-6 flex flex-wrap gap-2">
        {games.map((game) => (
          <button
            key={game}
            type="button"
            onClick={() => setSelectedGame(game)}
            className="rounded-full border px-3 py-1.5 text-sm transition-colors"
            style={
              game === selectedGame
                ? { borderColor: 'var(--accent-border)', background: 'var(--accent-bg)', color: 'var(--accent)' }
                : { borderColor: 'var(--border)', color: 'var(--text)' }
            }
          >
            {game}
          </button>
        ))}
      </div>

      {!profile || profile.metrics.length < 3 ? (
        <p className="mt-8" style={{ color: 'var(--text)' }}>
          Not enough matches yet to build a playstyle profile for this game.
        </p>
      ) : (
        <div className="mt-8 flex flex-col items-center gap-8 lg:flex-row lg:items-start">
          <svg
            viewBox={`0 0 ${SIZE} ${SIZE}`}
            className="w-full max-w-xl"
            role="img"
            aria-label={`Playstyle radar for ${profile.game}: ${profile.metrics
              .map((metric) => `${metric.label} ${metric.value} of ${SCALE_MAX}`)
              .join(', ')}`}
          >
            {RING_STEPS.map((step) => (
              <polygon
                key={step}
                points={profile.metrics
                  .map((_, i) => {
                    const p = pointOnAxis(i, profile.metrics.length, MAX_RADIUS * step)
                    return `${p.x},${p.y}`
                  })
                  .join(' ')}
                fill="none"
                stroke="var(--border)"
                strokeWidth={1}
              />
            ))}

            {profile.metrics.map((metric, i) => {
              const outer = pointOnAxis(i, profile.metrics.length, MAX_RADIUS)
              return (
                <line
                  key={metric.key}
                  x1={CENTER}
                  y1={CENTER}
                  x2={outer.x}
                  y2={outer.y}
                  stroke="var(--border)"
                  strokeWidth={1}
                />
              )
            })}

            <polygon
              points={profile.metrics
                .map((metric, i) => {
                  const p = pointOnAxis(i, profile.metrics.length, (MAX_RADIUS * metric.value) / SCALE_MAX)
                  return `${p.x},${p.y}`
                })
                .join(' ')}
              fill="var(--accent-bg)"
              stroke="var(--accent)"
              strokeWidth={2}
              strokeLinejoin="round"
            />

            {profile.metrics.map((metric, i) => {
              const p = pointOnAxis(i, profile.metrics.length, (MAX_RADIUS * metric.value) / SCALE_MAX)
              const isHovered = hovered === metric.key
              return (
                <g
                  key={metric.key}
                  tabIndex={0}
                  onMouseEnter={() => setHovered(metric.key)}
                  onMouseLeave={() => setHovered(null)}
                  onFocus={() => setHovered(metric.key)}
                  onBlur={() => setHovered(null)}
                  style={{ cursor: 'pointer', outline: 'none' }}
                >
                  <title>{`${metric.label}: ${metric.value} of ${SCALE_MAX}`}</title>
                  <circle cx={p.x} cy={p.y} r={14} fill="transparent" />
                  <circle cx={p.x} cy={p.y} r={isHovered ? 8 : 6} fill="var(--bg)" />
                  <circle cx={p.x} cy={p.y} r={isHovered ? 6 : 4} fill="var(--accent)" />
                </g>
              )
            })}

            {profile.metrics.map((metric, i) => {
              const p = pointOnAxis(i, profile.metrics.length, LABEL_RADIUS)
              const anchor = labelAnchor(p.angle)
              const isHovered = hovered === metric.key
              return (
                <text
                  key={metric.key}
                  x={p.x}
                  y={p.y}
                  textAnchor={anchor}
                  className="text-xs"
                  style={{ fontWeight: isHovered ? 600 : 400 }}
                >
                  <tspan x={p.x} dy="-6" style={{ fill: 'var(--text-h)' }}>
                    {metric.label}
                  </tspan>
                  <tspan x={p.x} dy="14" style={{ fill: 'var(--text)' }}>
                    {metric.value} / {SCALE_MAX}
                  </tspan>
                </text>
              )
            })}
          </svg>

          <div className="w-full overflow-x-auto lg:max-w-sm">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr>
                  <th className="border-b px-3 py-2 text-left" style={{ borderColor: 'var(--border)', color: 'var(--text)' }}>
                    Metric
                  </th>
                  <th className="border-b px-3 py-2 text-right" style={{ borderColor: 'var(--border)', color: 'var(--text)' }}>
                    Score
                  </th>
                </tr>
              </thead>
              <tbody>
                {profile.metrics.map((metric) => (
                  <tr
                    key={metric.key}
                    onMouseEnter={() => setHovered(metric.key)}
                    onMouseLeave={() => setHovered(null)}
                    style={{ background: hovered === metric.key ? 'var(--accent-bg)' : undefined }}
                  >
                    <td className="border-b px-3 py-2" style={{ borderColor: 'var(--border)', color: 'var(--text-h)' }}>
                      {metric.label}
                    </td>
                    <td
                      className="border-b px-3 py-2 text-right font-mono"
                      style={{ borderColor: 'var(--border)', color: 'var(--text-h)' }}
                    >
                      {metric.value} / {SCALE_MAX}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  )
}

export default Profile
