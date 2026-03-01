export const frontendConfig = {
  maxMainDocumentBytes: 20 * 1024 * 1024,
  maxReferencePdfBytes: 50 * 1024 * 1024,
  allowedMainExtensions: ['.pdf', '.docx'] as const,
  allowedMainMimeTypes: [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ] as const,
  allowedReferenceExtension: '.pdf' as const,
  allowedReferenceMimeType: 'application/pdf' as const,
}

