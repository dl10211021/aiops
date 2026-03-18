const fs = require('fs');

const chatPath = 'frontend/src/components/chat/ChatWindow.tsx';
let chatCode = fs.readFileSync(chatPath, 'utf8');

chatCode = chatCode.replace(/<select\s*value=\{thinkingMode\}\s*onChange=\{\(e\) => setThinkingMode\(e\.target\.value\)\}[\s\S]*?<\/select>/,
`<select
            value={thinkingMode}
            onChange={(e) => setThinkingMode(e.target.value)}
            className="bg-ops-surface0 text-ops-text text-xs rounded px-2 py-1.5 border border-ops-surface1 outline-none self-end"
            title="思维推理模式"
          >
            <option value="off">关闭思考 (默认)</option>
            <option value="enabled">开启思考 (自动)</option>
            <option value="low">低度思考</option>
            <option value="medium">中度思考</option>
            <option value="high">高度思考</option>
          </select>`);

fs.writeFileSync(chatPath, chatCode);
