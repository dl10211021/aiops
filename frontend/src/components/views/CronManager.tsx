import { useState, useEffect, useCallback } from 'react'
import { useStore } from '@/store'
import { getCronJobs, addCronJob, deleteCronJob } from '@/api/client'
import type { CronJob } from '@/types'

export default function CronManager() {
  const addToast = useStore((s) => s.addToast)
  const [jobs, setJobs] = useState<CronJob[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({
    cron_expr: '0 9 * * *',
    message: '',
    host: '',
    username: 'root',
    agent_profile: 'default',
    password: '',
  })

  const loadJobs = useCallback(async () => {
    try {
      const res = await getCronJobs()
      setJobs(res.data.jobs || [])
    } catch {
      addToast('加载巡检计划失败', 'error')
    }
  }, [addToast])

  useEffect(() => { loadJobs() }, [loadJobs])

  const handleAdd = async () => {
    if (!form.cron_expr || !form.message || !form.host) {
      addToast('请填写完整信息', 'error')
      return
    }
    try {
      await addCronJob(form)
      setShowAdd(false)
      setForm({ cron_expr: '0 9 * * *', message: '', host: '', username: 'root', agent_profile: 'default', password: '' })
      await loadJobs()
      addToast('巡检计划已添加', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '添加失败', 'error')
    }
  }

  const handleDelete = async (jobId: string) => {
    if (!confirm('确定要删除此巡检计划？')) return
    try {
      await deleteCronJob(jobId)
      setJobs(jobs.filter((j) => j.id !== jobId))
      addToast('巡检计划已删除', 'success')
    } catch {
      addToast('删除失败', 'error')
    }
  }

  const cronPresets = [
    { label: '每天 09:00', expr: '0 9 * * *' },
    { label: '每小时', expr: '0 * * * *' },
    { label: '每30分钟', expr: '*/30 * * * *' },
    { label: '每周一 09:00', expr: '0 9 * * 1' },
  ]

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-ops-text">⏰ 定时巡检</h1>
            <p className="text-sm text-ops-subtext mt-1">配置 AI 自动定时执行巡检任务</p>
          </div>
          <button
            onClick={() => setShowAdd(true)}
            className="bg-ops-accent text-ops-dark text-sm px-3 py-1.5 rounded-lg font-medium hover:bg-ops-accent/80 transition-colors"
          >
            + 新建计划
          </button>
        </div>

        {/* Job list */}
        {jobs.length > 0 ? (
          <div className="space-y-3">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="bg-ops-panel border border-ops-surface0 rounded-xl p-4 hover:border-ops-accent/40 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs bg-ops-dark text-ops-accent px-2 py-0.5 rounded">
                        {job.cron_expr}
                      </span>
                      <span className="text-xs text-ops-overlay">{job.host}</span>
                    </div>
                    <p className="text-sm text-ops-text">{job.message}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-ops-overlay">
                      <span>👤 {job.username}</span>
                      <span>🎭 {job.agent_profile}</span>
                      {job.next_run && <span>⏭️ 下次: {job.next_run}</span>}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(job.id)}
                    className="text-ops-overlay hover:text-ops-alert text-sm ml-3 transition-colors"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center text-ops-subtext py-20">
            <div className="text-4xl mb-3">⏰</div>
            <p>暂无巡检计划</p>
            <p className="text-xs mt-1">创建定时任务，AI 将按计划自动执行运维巡检</p>
          </div>
        )}

        {/* Add Modal */}
        {showAdd && (
          <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={() => setShowAdd(false)}>
            <div className="bg-ops-panel rounded-xl p-6 w-[480px]" onClick={(e) => e.stopPropagation()}>
              <h2 className="text-lg font-bold text-ops-text mb-4">新建巡检计划</h2>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-ops-subtext">Cron 表达式</label>
                  <div className="flex gap-2 mt-1">
                    <input
                      value={form.cron_expr}
                      onChange={(e) => setForm({ ...form, cron_expr: e.target.value })}
                      className="flex-1 bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text font-mono outline-none focus:border-ops-accent"
                    />
                  </div>
                  <div className="flex gap-1 mt-1.5">
                    {cronPresets.map((p) => (
                      <button
                        key={p.expr}
                        onClick={() => setForm({ ...form, cron_expr: p.expr })}
                        className="text-[10px] bg-ops-surface0 text-ops-subtext px-2 py-0.5 rounded hover:text-ops-text"
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-ops-subtext">巡检指令</label>
                  <textarea
                    value={form.message}
                    onChange={(e) => setForm({ ...form, message: e.target.value })}
                    rows={3}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent resize-none"
                    placeholder="执行每日系统深度体检，生成资源使用率报告..."
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-ops-subtext">目标主机</label>
                    <input
                      value={form.host}
                      onChange={(e) => setForm({ ...form, host: e.target.value })}
                      className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                      placeholder="192.168.1.1"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-ops-subtext">用户名</label>
                    <input
                      value={form.username}
                      onChange={(e) => setForm({ ...form, username: e.target.value })}
                      className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-ops-subtext">密码</label>
                  <input
                    type="password"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-4">
                <button onClick={() => setShowAdd(false)} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text">取消</button>
                <button onClick={handleAdd} className="bg-ops-accent text-ops-dark px-4 py-2 rounded-lg text-sm font-medium hover:bg-ops-accent/80">创建</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
