import { useState, type SubmitEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

function Login() {
  const [username, setUsername] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = username.trim()
    if (!trimmed) return
    login(trimmed)
    const redirectTo = (location.state as { from?: Location })?.from?.pathname ?? '/'
    navigate(redirectTo, { replace: true })
  }

  return (
    <section className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center px-6 py-12">
      <h1 className="text-center">Log in</h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5 text-left">
          <span className="text-sm font-medium" style={{ color: 'var(--text-h)' }}>
            Username
          </span>
          <input
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoFocus
            autoComplete="username"
            placeholder="Enter your username"
            className="rounded-lg border px-3 py-2 text-base outline-none focus:border-[var(--accent)]"
            style={{ borderColor: 'var(--border)', background: 'var(--bg)', color: 'var(--text-h)' }}
          />
        </label>
        <button
          type="submit"
          disabled={!username.trim()}
          className="rounded-lg px-4 py-2 font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          style={{ background: 'var(--accent)' }}
        >
          Continue
        </button>
      </form>
    </section>
  )
}

export default Login
