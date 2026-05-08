import PageHeader from '@/components/layout/PageHeader'
import { useStore } from '@/store'

const CONFIG_CARDS = [
  {
    id: 'model',
    eyebrow: '模型中心',
    title: '模型配置',
    description: '统一维护模型供应商、主模型、辅助模型、运行参数和模型拉取结果。',
    action: '打开模型配置',
    modal: 'llm-config',
    stats: ['主模型 / 辅助模型', '供应商连接', '自动获取模型'],
  },
  {
    id: 'safety',
    eyebrow: '安全边界',
    title: '安全策略',
    description: '集中管理只读边界、高危操作拦截、审批策略和工具执行规则。',
    action: '打开安全策略',
    modal: 'safety-policy',
    stats: ['工具审批', '硬拦截', '执行边界'],
  },
  {
    id: 'notify',
    eyebrow: '通知通道',
    title: '通知配置',
    description: '集中配置告警、巡检、审批和系统事件的消息通知通道。',
    action: '打开通知配置',
    modal: 'notifications',
    stats: ['告警通知', '巡检结果', '审批提醒'],
  },
]

export default function SystemConfigCenter() {
  const openModal = useStore((state) => state.openModal)

  return (
    <div className="flex-1 overflow-y-auto p-4 lg:p-5">
      <PageHeader
        eyebrow="系统中枢"
        title="系统配置"
        description="把模型、安全和通知集中到一个入口。左侧只保留“配置”，这里负责进入具体配置项。"
      />

      <section className="grid gap-4 xl:grid-cols-3">
        {CONFIG_CARDS.map((card) => (
          <button
            key={card.id}
            type="button"
            onClick={() => openModal(card.modal)}
            className="ops-card group overflow-hidden text-left transition-all hover:border-ops-accent/45 hover:shadow-[0_18px_50px_rgba(40,208,168,0.08)] focus:outline-none focus:ring-2 focus:ring-ops-accent/45"
            aria-label={card.action}
          >
            <div className="ops-card-header block">
              <div className="text-[11px] font-black uppercase tracking-[0.24em] text-ops-accent">{card.eyebrow}</div>
              <h2 className="mt-2 text-xl font-black text-ops-text">{card.title}</h2>
              <p className="mt-2 min-h-14 text-sm leading-6 text-ops-subtext">{card.description}</p>
            </div>
            <div className="space-y-2 p-4">
              {card.stats.map((item) => (
                <div key={item} className="ops-data-panel px-3 py-2 text-xs text-ops-subtext">
                  {item}
                </div>
              ))}
            </div>
            <div className="ops-card-footer">
              <span className="ops-primary-action block w-full px-4 py-2 text-center text-sm transition-transform group-hover:translate-x-0.5">
                {card.action}
              </span>
            </div>
          </button>
        ))}
      </section>

      <section className="ops-data-panel mt-4 p-4">
        <div className="text-sm font-bold text-ops-text">使用说明</div>
        <p className="mt-2 text-sm leading-6 text-ops-subtext">
          这里只承载系统级配置，不承载业务资产数据。资产接入去“资产中心”，会话与工具执行去“会话”，知识资料去“知识库”。
        </p>
      </section>
    </div>
  )
}
