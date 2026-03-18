const fs = require('fs');

const modalPath = 'frontend/src/components/modals/LLMConfigModal.tsx';
let modalCode = fs.readFileSync(modalPath, 'utf8');

// There is a small mistake in the regex I wrote, it might duplicate the border-t line.
// Let's verify it was correctly injected before the delete button
console.log(modalCode.includes('已拉取到的模型列表'));
