import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'
import { useAuth, AuthProvider } from './context/AuthContext'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Profile from './pages/Profile'
import Layout from './components/Layout'
import StudentLayout from './pages/student/StudentLayout'
import Resumes from './pages/student/Resumes'
import Jobs from './pages/student/Jobs'
import Quizzes from './pages/student/Quizzes'
import Interview from './pages/student/Interview'
import RecruiterLayout from './pages/recruiter/RecruiterLayout'
import JobsManage from './pages/recruiter/JobsManage'
import './styles/app.css'

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <div className="page-loading">Loading…</div>
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  return children
}

function RequireRole({ roles, children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="page-loading">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  if (!roles.includes(user.role)) return <Navigate to="/" replace />
  return children
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<Layout />}>
        <Route
          path="/"
          element={
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/profile"
          element={
            <RequireAuth>
              <Profile />
            </RequireAuth>
          }
        />
      </Route>
      <Route
        path="/student"
        element={
          <RequireRole roles={['student']}>
            <StudentLayout />
          </RequireRole>
        }
      >
        <Route index element={<Navigate to="resume" replace />} />
        <Route path="resume" element={<Resumes />} />
        <Route path="jobs" element={<Jobs />} />
        <Route path="quizzes" element={<Quizzes />} />
        <Route path="interview" element={<Interview />} />
      </Route>
      <Route
        path="/recruiter"
        element={
          <RequireRole roles={['recruiter']}>
            <RecruiterLayout />
          </RequireRole>
        }
      >
        <Route index element={<Navigate to="jobs" replace />} />
        <Route path="jobs" element={<JobsManage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}