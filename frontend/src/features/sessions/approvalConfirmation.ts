export const AUTO_APPROVE_CONFIRMATION_TEXT = '全部批准'

export function isAutoApproveConfirmationValid(value: string) {
  return value.trim() === AUTO_APPROVE_CONFIRMATION_TEXT
}
