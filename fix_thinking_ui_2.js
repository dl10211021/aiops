const fs = require('fs');

const chatPath = 'frontend/src/components/chat/ChatWindow.tsx';
let chatCode = fs.readFileSync(chatPath, 'utf8');

// I might have written the regex badly, let's just replace the whole select manually
chatCode = chatCode.replace(/<select[\s\S]*?value=\{thinkingMode\}[\s\S]*?onChange=\{\(e\) => setThinkingMode\(e\.target\.value\)\}[\s\S]*?title="思考模式 \(推理模型生效\)"\s*>[\s\S]*?<\/select>/,
`<select
                  value={thinkingMode}
                  onChange={(e) => setThinkingMode(e.target.value)}
                  className="bg-ops-surface0 text-ops-text text-[11px] rounded px-2 py-1 outline-none ml-2 border border-transparent hover:border-ops-surface1 cursor-pointer transition-colors"
                  disabled={isStreaming}
                  title="思考模式 (推理模型生效)"
                >
                  <option value="off">关闭思考 (默认)</option>
                  <option value="enabled">开启思考 (自动)</option>
                  <option value="low">低度思考</option>
                  <option value="medium">中度思考</option>
                  <option value="high">高度思考</option>
                </select>`);

fs.writeFileSync(chatPath, chatCode);
