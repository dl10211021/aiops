# OpsCore runtime artifact policy

## 目标

避免调试截图、实时画板运行态、临时脚本和本地缓存混入产品提交，同时不误删用户上传文档、知识库资料或审计证据。

## 保留原则

- `knowledge_base/` 下的业务资料默认视为用户数据，不自动删除，也不批量忽略。
- 根目录 `tmp_knowledge_*.png` 只作为前端调试截图，默认忽略，不进入提交。
- 根目录 `realtime_canvases.json` 是本地实时画板运行态，默认忽略，不进入提交。
- `.research/hermes-agent/` 是外部研究源码，除非明确做 Hermes 工作，否则不纳入 OpsCore 提交。

## 清理原则

- 提交前先运行 `python scripts/worktree_audit.py --check-staged`，确认暂存区没有运行态、敏感文件或外部源码。
- 临时文件先忽略或归档，不能直接递归删除不确定文件。
- 如果文件可能是用户上传资料、巡检证据、知识库原文或审计记录，必须人工确认后再处理。
