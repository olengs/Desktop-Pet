import { NavLink, Outlet } from 'react-router-dom'

function Layout() {
  return (
    <>
      <nav className="site-nav">
        <NavLink to="/" end>
          Home
        </NavLink>
        <NavLink to="/about">About</NavLink>
        <NavLink to="/colors">Colors</NavLink>
      </nav>
      <Outlet />
    </>
  )
}

export default Layout
