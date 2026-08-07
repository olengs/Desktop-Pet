import { Link } from 'react-router-dom'

function NotFound() {
  return (
    <section id="spacer">
      <h1>404</h1>
      <p>Page not found.</p>
      <Link to="/">Go home</Link>
    </section>
  )
}

export default NotFound
