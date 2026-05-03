const fs = require('fs');
const path = 'frontend/src/components/chat/ChatWindow.tsx';
let file = fs.readFileSync(path, 'utf8');

// Add thinkingMode state
if (!file.includes('thinkingMode')) {
  file = file.replace(
    /const \[modelName, setModelName\] = useState\(\(\) =>\n\s*localStorage.getItem\('ops_model'\) \|\| 'gemini-2.5-flash-preview-05-20'\n\s*\)/,
    `const [modelName, setModelName] = useState(() =>\n    localStorage.getItem('ops_model') || 'gemini-2.5-flash'\n  )\n  const [thinkingMode, setThinkingMode] = useState(() =>\n    localStorage.getItem('ops_thinking') || 'off'\n  )`
  );
  
  // Save thinkingMode to localStorage
  file = file.replace(
    /useEffect\(\(\) => {\n\s*localStorage\.setItem\('ops_model', modelName\)\n\s*}, \[modelName\]\)/,
    `useEffect(() => {\n    localStorage.setItem('ops_model', modelName)\n  }, [modelName])\n\n  useEffect(() => {\n    localStorage.setItem('ops_thinking', thinkingMode)\n  }, [thinkingMode])`
  );

  // Update streamChat call
  file = file.replace(
    /await streamChat\(currentSessionId, userMsg\.content, modelName, controller\.signal\)/,
    `await streamChat(currentSessionId, userMsg.content, modelName, thinkingMode, controller.signal)`
  );

  // Add Thinking Mode dropdown next to Model selector
  file = file.replace(
    /\{\/\* Model selector \*\/\}/,
    `{/* Thinking Mode selector */}
          <select
            value={thinkingMode}
            onChange={(e) => setThinkingMode(e.target.value)}
            className="bg-ops-surface0 text-ops-text text-xs rounded px-2 py-1.5 border border-ops-surface1 outline-none self-end"
          >
            <option value="off">默认思维</option>
            <option value="low">低度思考</option>
            <option value="medium">中度思考</option>
            <option value="high">高度思考</option>
          </select>
          
          {/* Model selector */}`
  );
  
  fs.writeFileSync(path, file);
}
