const fs = require('fs');
let clientPath = 'frontend/src/api/client.ts';
let code = fs.readFileSync(clientPath, 'utf8');

const newTypes = `

export interface ProviderConfig {
  id: string;
  name: string;
  protocol: string;
  base_url: string;
  api_key: string;
  models: string;
}

export interface ModelGroup {
  provider_id: string;
  provider_name: string;
  models: { id: string; name: string }[];
}

export async function getProviders() {
  return request<{ providers: ProviderConfig[] }>('/config/providers')
}

export async function updateProviders(providers: ProviderConfig[]) {
  return request('/config/providers', {
    method: 'POST', body: JSON.stringify(providers),
  })
}

export async function getAvailableModels() {
  return request<{ models: ModelGroup[] }>('/models')
}
`;

// Just replace everything under config
const configSplit = code.indexOf('// ---- Config ----');
if (configSplit > -1) {
    const afterConfig = code.indexOf('// ---- Hydrate ----', configSplit);
    code = code.substring(0, configSplit + 19) + newTypes + '\n' + code.substring(afterConfig);
    fs.writeFileSync(clientPath, code);
}
