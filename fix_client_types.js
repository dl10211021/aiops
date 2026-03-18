const fs = require('fs');
let clientPath = 'frontend/src/api/client.ts';
let code = fs.readFileSync(clientPath, 'utf8');

if (!code.includes('export interface ProviderConfig')) {
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
`;
  
  // Replace getLLMConfig with new Types
  code = code.replace(/export async function getLLMConfig\(\) \{[\s\S]*?export async function updateLLMConfig[\s\S]*?\}\n\n/, newTypes);
  
  // Update getAvailableModels to return groups
  code = code.replace(/export async function getAvailableModels\(\) \{\n  return request<\{ models: string\[\] \}>\('\/models'\)\n\}/, 
  `export async function getAvailableModels() {
  return request<{ models: ModelGroup[] }>('/models')
}`);

  fs.writeFileSync(clientPath, code);
}
