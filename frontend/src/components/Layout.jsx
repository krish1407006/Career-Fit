import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navLink = ({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand">
          Career<span>AI</span>
        </Link>
        <nav className="topnav">
          <NavLink to="/" className={navLink} end>
            Dashboard
          </NavLink>
          <NavLink to="/profile" className={navLink}>
            Profile
          </NavLink>
          {user?.is_recruiter && (
            <NavLink to="/recruiter" className={navLink}>
              Recruiter
            </NavLink>
          )}
          {user?.role === 'student' && (
            <NavLink to="/student" className={navLink}>
              Student
            </NavLink>
          )}
        </nav>
        <div className="topbar-right">
          <span className="topbar-user">
            {user?.username} <em className="role-tag">{user?.role}</em>
          </span>
          <button className="btn btn-ghost" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>
      <main className="page">
        <Outlet />
      </main>
    </div>
  )
}