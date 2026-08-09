import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from './auth'

function Layout() {
  const { username, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <>
      <nav className="site-nav">
        {username && (
          <NavLink to="/" end>
            Home
          </NavLink>
        )}
        {username && <NavLink to="/profile">Profile</NavLink>}
        {!username && <NavLink to="/login">Login</NavLink>}
        <NavLink to="/about">About</NavLink>
        {username && (
          <button
            type="button"
            onClick={handleLogout}
            className="cursor-pointer border-0 bg-transparent p-0 font-medium hover:text-(--accent)"
            style={{ color: 'var(--text)' }}
          >
            Logout
          </button>
        )}
      </nav>
      <Outlet />
    </>
  )
}

export default Layout
