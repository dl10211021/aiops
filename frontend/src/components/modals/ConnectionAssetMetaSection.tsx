interface ConnectionAssetMetaSectionProps {
  groupName: string
  remark: string
  onGroupNameChange: (value: string) => void
  onRemarkChange: (value: string) => void
}

export default function ConnectionAssetMetaSection({
  groupName,
  remark,
  onGroupNameChange,
  onRemarkChange,
}: ConnectionAssetMetaSectionProps) {
  return (
    <section className="ops-data-panel p-3">
      <div className="mb-3 text-xs font-semibold text-ops-text">资产备注</div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-ops-subtext">备注/别名</label>
          <input
            value={remark}
            onChange={(event) => onRemarkChange(event.target.value)}
            className="ops-control mt-1 w-full px-3 py-2 text-sm"
            placeholder="生产-WebServer-01"
          />
        </div>
        <div>
          <label className="text-xs text-ops-subtext">分组</label>
          <input
            value={groupName}
            onChange={(event) => onGroupNameChange(event.target.value)}
            className="ops-control mt-1 w-full px-3 py-2 text-sm"
            placeholder="未分组"
          />
        </div>
      </div>
    </section>
  )
}
