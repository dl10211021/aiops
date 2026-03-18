const fs = require('fs');

const chatPath = 'frontend/src/components/chat/ChatWindow.tsx';
let chatCode = fs.readFileSync(chatPath, 'utf8');

// The user is asking "我模型思考不应该有关闭选项吗？？？怎么低中高了"
// It seems they want explicitly "关闭思考" and "开启思考" instead of "默认思维" or just to have "关闭" clear.

chatCode = chatCode.replace(
  /<option value="off">默认思维<\/option>/g,
  '<option value="off">关闭思考 (默认)</option>'
);

if (!chatCode.includes('<option value="enabled">开启思考</option>')) {
  // Let's add an explicit "enabled" if they want it. But Anthropic budget expects tokens, OpenAI expects reasoning_effort.
  // Actually, Anthropic can just have budget=enabled but what's the budget? We mapped "low", "medium", "high".
  // Let's just rename the labels to be clearer.
}

fs.writeFileSync(chatPath, chatCode);
console.log("Updated thinking mode labels.");
