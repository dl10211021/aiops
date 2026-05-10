import { useState } from 'react'
import type { ModelGroup } from '@/api/client'
import type { Session, SessionToolCatalog } from '@/types'
import {
  SessionIdentityStrip,
  SessionRuntimeControls,
  SessionToolsetDetails,
} from './SessionToolsetBarParts'
import { buildSessionToolsetModel } from './sessionToolsetModel'

interface SessionToolsetBarProps {
  catalog: SessionToolCatalog | null
  session: Session
  availableModels: ModelGroup[]
  modelName: string
  orchestrationMode: 'single' | 'split' | 'fast'
  thinkingMode: string
  onModelChange: (value: string) => void
  onOrchestrationModeChange: (mode: 'single' | 'split' | 'fast') => void
  onThinkingModeChange: (value: string) => void
}

export default function SessionToolsetBar({
  catalog,
  session,
  availableModels,
  modelName,
  orchestrationMode,
  thinkingMode,
  onModelChange,
  onOrchestrationModeChange,
  onThinkingModeChange,
}: SessionToolsetBarProps) {
  const [detailsOpen, setDetailsOpen] = useState(false)
  const toolsetModel = buildSessionToolsetModel(session, catalog)

  return (
    <div className="border-b border-ops-surface0/75 bg-[linear-gradient(90deg,rgba(40,208,168,0.07),rgba(15,31,50,0.76),rgba(10,20,35,0.88))] px-3 py-1.5">
      <div className="grid gap-1.5 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-center">
        <SessionIdentityStrip
          session={session}
          assetText={toolsetModel.assetText}
          protocolText={toolsetModel.protocolText}
          capabilityItems={toolsetModel.capabilityItems}
        />
        <SessionRuntimeControls
          availableModels={availableModels}
          modelName={modelName}
          orchestrationMode={orchestrationMode}
          thinkingMode={thinkingMode}
          capabilityItems={toolsetModel.capabilityItems}
          detailsOpen={detailsOpen}
          onModelChange={onModelChange}
          onOrchestrationModeChange={onOrchestrationModeChange}
          onThinkingModeChange={onThinkingModeChange}
          onToggleDetails={() => setDetailsOpen((open) => !open)}
        />
      </div>

      {detailsOpen && (
        <SessionToolsetDetails
          enabledToolsets={toolsetModel.enabledToolsets}
          primaryToolsets={toolsetModel.primaryToolsets}
          scope={toolsetModel.scope}
          scopeValue={toolsetModel.scopeValue}
          session={session}
          targetLabel={toolsetModel.targetLabel}
        />
      )}
    </div>
  )
}
