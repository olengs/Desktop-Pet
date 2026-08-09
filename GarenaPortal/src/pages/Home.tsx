import { Link } from 'react-router-dom'
import { recentMatches } from '../data/matches'
import { useAuth } from '../auth'
import '../App.css'

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

function Home() {
  const { username } = useAuth()

  return (
    <>
      <div className="ticks"></div>

      <section id="matches" className="px-8 py-8 text-left md:px-8">
        <h2>Recent matches{username ? ` · ${username}` : ''}</h2>
        <ul className="mt-4 flex flex-col gap-2">
          {recentMatches.map((match) => (
            <li key={match.id}>
              <Link
                to={`/matches/${match.id}`}
                className="flex items-center justify-between gap-4 rounded-lg border px-4 py-3 no-underline transition-colors hover:border-(--accent-border)"
                style={{ borderColor: 'var(--border)', color: 'inherit' }}
              >
                <div className="flex items-center gap-3">
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
                  <div>
                    <div className="font-medium" style={{ color: 'var(--text-h)' }}>
                      {match.game} · {match.mode}
                    </div>
                    <div className="text-sm" style={{ color: 'var(--text)' }}>
                      {match.map}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-sm" style={{ color: 'var(--text-h)' }}>
                    {match.score}
                  </div>
                  <div className="text-xs" style={{ color: 'var(--text)' }}>
                    {dateFormatter.format(new Date(match.playedAt))}
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}

export default Home
