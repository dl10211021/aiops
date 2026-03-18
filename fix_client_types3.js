const fs = require('fs');
let clientPath = 'frontend/src/api/client.ts';
let code = fs.readFileSync(clientPath, 'utf8');

const missingApis = `

export async function getNotificationConfig() {
  return request<Record<string, unknown>>('/config/notifications')
}

export async function updateNotificationConfig(config: Record<string, unknown>) {
  return request('/config/notifications', {
    method: 'POST', body: JSON.stringify(config),
  })
}

export async function testNotificationChannel(channel: string) {
  return request('/config/notifications/test', {
    method: 'POST', body: JSON.stringify({ channel }),
  })
}
`;

code = code.replace('// ---- Hydrate ----', missingApis + '\n// ---- Hydrate ----');
fs.writeFileSync(clientPath, code);

let chatCode = fs.readFileSync('frontend/src/components/chat/ChatWindow.tsx', 'utf8');
chatCode = chatCode.replace('const [availableModels, setAvailableModels] = useState<string[]>([])', 'const [availableModels, setAvailableModels] = useState<import(\'@/api/client\').ModelGroup[]>([])');
chatCode = chatCode.replace('{availableModels.length > 0 ? (\n              availableModels.map((m) => <option key={m} value={m}>{m}</option>)\n            ) : (', '{availableModels.length > 0 ? (\n              availableModels.map(group => (\n                <optgroup key={group.provider_id} label={group.provider_name}>\n                  {group.models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}\n                </optgroup>\n              ))\n            ) : (');
fs.writeFileSync('frontend/src/components/chat/ChatWindow.tsx', chatCode);
