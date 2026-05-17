from __future__ import annotations

# Compatibility barrel for existing imports. New schema implementations live in
# api.schema_models.

from api.schema_models.alerts import AlertEventUpdateRequest
from api.schema_models.approvals import (
    ApprovalDecisionRequest,
    ToolApprovalRequest,
    UserInteractionResponseRequest,
)
from api.schema_models.assets import (
    AssetPayload,
    BatchAssetDeletePayload,
    BatchAssetGroupDeletePayload,
    BatchAssetGroupPayload,
    BatchAssetGroupRenamePayload,
    BatchAssetImportItem,
)
from api.schema_models.chat import ChatRequest
from api.schema_models.common import ResponseModel
from api.schema_models.config import (
    AgentRuntimeConfigRequest,
    EmbeddingConfigRequest,
    NotificationConfigRequest,
    ProviderConfig,
    SafetyPolicyTestRequest,
    SafetyPolicyUpdateRequest,
    SessionRetentionConfigRequest,
    TestNotificationRequest,
)
from api.schema_models.connections import (
    CommandRequest,
    ConnectionInspectionRequest,
    ConnectionRequest,
)
from api.schema_models.inspection import (
    CronAddRequest,
    InspectionTemplatePayload,
    InspectionTemplateStepPayload,
)
from api.schema_models.sessions import (
    HeartbeatUpdateRequest,
    MultiAgentPermissionSyncRequest,
    PermissionUpdateRequest,
    SessionGroupUpdateRequest,
    SessionMetadataUpdateRequest,
    SessionMessageFeedbackRequest,
    SessionMessageUpdateRequest,
    SessionProfileGenerateRequest,
    SessionRunLearningCandidateRequest,
    SessionWebhookSendRequest,
    SkillsUpdateRequest,
    SlashCommandPayload,
)
from api.schema_models.skills import (
    CreateSkillRequest,
    MigrateRequest,
    SkillRollbackRequest,
    SkillValidationRequest,
)
