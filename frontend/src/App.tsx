import { AnimatePresence } from 'framer-motion'
import { useAppStore } from './stores/useAppStore'
import { UploadScreen } from './components/UploadScreen'
import { AnalysisView } from './components/AnalysisView'

export default function App() {
  const screen = useAppStore((s) => s.screen)

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <AnimatePresence mode="wait">
        {screen === 'upload' ? (
          <UploadScreen key="upload" />
        ) : (
          <AnalysisView key="analysis" />
        )}
      </AnimatePresence>
    </div>
  )
}
