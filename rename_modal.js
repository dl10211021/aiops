const fs = require('fs');
const pathModal = 'frontend/src/components/modals/LLMConfigModal.tsx';
let modalContent = fs.readFileSync(pathModal, 'utf8');

modalContent = modalContent.replace('⚙️ AI 大脑配置', '⚙️ 模型配置');
fs.writeFileSync(pathModal, modalContent);

const pathNav = 'frontend/src/components/layout/LeftNav.tsx';
if (fs.existsSync(pathNav)) {
    let navContent = fs.readFileSync(pathNav, 'utf8');
    navContent = navContent.replace('title="AI 配置"', 'title="模型配置"');
    fs.writeFileSync(pathNav, navContent);
}
