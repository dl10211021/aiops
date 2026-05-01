import type { ChatAttachmentPreview } from './chatTypes'
import { formatBytes } from './format'

export function composeChatMessage(text: string, attachments: ChatAttachmentPreview[]) {
  if (attachments.length === 0) return text
  const attachmentText = attachments.map((file, index) => {
    const meta = [
      `文件名：${file.filename}`,
      `类型：${file.ext || 'unknown'}`,
      `大小：${formatBytes(file.size)}`,
      file.rows !== undefined ? `行数：${file.rows}` : '',
      file.pages !== undefined ? `页数：${file.pages}` : '',
      file.sheets?.length ? `工作表：${file.sheets.join(', ')}` : '',
      file.truncated ? '内容已截断：是' : '',
    ].filter(Boolean).join('；')
    return [
      `## 附件 ${index + 1}`,
      meta,
      '```text',
      file.text || '[附件没有解析出可读文本]',
      '```',
    ].join('\n')
  }).join('\n\n')
  return [
    text || '请先阅读下面附件内容，并基于附件继续分析。',
    '',
    '以下是本次消息随附的一次性文件内容，仅用于当前会话上下文：',
    attachmentText,
  ].join('\n')
}

export function chatAttachmentPayload(attachments: ChatAttachmentPreview[]) {
  return attachments.map((file) => ({
    filename: file.filename,
    ext: file.ext,
    size: file.size,
    content_type: file.content_type,
    kind: file.kind,
    rows: file.rows,
    pages: file.pages,
    sheets: file.sheets,
    truncated: file.truncated,
    data_url: file.data_url || null,
  }))
}

export function chatMessageAttachments(attachments: ChatAttachmentPreview[]) {
  return attachments.map((file) => ({
    filename: file.filename,
    ext: file.ext,
    size: file.size,
    kind: file.kind,
    rows: file.rows,
    pages: file.pages,
    sheets: file.sheets,
    truncated: file.truncated,
  }))
}
