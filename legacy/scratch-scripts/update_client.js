const fs = require('fs');

const path = 'frontend/src/api/client.ts';
let file = fs.readFileSync(path, 'utf8');

// Update streamChat
file = file.replace(
  /export function streamChat\(\s*sessionId: string, message: string, modelName: string,\s*signal\?: AbortSignal\s*\) {/g,
  `export function streamChat(
  sessionId: string, message: string, modelName: string,
  thinkingMode: string = 'off',
  signal?: AbortSignal
) {`
);

file = file.replace(
  /body: JSON\.stringify\({ session_id: sessionId, message, model_name: modelName }\),/g,
  `body: JSON.stringify({ session_id: sessionId, message, model_name: modelName, thinking_mode: thinkingMode }),`
);

// Update getAvailableModels path
file = file.replace(
  /return request<\{ models: string\[\] \}>\('\/config\/models'\)/g,
  `return request<{ models: string[] }>('/models')`
);

fs.writeFileSync(path, file);
