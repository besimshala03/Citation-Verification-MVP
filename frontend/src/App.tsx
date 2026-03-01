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
      <AnimatePresence mode="wait">
        {screen === 'projects' && <ProjectListScreen key="projects" />}
        {screen === 'project-detail' && <ProjectDetailScreen key="detail" />}
        {screen === 'analysis' && <AnalysisView key="analysis" />}
      </AnimatePresence>
    </div>
  )
}
