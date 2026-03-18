const fs = require('fs');

const modalPath = 'frontend/src/components/modals/LLMConfigModal.tsx';
let modalCode = fs.readFileSync(modalPath, 'utf8');

// The user says "测试动态拉取模型无法点击". Let's check why the button might be disabled or failing.
// Looking at the code:
// <button onClick={handleTestModels} className="text-xs bg-ops-surface1 hover:bg-ops-surface2 text-ops-text px-3 py-1.5 rounded transition-colors">
// 🔍 测试全局连接 & 动态获取模型
// </button>
// It doesn't seem to be disabled by state, except maybe the click area is blocked?
// Or maybe saving throws an error and interrupts handleTestModels.

modalCode = modalCode.replace(
  /const handleTestModels = async \(\) => \{\n\s*try \{\n\s*await updateProviders\(providers\)/,
  `const handleTestModels = async () => {\n    try {\n      try { await updateProviders(providers) } catch (e) { console.warn('Save before test failed', e) }`
);

// Another possibility: The modal isn't rendering because Vite wasn't serving the new code due to a hard reload issue or port change.
// But the user said "现在模型界面正常了", meaning the UI did update.
// Why would the button not be clickable? 
// "无法点击" often means z-index issue, or disabled, or it errors out immediately silently.
// Let's add a console.log to be sure.

modalCode = modalCode.replace(
  /const handleTestModels = async \(\) => \{/,
  `const handleTestModels = async () => {\n    console.log("Testing models...");`
);

fs.writeFileSync(modalPath, modalCode);
