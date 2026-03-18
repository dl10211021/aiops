const fs = require('fs');
const path = 'frontend/src/components/modals/LLMConfigModal.tsx';
let content = fs.readFileSync(path, 'utf8');

// Remove getEmbeddingConfig, updateEmbeddingConfig from import
content = content.replace(/, getEmbeddingConfig, updateEmbeddingConfig/g, '');

// Remove embedding states
content = content.replace(/const \[embModel, setEmbModel\] = useState\(''\)\s*const \[embDim, setEmbDim\] = useState\(768\)/, '');

// Remove embedding fetch
content = content.replace(/getEmbeddingConfig\(\)\.then\(\(r\) => \{\s*setEmbModel\(r\.data\.model \|\| ''\)\s*setEmbDim\(r\.data\.dim \|\| 768\)\s*\}\)\.catch\(\(\) => \{\}\)/, '');

// Remove embedding save
content = content.replace(/if \(embModel\) await updateEmbeddingConfig\(embModel, embDim\)/, '');

// Remove embedding UI
content = content.replace(/<hr className="border-ops-surface0" \/>\s*\{\/\* Embedding config \*\/\}\s*<div>\s*<label className="text-xs text-ops-subtext">Embedding 模型<\/label>[\s\S]*?<\/div>\s*<div>\s*<label className="text-xs text-ops-subtext">Embedding 维度<\/label>[\s\S]*?<\/div>/, '');

fs.writeFileSync(path, content);
