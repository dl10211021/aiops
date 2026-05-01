export default function ChatEmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center text-ops-subtext">
      <div className="text-center">
        <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-lg border border-ops-accent/35 bg-ops-accent/10 text-xs font-black text-ops-accent">OPS</div>
        <h2 className="text-xl font-semibold text-ops-text mb-2">SkillOps AIOps 平台</h2>
        <p className="text-sm">选择一个已有会话或新建连接开始工作</p>
      </div>
    </div>
  )
}
