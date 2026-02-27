import { useCallback, useState } from 'react'
import { motion } from 'framer-motion'
import { useAppStore } from '../stores/useAppStore'

export function UploadScreen() {
  const uploadFile = useAppStore((s) => s.uploadFile)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFile = useCallback(
    async (file: File) => {
      const ext = file.name.toLowerCase()
      if (!ext.endsWith('.pdf') && !ext.endsWith('.docx')) {
        setError('Only PDF and DOCX files are supported.')
        return
      }
      setError(null)
      setUploading(true)
      try {
        await uploadFile(file)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Upload failed')
        setUploading(false)
      }
    },
    [uploadFile],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(true)
  }, [])

  const onDragLeave = useCallback(() => setDragging(false), [])

  const onBrowse = useCallback(() => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.pdf,.docx'
    input.onchange = () => {
      const file = input.files?.[0]
      if (file) handleFile(file)
    }
    input.click()
  }, [handleFile])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen flex flex-col items-center justify-center p-8"
    >
      {/* Title */}
      <motion.div
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1, duration: 0.5 }}
        className="text-center mb-10"
      >
        <h1 className="text-4xl font-bold text-white mb-2">Citation Verifier</h1>
        <p className="text-gray-400 text-lg">
          Upload an academic document to verify its citations
        </p>
      </motion.div>

      {/* Drop zone */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.5 }}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={onBrowse}
        className={`
          glass-card w-full max-w-xl p-16 flex flex-col items-center justify-center
          cursor-pointer transition-all duration-300
          ${dragging
            ? 'border-amber-400/60 shadow-[0_0_40px_rgba(245,158,11,0.3)]'
            : 'hover:border-white/20 hover:shadow-[0_0_30px_rgba(255,255,255,0.05)]'
          }
          ${uploading ? 'pointer-events-none opacity-60' : ''}
        `}
      >
        {uploading ? (
          <>
            <div className="w-10 h-10 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mb-4" />
            <p className="text-gray-300 text-lg">Analyzing document...</p>
          </>
        ) : (
          <>
            {/* Upload icon */}
            <div className="mb-6">
              <svg
                className={`w-16 h-16 transition-colors duration-300 ${
                  dragging ? 'text-amber-400' : 'text-gray-500'
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
            </div>
            <p className="text-gray-300 text-lg mb-2">
              {dragging ? 'Drop your file here' : 'Drag & drop your PDF or DOCX'}
            </p>
            <p className="text-gray-500 text-sm">or click to browse</p>
          </>
        )}
      </motion.div>

      {/* Error message */}
      {error && (
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-red-400 mt-4 text-sm"
        >
          {error}
        </motion.p>
      )}
    </motion.div>
  )
}
