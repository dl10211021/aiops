const fs = require('fs');
let chatPath = 'frontend/src/components/chat/ChatWindow.tsx';
let code = fs.readFileSync(chatPath, 'utf8');

code = code.replace(/availableModels\.map\(\(m\) => <option key=\{m\} value=\{m\}>\{m\}<\/option>\)/, 
  `availableModels.map(group => (
    <optgroup key={group.provider_id} label={group.provider_name}>
      {group.models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
    </optgroup>
  ))`);

fs.writeFileSync(chatPath, code);
