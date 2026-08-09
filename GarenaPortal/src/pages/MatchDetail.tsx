import { Link, useParams } from 'react-router-dom'
import { getMatchById } from '../data/matches'

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

function MatchDetail() {
  const { id } = useParams<{ id: string }>()
  const match = id ? getMatchById(id) : undefined

  if (!match) {
    return (
      <section className="px-8 py-8 text-left">
        <h1>Match not found</h1>
        <p style={{ color: 'var(--text)' }}>This match doesn't exist or has expired.</p>
        <p className="mt-4">
          <Link to="/" style={{ color: 'var(--accent)' }}>
            ← Back to matches
          </Link>
        </p>
      </section>
    )
  }

  return (
    <section className="px-8 py-8 text-left">
      <p className="text-sm">
        <Link to="/" style={{ color: 'var(--accent)' }}>
          ← Back to matches
        </Link>
      </p>

      <h1>{match.game}</h1>

      <div className="flex flex-wrap items-center gap-3">
        <span
          className="rounded-md px-2 py-1 text-xs font-semibold uppercase"
          style={
            match.result === 'win'
              ? { color: '#15803d', background: 'rgba(21,128,61,0.12)' }
              : { color: 'var(--accent)', background: 'var(--accent-bg)' }
          }
        >
          {match.result}
        </span>
        <span style={{ color: 'var(--text)' }}>
          {match.mode} · {match.map}
        </span>
      </div>
      <p className="mt-1 text-sm" style={{ color: 'var(--text)' }}>
        {dateFormatter.format(new Date(match.playedAt))} · {match.duration}
      </p>

      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {match.stats.map((stat) => (
          <div key={stat.label} className="rounded-lg border p-3" style={{ borderColor: 'var(--border)' }}>
            <div className="text-xs" style={{ color: 'var(--text)' }}>
              {stat.label}
            </div>
            <div className="font-mono text-lg" style={{ color: 'var(--text-h)' }}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

export default MatchDetail
