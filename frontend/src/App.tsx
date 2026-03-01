import { useEffect } from 'react'
import { AnimatePresence } from 'framer-motion'
import { useAppStore } from './stores/useAppStore'
import { AuthScreen } from './components/AuthScreen'
import { ProjectListScreen } from './components/ProjectListScreen'
import { ProjectDetailScreen } from './components/ProjectDetailScreen'
import { AnalysisView } from './components/AnalysisView'

export default function App() {
  const screen = useAppStore((s) => s.screen)
  const authUser = useAppStore((s) => s.authUser)
  const authLoading = useAppStore((s) => s.authLoading)
  const initializeAuth = useAppStore((s) => s.initializeAuth)
  const logout = useAppStore((s) => s.logout)

  useEffect(() => {
    initializeAuth()
  }, [initializeAuth])

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-300">
        Authenticating...
      </div>
    )
  }

  if (!authUser) {
    return <AuthScreen />
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <div className="fixed top-3 right-3 z-50 flex items-center gap-2 text-xs">
        <span className="text-gray-400">{authUser.email}</span>
        <button
          onClick={logout}
          className="px-2 py-1 rounded bg-white/10 text-gray-200 hover:bg-white/20"
        >
          Logout
        </button>
      </div>
      <AnimatePresence mode="wait">
        {screen === 'projects' && <ProjectListScreen key="projects" />}
        {screen === 'project-detail' && <ProjectDetailScreen key="detail" />}
        {screen === 'analysis' && <AnalysisView key="analysis" />}
      </AnimatePresence>
    </div>
  )
}
