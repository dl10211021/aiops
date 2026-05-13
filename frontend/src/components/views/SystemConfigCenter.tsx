import PageHeader from '@/components/layout/PageHeader'
import { useStore } from '@/store'

const CONFIG_CARDS = [
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
  {
    id: 'retention',
    eyebrow: '数据生命周期',
    title: '会话保留策略',
    description: '管理聊天历史、工具结果、执行链路和审计元数据的保留周期。命令和 SQL 会独立保留。',
    action: '打开保留策略',
    modal: 'session-retention',
    stats: ['结果摘要化', '压缩历史清理', '审计元数据'],
  },
]

const BOUNDARY_CARDS = [
  {
    title: '系统配置',
    description: '安全、通知、数据保留等平台级开关。',
  },
  {
    title: '资产中心',
    description: '资产接入、协议、凭据和分组管理。',
  },
  {
    title: '会话 / 知识库',
    description: '工具执行、会话追踪和资料检索。',
  },
]

export default function SystemConfigCenter() {
  const openModal = useStore((state) => state.openModal)

  return (
    <div className="flex-1 overflow-y-auto p-4 lg:p-5">
      <PageHeader
        eyebrow="系统中枢"
        title="系统配置"
        description="把安全、通知和数据保留集中到一个入口。左侧只保留“配置”，这里负责进入具体配置项。"
      />

      <section className="grid gap-4 xl:grid-cols-4">
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
        <div className="text-sm font-bold text-ops-text">入口边界</div>
        <div className="mt-3 grid gap-2 text-xs text-ops-subtext lg:grid-cols-3">
          {BOUNDARY_CARDS.map((item) => (
            <div key={item.title} className="rounded-xl border border-ops-surface1/70 bg-ops-dark/28 px-3 py-2">
              <div className="font-bold text-ops-text">{item.title}</div>
              <div className="mt-1 leading-5">{item.description}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
