export interface ChatAttachmentPreview {
  id: string
  filename: string
  ext: string
  size: number
  text: string
  truncated: boolean
  rows?: number
  sheets?: string[]
  pages?: number
  kind?: string
  content_type?: string
  previewUrl?: string
  data_url?: string | null
}
