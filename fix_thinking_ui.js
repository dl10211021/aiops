const fs = require('fs');

const chatPath = 'frontend/src/components/chat/ChatWindow.tsx';
let chatCode = fs.readFileSync(chatPath, 'utf8');

// Update the options to be: 默认/关闭, 开启, 低度思考, 中度思考, 高度思考
chatCode = chatCode.replace(
  /<select\s+value=\{thinkingMode\}\s+onChange=\{\(e\) => setThinkingMode\(e\.target\.value\)\}\s+className="bg-ops-surface0 text-ops-text text-\[11px\] rounded px-2 py-1 outline-none ml-2 border border-transparent hover:border-ops-surface1 cursor-pointer transition-colors"\s+disabled=\{isStreaming\}\s+title="思考模式 \(推理模型生效\)"\s+>\s+<option value="off">关闭思考 \(默认\)<\/option>\s+<option value="low">低度思考<\/option>\s+<option value="medium">中度思考<\/option>\s+<option value="high">高度思考<\/option>\s+<\/select>/,
  `<select
                  value={thinkingMode}
                  onChange={(e) => setThinkingMode(e.target.value)}
                  className="bg-ops-surface0 text-ops-text text-[11px] rounded px-2 py-1 outline-none ml-2 border border-transparent hover:border-ops-surface1 cursor-pointer transition-colors"
                  disabled={isStreaming}
                  title="思考模式 (推理模型生效)"
                >
                  <option value="off">关闭思考</option>
                  <option value="enabled">开启思考 (默认深度)</option>
                  <option value="low">低度思考</option>
                  <option value="medium">中度思考</option>
                  <option value="high">高度思考</option>
                </select>`
);

fs.writeFileSync(chatPath, chatCode);
console.log("Updated UI for thinking mode");
