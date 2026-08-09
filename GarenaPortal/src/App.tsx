import { Route, Routes } from 'react-router-dom'
import Layout from './Layout'
import Home from './pages/Home'
import About from './pages/About'
import Colors from './pages/Colors'
import Login from './pages/Login'
import MatchDetail from './pages/MatchDetail'
import Profile from './pages/Profile'
import NotFound from './pages/NotFound'
import ProtectedRoute from './ProtectedRoute'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route
          index
          element={
            <ProtectedRoute>
              <Home />
            </ProtectedRoute>
          }
        />
        <Route path="about" element={<About />} />
        <Route path="colors" element={<Colors />} />
        <Route path="login" element={<Login />} />
        <Route
          path="matches/:id"
          element={
            <ProtectedRoute>
              <MatchDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="profile"
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default App
