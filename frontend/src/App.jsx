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
import Profile from './pages/Profile'
import Layout from './components/Layout'
import AdminArea from './pages/admin/AdminArea'
import StudentLayout from './pages/student/StudentLayout'
import StudentHome from './pages/student/StudentHome'
import StudentProfile from './pages/student/StudentProfile'
import Jobs from './pages/student/Jobs'
import JobDetails from './pages/student/JobDetails'
import MyApplications from './pages/student/MyApplications'
import Quizzes from './pages/student/Quizzes'
import Interview from './pages/student/Interview'
import RecruiterLayout from './pages/recruiter/RecruiterLayout'
import RecruiterHome from './pages/recruiter/RecruiterHome'
import JobsManage from './pages/recruiter/JobsManage'
import RecruiterApplications from './pages/recruiter/RecruiterApplications'
import './styles/app.css'

const roleHome = (user) => {
  if (user.is_admin_role) return '/admin'
  if (user.role === 'recruiter') return '/recruiter'
  return '/student'
}

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
  const allowed =
    roles.includes(user.role) || (roles.includes('admin') && user.is_admin_role)
  if (!allowed) return <Navigate to={roleHome(user)} replace />
  return children
}

function HomeRedirect() {
  const { user } = useAuth()
  return <Navigate to={roleHome(user)} replace />
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
              <HomeRedirect />
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
        <Route
          path="/admin"
          element={
            <RequireRole roles={['admin']}>
              <AdminArea />
            </RequireRole>
          }
        />
        <Route
          path="/student"
          element={
            <RequireRole roles={['student']}>
              <StudentLayout />
            </RequireRole>
          }
        >
          <Route index element={<StudentHome />} />
          <Route path="profile" element={<StudentProfile />} />
          <Route path="jobs" element={<Jobs />} />
          <Route path="jobs/:id" element={<JobDetails />} />
          <Route path="applications" element={<MyApplications />} />
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
          <Route index element={<RecruiterHome />} />
          <Route path="jobs" element={<JobsManage />} />
          <Route path="applications" element={<RecruiterApplications />} />
        </Route>
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