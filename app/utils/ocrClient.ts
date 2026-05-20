import type { FileItem, OcrResult, OcrStatus, OcrWordLocation, PageOcrResult } from '../credentialForm/form/types/Types'

// ---------------------------------------------------------------------------
// Local Tesseract.js OCR client
// Runs entirely in the browser via WebAssembly — no server round-trips needed.
// ---------------------------------------------------------------------------

/** MIME / extension helpers ------------------------------------------------ */

const IMAGE_TYPES = new Set([
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/bmp',
  'image/tiff'
])

const IMAGE_EXTENSIONS = new Set([
  '.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif'
])

const isImage = (file: FileItem): boolean => {
  if (file.file && IMAGE_TYPES.has(file.file.type)) return true
  const ext = (file.fileExtension ?? file.name.split('.').pop() ?? '').toLowerCase()
  return IMAGE_EXTENSIONS.has('.' + ext)
}

const isPDF = (file: FileItem): boolean => {
  if (file.file && file.file.type === 'application/pdf') return true
  const ext = (file.fileExtension ?? file.name.split('.').pop() ?? '').toLowerCase()
  return ext === 'pdf'
}

const canOCR = (file: FileItem): boolean => isImage(file) || isPDF(file)

// ---------------------------------------------------------------------------
// Worker lazy-initialisation (singleton)
// ---------------------------------------------------------------------------

const { createWorker } = await import('tesseract.js')
let workerPromise: ReturnType<typeof createWorker> | null = null

async function getWorker() {
  if (!workerPromise) {
    workerPromise = createWorker('eng', 1, {
      logger: () => { /* progress logged per-recognize call below */ }
    })
  }
  return workerPromise
}


// ---------------------------------------------------------------------------
// OCR for a single image (PNG, JPEG, etc.)
// ---------------------------------------------------------------------------

async function extractFromImage(
  file: File,
  onProgress?: (p: number) => void
): Promise<{ text: string; words: OcrWordLocation[] }> {
  const worker = await getWorker()
  const imageUrl = URL.createObjectURL(file)

  try {
    const { data: { text, words: rawWords } } = await worker.recognize(imageUrl, undefined, {
      // logger: (m) => {
      //   if (m.status === 'recognizing text' && m.progress != null) {
      //     onProgress?.(m.progress)
      //   }
      // }
    })

    const words: OcrWordLocation[] = (rawWords ?? []).map((w: any) => ({
      text: w.text,
      bbox: { x0: w.bbox.x0, y0: w.bbox.y0, x1: w.bbox.x1, y1: w.bbox.y1 },
      confidence: w.confidence
    }))

    return { text: text.trim(), words }
  } finally {
    URL.revokeObjectURL(imageUrl)
  }
}

// ---------------------------------------------------------------------------
// OCR for PDFs (render pages via pdfjs-dist, then Tesseract each page)
// ---------------------------------------------------------------------------

async function extractFromPDF(
  file: File,
  onProgress?: (p: { current: number; total: number }) => void
): Promise<{ pages: PageOcrResult[] }> {
  const pdfjsLib = await import('pdfjs-dist')
  const arrayBuffer = await file.arrayBuffer()
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise

  const totalPages = pdf.numPages
  const MAX_PAGES = 20
  const pagesToProcess = Math.min(totalPages, MAX_PAGES)
  const pageResults: PageOcrResult[] = []

  for (let pageNum = 1; pageNum <= pagesToProcess; pageNum++) {
    const page = await pdf.getPage(pageNum)
    const viewport = page.getViewport({ scale: 2 })
    const canvas = document.createElement('canvas')
    canvas.width = viewport.width
    canvas.height = viewport.height
    const ctx = canvas.getContext('2d')!

    await page.render({ canvasContext: ctx, viewport }).promise

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/png')
    )
    if (!blob) continue

    const imageFile = new File([blob], `page-${pageNum}.png`, { type: 'image/png' })
    const { text, words } = await extractFromImage(imageFile)

    pageResults.push({ page: pageNum, text, words })
    onProgress?.({ current: pageNum, total: pagesToProcess })
  }

  return { pages: pageResults }
}

// ---------------------------------------------------------------------------
// Public API: ocrFileItem
// ---------------------------------------------------------------------------

export interface OcrProgress {
  status: OcrStatus
  /** 0–1 for images; {current, total} for PDFs */
  detail?: number | { current: number; total: number }
}

export async function ocrFileItem(
  item: FileItem,
  onProgress?: (p: OcrProgress) => void
): Promise<OcrResult> {
  if (!canOCR(item)) {
    return {
      status: 'failed',
      fullText: '',
      pages: [],
      error: `Unsupported file type: ${item.fileExtension ?? item.name}`
    }
  }

  if (!item.file) {
    return { status: 'failed', fullText: '', pages: [], error: 'Missing file data' }
  }

  try {
    onProgress?.({ status: 'processing' })

    if (isPDF(item)) {
      const { pages } = await extractFromPDF(item.file, (prog) => {
        onProgress?.({ status: 'processing', detail: prog })
      })
      const fullText = pages.map((p) => p.text).join('\n\n').trim()
      onProgress?.({ status: 'completed' })
      return { status: 'completed', fullText, pages }
    } else {
      const { text, words } = await extractFromImage(item.file, (prog) => {
        onProgress?.({ status: 'processing', detail: prog })
      })
      onProgress?.({ status: 'completed' })
      return {
        status: 'completed',
        fullText: text,
        pages: [{ page: 1, text, words }]
      }
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown OCR error'
    return { status: 'failed', fullText: '', pages: [], error: message }
  }
}

// ---------------------------------------------------------------------------
// Public helper: which files are eligible and still need OCR
// ---------------------------------------------------------------------------

export function filesNeedingOcr(files: FileItem[]): FileItem[] {
  return files.filter(
    (f) =>
      canOCR(f) &&
      f.file != null &&
      (!f.ocrResult || f.ocrResult.status === 'pending' || f.ocrResult.status === 'failed')
  )
}

export { canOCR }

