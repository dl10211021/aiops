import { previewChatAttachment } from '@/api/client'
import type { ChatAttachmentPreview } from './chatTypes'

export interface ParsedAttachmentBatch {
  failed: string[]
  limitTip: string
  parsed: ChatAttachmentPreview[]
}

export function selectPreviewFiles(files: FileList | File[] | null, limit = 5) {
  const incoming = files ? Array.from(files) : []
  return {
    incoming,
    selected: incoming.slice(0, limit),
  }
}

export async function parseChatAttachmentFiles(
  files: File[],
  registerPreviewUrl: (url: string) => void,
): Promise<Pick<ParsedAttachmentBatch, 'failed' | 'parsed'>> {
  const results = await Promise.allSettled(files.map(async (file) => {
    try {
      const res = await previewChatAttachment(file)
      const previewUrl = file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
      if (previewUrl) registerPreviewUrl(previewUrl)
      return {
        id: `${Date.now()}-${file.name}-${Math.random().toString(36).slice(2)}`,
        previewUrl,
        ...res.data.attachment,
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '解析失败'
      throw new Error(`${file.name}: ${message}`)
    }
  }))

  const parsed: ChatAttachmentPreview[] = []
  const failed: string[] = []
  for (const result of results) {
    if (result.status === 'fulfilled') {
      parsed.push(result.value)
    } else {
      failed.push(result.reason instanceof Error ? result.reason.message : String(result.reason))
    }
  }
  return { failed, parsed }
}

export function appendSessionAttachments(
  current: ChatAttachmentPreview[],
  parsed: ChatAttachmentPreview[],
  limit = 8,
) {
  return [...current, ...parsed].slice(0, limit)
}

export function attachmentUploadToastMessage(batch: ParsedAttachmentBatch) {
  if (batch.failed.length > 0) {
    return {
      message: `已解析 ${batch.parsed.length} 个附件，${batch.failed.length} 个失败${batch.limitTip}。${batch.failed[0]}`,
      type: 'info' as const,
    }
  }
  return {
    message: `已解析 ${batch.parsed.length} 个附件，可随消息一起发送${batch.limitTip}`,
    type: 'success' as const,
  }
}
