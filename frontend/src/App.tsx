import { AnimatePresence } from 'framer-motion'
import { useAppStore } from './stores/useAppStore'
import { ProjectListScreen } from './components/ProjectListScreen'
import { ProjectDetailScreen } from './components/ProjectDetailScreen'
import { AnalysisView } from './components/AnalysisView'

export default function App() {
  const screen = useAppStore((s) => s.screen)

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
