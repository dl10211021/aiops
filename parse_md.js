const fs = require('fs');
const content = fs.readFileSync('frontend/src/components/modals/LLMConfigModal.tsx', 'utf8');

// Extract just the typescript part
const match = content.match(/```tsx\n([\s\S]*?)```/);
if (match) {
    fs.writeFileSync('frontend/src/components/modals/LLMConfigModal.tsx', match[1]);
    console.log('Successfully extracted TSX code');
} else {
    console.log('Failed to extract TSX');
}
