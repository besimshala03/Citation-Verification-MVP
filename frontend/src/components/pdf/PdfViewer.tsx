import { useEffect, useRef, useState } from 'react'
import { Document, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import { useAppStore } from '../../stores/useAppStore'
import { getFileUrl } from '../../api/client'
import { PdfPage } from './PdfPage'

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

export function PdfViewer() {
  const fileId = useAppStore((s) => s.fileId)
  const [numPages, setNumPages] = useState<number>(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const [pageWidth, setPageWidth] = useState<number>(500)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      const w = entries[0].contentRect.width
      setPageWidth(Math.max(300, w - 32)) // 32px for padding
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  if (!fileId) return null

  return (
    <div ref={containerRef} className="flex flex-col items-center py-6 px-4 gap-6">
      <Document
        file={getFileUrl(fileId)}
        onLoadSuccess={({ numPages }) => setNumPages(numPages)}
        loading={
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
          </div>
        }
        error={
          <div className="text-red-400 text-sm p-8">Failed to load PDF</div>
        }
      >
        {Array.from({ length: numPages }, (_, i) => (
          <PdfPage key={i} pageNumber={i + 1} width={pageWidth} />
        ))}
      </Document>
    </div>
  )
}
