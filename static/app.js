let currentSessionId = null;
        let sessions = {};
        let currentHost = ''; // 记录当前连接的主机名
        let currentRemark = ''; // 记录当前连接的备注
        let isReadWriteMode = false;
        const apiBaseUrl = '/api/v1';
let currentLoadedRegistry = [];
let loadedAssetsList = [];
let collapsedGroups = new Set(); // #21: 记录被折叠的分组

async function fetchSkills() {
    if (currentLoadedRegistry.length > 0) return currentLoadedRegistry;
    try {
        const response = await fetch(`${apiBaseUrl}/skills/registry`);
        const resData = await response.json();
        if (response.ok && resData.status === "success") {
            currentLoadedRegistry = resData.data.registry;
            return currentLoadedRegistry;
        }
    } catch (e) { console.error(e); }
    return [];
}

async function loadSkillsRegistry(checkedSet = null) {
    const activeSet = checkedSet || new Set();
    const registry = await fetchSkills();
    const container = document.getElementById("skillsCheckboxList");
    if (!container) return;
    if (!registry || registry.length === 0) {
        container.innerHTML = "<div class='text-gray-500 italic p-2 text-center'>暂未安装任何技能包。</div>";
        return;
    }
    const installedSkills = registry.filter(s => !s.is_market);
    if (installedSkills.length === 0) {
        container.innerHTML = "<div class='text-gray-500 italic p-2 text-center'>暂未安装任何技能包。</div>";
        return;
    }
    container.innerHTML = installedSkills.map(skill => {
        const isChecked = activeSet.has(skill.id) ? "checked" : "";
        return `<label class="flex items-start space-x-2 p-1.5 hover:bg-gray-800 rounded cursor-pointer transition">
            <input type="checkbox" value="${escapeHTML(skill.id)}" ${isChecked} class="mt-0.5 rounded bg-gray-900 border-gray-700 text-opsAccent focus:ring-0">
            <div class="flex flex-col">
                <span class="font-bold text-[10px] text-gray-300 leading-tight">${escapeHTML(skill.name)}</span>
                <span class="text-[9px] text-gray-500 leading-tight truncate max-w-[120px]" title="${escapeHTML(skill.description)}">${escapeHTML(skill.description)}</span>
            </div>
        </label>`;
    }).join("");
}

async function readFullSkillMd(skillId) {
    try {
        const res = await fetch(`${apiBaseUrl}/skills/registry/${skillId}`);
        const data = await res.json();
        if (res.ok && data.status === "success") {
            alert("【技能文档】\\n" + data.data.instructions.substring(0, 1000) + "...");
        } else {
            alert("获取详情失败");
        }
    } catch(e) {
        alert("网络异常");
    }
}


        // 页面加载时恢复上一次保存的连接参数
        // original DOMContentLoaded logic moved

        async function toggleModal(modalID){
            const modal = document.getElementById(modalID);
            if(!modal) { console.error('Modal not found:', modalID); return; }
            modal.classList.toggle('hidden');
            
            if (modalID === 'connModal' && !modal.classList.contains('hidden')) {
                const _el_connError = document.getElementById('connError'); if(_el_connError) _el_connError.classList.add('hidden');
                currentLoadedRegistry = []; // 强制清除缓存，从后端拉取最新
                await loadSkillsRegistry();
            }
            if (modalID === 'knowledgeModal' && !modal.classList.contains('hidden')) {
                const _el_kbUploadMsg = document.getElementById('kbUploadMsg'); if(_el_kbUploadMsg) _el_kbUploadMsg.classList.add('hidden');
                document.getElementById('kbFileInput').value = '';
                document.getElementById('kbFileName').innerText = '';
                await fetchKnowledgeDocuments();
            }
        }

        async function migrateSkill(sourcePath, folderName) {
            try {
                const response = await fetch(`${apiBaseUrl}/skills/migrate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ source_path: sourcePath, target_dir_name: folderName })
                });
                const data = await response.json();
                if (response.ok && data.status === 'success') {
                    alert(data.message);
                    currentLoadedRegistry = []; // 清空前端缓存强制刷新
                    openSkillOverview(); 
                    const _el_scanResultPanel = document.getElementById('scanResultPanel'); if(_el_scanResultPanel) _el_scanResultPanel.classList.add('hidden');
                } else {
                    alert(data.message || '迁移失败');
                }
            } catch (e) { alert("网络请求失败"); }
        }

        async function scanLocalSkills() {
            try {
                const response = await fetch(`${apiBaseUrl}/skills/scan`, { method: 'POST' });
                const data = await response.json();
                if (response.ok && data.status === 'success') {
                    alert(data.message);
                    currentLoadedRegistry = [];
                    openSkillOverview();
                } else {
                    alert(data.message || '扫描失败');
                }
            } catch(e) {
                alert("网络异常: " + e.message);
            }
        }

        async function launchSkillCreatorCLI() {
            try {
                // 1. 发起建立虚拟会话请求，连接 localhost，挂载 skill-creator
                const response = await fetch(`${apiBaseUrl}/connect`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        host: "localhost", 
                        port: 22, 
                        username: "dev_user", 
                        password: "", 
                        allow_modifications: true, 
                        active_skills: ["skill-creator"], 
                        agent_profile: "default", 
                        remark: "技能研发 CLI", 
                        protocol: "virtual", 
                        extra_args: {} 
                    })
                });
                
                const data = await response.json();
                if (response.ok && data.status === 'success') {
                    const sid = data.data.session_id;
                    currentSessionId = sid;
                    currentHost = "localhost";
                    currentRemark = "技能研发 CLI";
                    isReadWriteMode = true;
                    
                    const defaultModel = localStorage.getItem('opscore_default_model') || document.getElementById('modelSelector').value;
                    
                    sessions[sid] = {
                        id: sid, host: "localhost", remark: "技能研发 CLI", isReadWriteMode: true, skills: ["skill-creator"], agentProfile: "default", user: "dev_user", protocol: "virtual", extra_args: {}, heartbeatEnabled: false, selectedModel: defaultModel
                    };
                    
                    // 2. 切换到 AI 聊天界面
                    switchView('chatView');
                    
                    updateModeUI();
                    updateHeartbeatUI();
                    
                    const _el_noSessionHint = document.getElementById('noSessionHint'); if(_el_noSessionHint) _el_noSessionHint.classList.add('hidden');
                    const _el2_activeSessionContainer = document.getElementById('activeSessionContainer'); if(_el2_activeSessionContainer) _el2_activeSessionContainer.classList.remove('hidden');
                    const _elT_sideSessionInfo = document.getElementById('sideSessionInfo'); if(_elT_sideSessionInfo) _elT_sideSessionInfo.innerText = `dev_user@localhost`;
                    const _el2_topBadge = document.getElementById('topBadge'); if(_el2_topBadge) _el2_topBadge.classList.remove('hidden');
                    
                    const chatHtml = `<div id="chatContainer_${sid}" class="absolute inset-0 overflow-y-auto p-6 space-y-6 hidden"></div>`;
                    document.getElementById('mainChatWrapper').insertAdjacentHTML('beforeend', chatHtml);
                    switchSession(sid);
                    
                    const _el_welcomeBox = document.getElementById('welcomeBox'); if(_el_welcomeBox) _el_welcomeBox.classList.add('hidden');
                    const _elT_topMountedSkillsCount = document.getElementById('topMountedSkillsCount'); if(_elT_topMountedSkillsCount) _elT_topMountedSkillsCount.innerText = "1";
                    
                    // 3. 初始问候提示
                    addSystemMessage(`🚀 [开发者模式] 已成功唤醒本地研发 CLI 环境，已挂载「Skill Creator」核心能力，并授予读写特权。`);
                    appendAIBubbleSkeleton();
                    setTimeout(() => {
                        const statusEl = document.getElementById(currentAiBubbleId + '_status');
                        const textEl = document.getElementById(currentAiBubbleId + '_text');
                        statusEl.classList.add('hidden');
                        textEl.innerHTML = DOMPurify.sanitize(marked.parse("**系统已就绪。**\n您可以在此处自由发挥，指挥我为您编写、测试并创建新的技能卡带。例如您可以对我说：\n`帮我在 my_custom_skills 下创建一个名为 db-auditor 的技能，要求...`"));
                        scrollToBottom();
                    }, 500);

                } else {
                    alert("唤醒开发 CLI 失败：" + (data.detail || data.message));
                }
            } catch(e) {
                alert("网络异常: " + e.message);
            }
        }

        // --- 辅助 UI ---
        async function togglePermission(newMode) {
            if(!currentSessionId) return;
            try {
                const response = await fetch(`${apiBaseUrl}/session/${currentSessionId}/permission`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ allow_modifications: newMode })
                });
                
                if(response.ok) {
                    isReadWriteMode = newMode;
                    if(sessions[currentSessionId]) sessions[currentSessionId].isReadWriteMode = newMode;
                    updateModeUI();
                    
                    const actionLog = newMode 
                        ? '🔴 权限已升级：当前会话已授予 AI【读写修改】最高权限。' 
                        : '🟢 权限已降级：当前会话已恢复为【诊断只读】安全模式。';
                    addSystemMessage(actionLog);
                }
            } catch(e) { alert('权限切换失败'); }
        }

        async function toggleHeartbeat() {
            if(!currentSessionId) return;
            const session = sessions[currentSessionId];
            if(!session) return;
            const newMode = !session.heartbeatEnabled;
            
            try {
                const response = await fetch(`${apiBaseUrl}/session/${currentSessionId}/heartbeat`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ heartbeat_enabled: newMode })
                });
                
                if(response.ok) {
                    session.heartbeatEnabled = newMode;
                    updateHeartbeatUI();
                    
                    const actionLog = newMode 
                        ? '❤️ [后台心跳已开启] AI 专家将在空闲时主动巡检并通报系统状态。' 
                        : '💔 [后台心跳已关闭] AI 专家已转为被动响应模式。';
                    addSystemMessage(actionLog);
                }
            } catch(e) { alert('心跳切换失败'); }
        }

        function updateHeartbeatUI() {
            if(!currentSessionId) return;
            const session = sessions[currentSessionId];
            const btn = document.getElementById('heartbeatToggleBtn');
            const icon = document.getElementById('heartbeatIcon');
            const text = document.getElementById('heartbeatText');
            
            btn.classList.remove('hidden');
            if (session && session.heartbeatEnabled) {
                icon.className = "fa-solid fa-heart mr-1.5 text-opsAlert animate-pulse";
                text.innerText = "心跳运行中";
                text.className = "text-opsAlert font-bold";
            } else {
                icon.className = "fa-regular fa-heart mr-1.5 text-gray-500";
                text.innerText = "心跳关闭";
                text.className = "text-gray-500";
            }
        }

        // 定时轮询获取后台心跳推送
        setInterval(async () => {
            try {
                const response = await fetch(`${apiBaseUrl}/sessions/poll_all`);
                const data = await response.json();
                if(response.ok && data.status === 'success' && data.data.updates) {
                    for (const [sid, messages] of Object.entries(data.data.updates)) {
                        if (!messages || messages.length === 0) continue;

                        // Ensure chat container exists for this session
                        if (!document.getElementById('chatContainer_' + sid)) {
                            const chatHtml = `<div id="chatContainer_${sid}" class="absolute inset-0 overflow-y-auto p-6 space-y-6 hidden"></div>`;
                            document.getElementById('mainChatWrapper').insertAdjacentHTML('beforeend', chatHtml);
                        }

                        messages.forEach(msg => {
                            const { bubbleId, execId } = appendAIBubbleSkeleton(sid);
                            const statusEl = document.getElementById(bubbleId + '_status');
                            const textEl = document.getElementById(bubbleId + '_text');
                            statusEl.classList.add('hidden');
                            textEl.innerHTML = DOMPurify.sanitize(marked.parse(msg));

                            // Visual indicator for background activity if looking at another session
                            if (currentSessionId !== sid) {
                                // Add a highlight effect on the sidebar item
                                renderSidebar(); // Rerendering sidebar might be heavy, but let's assume it's okay for now.
                            } else {
                                scrollToBottom();
                            }
                        });
                    }
                }
            } catch(e) {}
        }, 5000);

        function setLLMPreset(type) {
            const urlInput = document.getElementById('apiBaseUrlInput');
            const keyInput = document.getElementById('apiKeyInput');
            if (type === 'gemini') {
                urlInput.value = 'https://generativelanguage.googleapis.com/v1beta/openai/';
                keyInput.placeholder = '输入 Gemini API Key';
            } else if (type === 'ollama') {
                urlInput.value = 'http://localhost:11434/v1/';
                keyInput.value = 'ollama'; 
                keyInput.placeholder = 'Ollama 无需真实Key';
            } else if (type === 'openai') {
                urlInput.value = 'https://api.openai.com/v1/';
                keyInput.value = '';
                keyInput.placeholder = '输入 OpenAI API Key';
            } else if (type === 'vllm') {
                urlInput.value = 'http://localhost:8000/v1/'; // vLLM 默认端口
                keyInput.value = 'vllm-key';
                keyInput.placeholder = '输入 vLLM API Key (如果有)';
            } else if (type === 'deepseek') {
                urlInput.value = 'https://api.deepseek.com/v1/';
                keyInput.value = '';
                keyInput.placeholder = '输入 DeepSeek API Key';
            } else if (type === 'anthropic') {
                // OpenAI compatible anthropic endpoint if they use proxy, or we leave it for standard OpenAI format
                urlInput.value = 'https://api.anthropic.com/v1/';
                keyInput.value = '';
                keyInput.placeholder = '输入 Anthropic API Key';
            }
        }

        async function fetchAvailableModels() {
            try {
                const response = await fetch(`${apiBaseUrl}/config/models`);
                const data = await response.json();
                if (response.ok && data.status === 'success' && data.data.models && data.data.models.length > 0) {
                    const select = document.getElementById('modelSelector');
                    const currentVal = select.value;
                    
                    let html = '';
                    // 优先把常用的模型放前面
                    const preferred = ['gemini-2.5-flash', 'gemini-2.5-pro', 'deepseek-chat', 'deepseek-coder', 'gpt-4o', 'gpt-4-turbo', 'qwen2.5', 'llama3', 'claude-3-5-sonnet'];
                    const availableModels = data.data.models;
                    
                    // 排序: preferred先，然后按字母排序
                    availableModels.sort((a, b) => {
                        const idxA = preferred.findIndex(p => a.includes(p));
                        const idxB = preferred.findIndex(p => b.includes(p));
                        if (idxA !== -1 && idxB !== -1) return idxA - idxB;
                        if (idxA !== -1) return -1;
                        if (idxB !== -1) return 1;
                        return a.localeCompare(b);
                    });

                    html = availableModels.map(m => `<option value="${m}">${m}</option>`).join('');
                    select.innerHTML = html;
                    
                    // 尝试保持之前选中的模型，或者从本地缓存加载全局默认
                    const savedGlobalModel = localStorage.getItem('opscore_default_model');
                    if(availableModels.includes(currentVal) && currentVal) {
                        select.value = currentVal;
                    } else if (savedGlobalModel && availableModels.includes(savedGlobalModel)) {
                        select.value = savedGlobalModel;
                    }
                    
                    // 添加 change 事件，保存全局默认，并且如果有活跃会话则保存给该会话
                    select.addEventListener('change', (e) => {
                        const newModel = e.target.value;
                        localStorage.setItem('opscore_default_model', newModel);
                        if (currentSessionId && sessions[currentSessionId]) {
                            sessions[currentSessionId].selectedModel = newModel;
                            // Add per-host model caching
                            const s = sessions[currentSessionId];
                            localStorage.setItem('opscore_model_' + s.host, newModel);
                        }
                    });
                }
            } catch (e) {
                console.log("获取动态模型列表失败，使用后备默认列表", e);
            }
        }

        async function testLLMConnection() {
            const baseUrl = document.getElementById('apiBaseUrlInput').value.trim();
            const apiKey = document.getElementById('apiKeyInput').value.trim();
            const btn = document.getElementById('btnTestLLM');
            const msgObj = document.getElementById('llmTestMsg');
            
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i>测试中...';
            btn.disabled = true;
            msgObj.classList.add('hidden');
            
            try {
                // We use the save endpoint first, then fetch models as a proxy for "testing connection"
                await fetch(`/api/v1/config/llm`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ base_url: baseUrl, api_key: apiKey })
                });
                
                const response = await fetch(`${apiBaseUrl}/config/models`);
                const data = await response.json();
                
                if (response.ok && data.status === 'success' && data.data.models && data.data.models.length > 0) {
                    msgObj.innerHTML = `<span class="text-opsSuccess"><i class="fa-solid fa-check mr-1"></i>连接成功！发现 ${data.data.models.length} 个可用模型。</span>`;
                    msgObj.classList.remove('hidden');
                    fetchAvailableModels(); // Update the dropdown
                } else {
                    msgObj.innerHTML = `<span class="text-opsAlert"><i class="fa-solid fa-xmark mr-1"></i>连接失败: 无法获取模型列表。</span>`;
                    msgObj.classList.remove('hidden');
                }
            } catch(e) {
                msgObj.innerHTML = `<span class="text-opsAlert"><i class="fa-solid fa-xmark mr-1"></i>测试失败: ${e.message}</span>`;
                msgObj.classList.remove('hidden');
            } finally {
                btn.innerHTML = '<i class="fa-solid fa-stethoscope mr-1"></i>测试连通性';
                btn.disabled = false;
            }
        }

        // ---【新功能】更新大模型后端 API 配置 ---
        async function saveApiConfig() {
            const baseUrl = document.getElementById('apiBaseUrlInput').value.trim();
            const apiKey = document.getElementById('apiKeyInput').value.trim();
            const saveMsg = document.getElementById('apiSaveMsg');
            
            try {
                // 这个接口我们在后端实现
                const response = await fetch(`/api/v1/config/llm`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ base_url: baseUrl, api_key: apiKey })
                });
                
                if (response.ok) {
                    saveMsg.classList.remove('hidden');
                    setTimeout(() => { 
                        saveMsg.classList.add('hidden'); 
                        toggleModal('apiConfigModal');
                    }, 1500);
                } else {
                    alert("配置保存失败");
                }
            } catch(e) {
                alert("网络异常: " + e.message);
            }
        }

                // ---【新功能】动态修改挂载技能 ---
                        async function openDynamicSkillsModal() {
                            if (!currentSessionId) {
                                alert("当前没有处于连接状态的会话，请先连接一台服务器！");
                                return;
                            }
                            
                            // Sync the current session skills before opening
                            let dynSkillIds = new Set();
                            if (sessions[currentSessionId] && sessions[currentSessionId].skills) {
                                dynSkillIds = new Set(sessions[currentSessionId].skills);
                            }
                            
                            toggleModal('dynamicSkillsModal');
        
                            const container = document.getElementById('dynamicSkillsCheckboxList');
                            currentLoadedRegistry = []; // 每次打开都强制清除缓存，从后端拉取最新
                    const registry = await fetchSkills();
        
                    const installedSkills = registry.filter(s => !s.is_market);            
            if (!installedSkills || installedSkills.length === 0) {
                container.innerHTML = '<div class="text-gray-500 italic p-2 text-center">暂未发现可用的私有技能卡带。<br>请前往【全局插件市场】选择复制。</div>';
                return;
            }

            container.innerHTML = installedSkills.map(skill => {
                const isChecked = dynSkillIds.has(skill.id) ? 'checked' : '';
                return `
                <label class="flex items-start space-x-2 p-2 hover:bg-gray-800 rounded cursor-pointer transition border border-transparent hover:border-gray-700 bg-gray-900/40">
                    <input type="checkbox" name="dyn_skill_checkbox" value="${escapeHTML(skill.id)}" ${isChecked} class="mt-1 rounded bg-gray-900 border-gray-700 text-opsAccent focus:ring-0 w-3.5 h-3.5 flex-shrink-0">
                    <div class="flex flex-col w-full">
                        <div class="font-bold text-xs text-opsAccent flex justify-between items-center">
                            <span>${escapeHTML(skill.name)}</span>
                            <div class="flex items-center space-x-1.5">
                                <span class="text-gray-400 bg-gray-800 px-1.5 py-0.5 rounded text-[8px] border border-gray-700">${escapeHTML(skill.source_type || 'Unknown')}</span>
                                <span class="text-opsSuccess bg-opsSuccess/10 px-1.5 py-0.5 rounded text-[9px] border border-opsSuccess/20">${skill.tool_count} Tools</span>
                            </div>
                        </div>
                    </div>
                </label>
            `}).join('');
        }

        async function saveDynamicSkills() {
            if (!currentSessionId) return;
            const btn = document.getElementById('btnSaveDynamicSkills');
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i>保存中...';
            btn.disabled = true;
            
            const checkedSkills = Array.from(document.querySelectorAll('#dynamicSkillsCheckboxList input:checked')).map(el => el.value);
            
            try {
                const response = await fetch(`${apiBaseUrl}/session/${currentSessionId}/skills`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ active_skills: checkedSkills })
                });
                
                if (response.ok) {
                    if(sessions[currentSessionId]) sessions[currentSessionId].skills = checkedSkills;
                    const _elT_topMountedSkillsCount = document.getElementById('topMountedSkillsCount'); if(_elT_topMountedSkillsCount) _elT_topMountedSkillsCount.innerText = checkedSkills.length;
                    toggleModal('dynamicSkillsModal');
                    addSystemMessage(`🧩 [动态挂载更新]: 当前会话的挂载卡带已更新为 ${checkedSkills.length} 个。`);
                } else {
                    alert("配置更新失败");
                }
            } catch(e) {
                alert("网络异常: " + e.message);
            } finally {
                btn.innerHTML = '保存配置并生效 (Save)';
                btn.disabled = false;
            }
        }

        // 更新界面上的 [读写]/[只读] 状态
        function updateModeUI() {
            if (!currentSessionId) return;
            const modeTag = isReadWriteMode 
                ? '<span class="text-opsAlert font-bold ml-1 cursor-pointer hover:underline border border-opsAlert/50 px-1 rounded text-xs" onclick="togglePermission(false)">[读写特权]</span>' 
                : '<span class="text-opsSuccess ml-1 cursor-pointer hover:underline border border-opsSuccess/50 px-1 rounded text-xs" onclick="togglePermission(true)">[只读安全]</span>';
            
            const display = currentRemark ? '[' + currentRemark + '] ' + currentHost : currentHost;
            document.getElementById('topSessionName').innerHTML = `已接管: ${display} ${modeTag}`;
        }

        // 1. 发起网络连接，获取 Session
        function handleAssetCategoryChange() {
            const category = document.getElementById('connAssetCategory').value;
            
            // Labels
            document.getElementById('lblConnHost').innerText = category === 'api' ? 'API Endpoint URL:' : '主机/IP/URL:';
            document.getElementById('lblConnUser').innerText = category === 'api' ? 'Auth User (如需):' : '账号/用户名:';
            document.getElementById('lblConnPwd').innerText = category === 'api' ? 'API Token/Key:' : '密码/Token:';
            document.getElementById('lblConnPort').innerText = category === 'api' ? '保留:' : '端口:';
            
            // Default Ports & Visibility
            document.getElementById('fieldDbName').classList.add('hidden');
            document.getElementById('fieldEnablePwd').classList.add('hidden');
            document.getElementById('fieldAuthHeader').classList.add('hidden');
            
            if (category === 'linux') {
                document.getElementById('connPort').value = '22';
            } else if (category === 'windows') {
                document.getElementById('connPort').value = '5985'; // WinRM Default
            } else if (category === 'database') {
                document.getElementById('connPort').value = '3306';
                document.getElementById('fieldDbName').classList.remove('hidden');
            } else if (category === 'network') {
                document.getElementById('connPort').value = '22';
                document.getElementById('fieldEnablePwd').classList.remove('hidden');
            } else if (category === 'api') {
                document.getElementById('connPort').value = '';
                document.getElementById('fieldAuthHeader').classList.remove('hidden');
            }
            
            // Auto-check related skills (if they exist in the registry)
            // Example:
            if (category === 'database' && currentLoadedRegistry.some(s => s.id === 'database')) {
                const cb = document.querySelector("input[value='database']"); if(cb) cb.checked = true;
            }
            if (category === 'api' && currentLoadedRegistry.some(s => s.id === 'manage-engine')) {
                const cb2 = document.querySelector("input[value='manage-engine']"); if(cb2) cb2.checked = true;
            }
        }

        async function connectToServer() {
            const el = document.getElementById('connGroupName');
            const groupName = (el ? el.value.trim() : '') || '未分组';
            const remark = document.getElementById('connRemark').value.trim();
            const host = document.getElementById('connHost').value.trim();
            const portStr = document.getElementById('connPort').value;
            const port = portStr ? parseInt(portStr) : (document.getElementById('connAssetCategory').value === 'api' ? 443 : 22);
            const user = document.getElementById('connUser').value.trim();
            const pwd = document.getElementById('connPwd').value;
            const allowMod = document.getElementById('connAllowMod').checked;
            
            const category = document.getElementById('connAssetCategory').value;
            let protocol = 'virtual';
            if (category === 'linux') protocol = 'ssh';
            if (category === 'windows') protocol = 'winrm';
            
            let extraArgs = { device_type: category };
            
            // Build extraArgs dynamically
            if (category === 'database') {
                extraArgs.database = document.getElementById('connDbName').value.trim();
            } else if (category === 'network') {
                extraArgs.enable_password = document.getElementById('connEnablePwd').value;
            } else if (category === 'api') {
                extraArgs.auth_header = document.getElementById('connAuthHeader').value.trim();
            }
            
            const customHb = document.getElementById('connHeartbeatPrompt').value.trim();
            if (customHb) extraArgs.heartbeat_prompt = customHb;
            
            // Handle raw JSON append if any (from old textarea, now we use it as an advanced field)
            const extraArgsStr = document.getElementById('connExtraArgs').value.trim();
            if(extraArgsStr) {
                try { 
                    const parsed = JSON.parse(extraArgsStr); 
                    extraArgs = { ...extraArgs, ...parsed };
                }
                catch(e) { alert('Invalid JSON in extra arguments'); return; }
            }
            
            const agentProfile = document.getElementById('connAgentProfile').value;
            
            // 收集用户勾选了哪些能力卡带 (从维护的状态集合里取)
            const checkedSkills = Array.from(document.querySelectorAll('#skillsCheckboxList input:checked')).map(el => el.value);

            const btn = document.getElementById('connBtn');
            const errBox = document.getElementById('connError');

            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> 连接中...';
            btn.disabled = true;
            errBox.classList.add('hidden');

            try {
                const response = await fetch(`${apiBaseUrl}/connect`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ host: host, port: port, username: user, password: pwd, allow_modifications: allowMod, active_skills: checkedSkills, agent_profile: agentProfile, remark: remark, protocol: protocol, extra_args: extraArgs, group_name: groupName })
                });
                
                const data = await response.json();
                
                if(response.ok && data.status === 'success') {
                    const sid = data.data.session_id;
                    currentSessionId = sid;
                    currentHost = host;
                    currentRemark = remark;
                    isReadWriteMode = allowMod;
                    
                    const defaultModel = localStorage.getItem('opscore_default_model') || document.getElementById('modelSelector').value;
                    
                    sessions[sid] = {
                        id: sid, host: host, remark: remark, isReadWriteMode: allowMod, skills: checkedSkills, agentProfile: agentProfile, user: user, protocol: protocol, extra_args: extraArgs, heartbeatEnabled: false, selectedModel: defaultModel
                    };
                    
                    // 刷新 UI
                    updateModeUI();
                    const _el_noSessionHint = document.getElementById('noSessionHint'); if(_el_noSessionHint) _el_noSessionHint.classList.add('hidden');
                    const _el2_activeSessionContainer = document.getElementById('activeSessionContainer'); if(_el2_activeSessionContainer) _el2_activeSessionContainer.classList.remove('hidden');
                    const _elT_sideSessionInfo = document.getElementById('sideSessionInfo'); if(_elT_sideSessionInfo) _elT_sideSessionInfo.innerText = `${user}@${host}`;
                    const _el2_topBadge = document.getElementById('topBadge'); if(_el2_topBadge) _el2_topBadge.classList.remove('hidden');
                    
                    // 为这个会话创建一个独立隔离的物理聊天房间
                    const chatHtml = `<div id="chatContainer_${sid}" class="absolute inset-0 overflow-y-auto p-6 space-y-6 hidden"></div>`;
                    document.getElementById('mainChatWrapper').insertAdjacentHTML('beforeend', chatHtml);
                    switchSession(sid);
                    
                    // --- 新增：持久化保存最新连接参数 ---
                                        localStorage.setItem('opscore_conn_cache', JSON.stringify({
                                            remark: remark, host: host, port: port, user: user, pwd: pwd, allowMod: allowMod, skills: checkedSkills, agentProfile: agentProfile, protocol: protocol, extraArgs: extraArgs, category: category
                                        }));

                    // 隐藏欢迎提示，添加系统消息
                    const _el_welcomeBox = document.getElementById('welcomeBox'); if(_el_welcomeBox) _el_welcomeBox.classList.add('hidden');
                    if(sessions[currentSessionId]) sessions[currentSessionId].skills = checkedSkills;
                    const _elT_topMountedSkillsCount = document.getElementById('topMountedSkillsCount'); if(_elT_topMountedSkillsCount) _elT_topMountedSkillsCount.innerText = checkedSkills.length;
                    
                    const msgAlias = remark ? `[${remark}] ` : '';
                    addSystemMessage(`🔌 成功连接到 ${msgAlias}${user}@${host} | 当前安全策略: ${allowMod ? '🔴 读写特权模式' : '🟢 诊断只读模式'}`);
                    toggleModal('connModal');
                } else {
                    errBox.innerText = data.detail || data.message || "连接失败";
                    errBox.classList.remove('hidden');
                }
            } catch(e) {
                errBox.innerText = "网络异常或后端服务未启动: " + e.message;
                errBox.classList.remove('hidden');
            } finally {
                btn.innerHTML = '连接 (Connect)';
                btn.disabled = false;
            }
        }

                let currentAiBubbleId = null;
                let currentAiMarkdown = '';
                let executionContainerId = null;
                let currentChatController = null;
        
                async function stopChatSession() {
                    if (!currentSessionId) return;
                    
                    // 1. Abort the frontend fetch stream if it's active
                    if (currentChatController) {
                        currentChatController.abort();
                        currentChatController = null;
                    }
                    
                    try {
                        const res = await fetch(`${apiBaseUrl}/session/${currentSessionId}/stop`, {
                            method: 'POST'
                        });
                        if (res.ok) {
                            appendSystemMessage("🛑 已向后台发送终止任务的信号。");
                        }
                    } catch (e) {
                        console.error("Stop session failed:", e);
                    }
                }
        
                // 2. 发送用户消息并请求大模型 (SSE 流式版)
                async function sendChatMessage() {
                    if(!currentSessionId) {
                        alert("请先点击左上角加号，连接一台服务器！");
                        return;
                    }
        
                    const inputEl = document.getElementById('chatInput');
                    const msg = inputEl.value.trim();
                    if(!msg) return;
        
                    inputEl.value = ''; // 清空输入框
                    inputEl.style.height = 'auto';
        
                    // 插入用户气泡
                    appendUserBubble(msg);
        
                    // 插入初始的 AI 气泡和执行框
                    const { bubbleId, execId } = appendAIBubbleSkeleton();
                    currentAiBubbleId = bubbleId;
                    executionContainerId = execId;
                    currentAiMarkdown = '';
        
                    const selectedModel = document.getElementById('modelSelector').value;
        
                    const btnStopChat = document.getElementById('btnStopChat');
                    if (btnStopChat) btnStopChat.classList.remove('hidden');
                    
                    // Abort previous stream if still running
                    if (currentChatController) {
                        currentChatController.abort();
                    }
                    currentChatController = new AbortController();
        
                    try {
                        const response = await fetch(`${apiBaseUrl}/chat`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ session_id: currentSessionId, message: msg, model_name: selectedModel }),
                            signal: currentChatController.signal
                        });                
                if (!response.ok) {
                    appendSystemMessage(`❌ 请求出错`);
                    return;
                }

                // --- 解析 SSE 流 ---
                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    
                    // 将可能不完整的最后一行留在 buffer 中等待下个 chunk 拼接
                    buffer = lines.pop();
                    
                    for (let line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                handleStreamEvent(data);
                            } catch(e) { 
                                console.error("JSON parse error on chunk, skipping:", line, e); 
                            }
                        }
                    }
                }
            } catch(e) {
                if (e.name === 'AbortError') {
                    appendSystemMessage('⏹️ 请求已取消。');
                } else {
                    appendSystemMessage(`❌ 网络异常: ${e.message}`);
                }
            } finally {
                const btnStopChat = document.getElementById('btnStopChat');
                if (btnStopChat) btnStopChat.classList.add('hidden');
            }
        }

        // 处理从后端源源不断发来的事件流
        function handleStreamEvent(data) {
            const statusEl = document.getElementById(currentAiBubbleId + '_status');
            const execContainer = document.getElementById(executionContainerId);
            
            if (data.type === 'status') {
                statusEl.innerText = data.content;
                statusEl.classList.remove('hidden');
            } 
            else if (data.type === 'tool_ask_approval') {
                execContainer.classList.remove('hidden');
                statusEl.classList.add('hidden');
                
                const uniqueId = `execLog_${currentAiBubbleId}_${data.id}`;
                const html = `
                <div class="mt-2 text-xs border border-yellow-700/50 rounded bg-yellow-900/20 overflow-hidden" id="card_${uniqueId}">
                    <div class="flex items-center text-yellow-400 p-2 border-b border-yellow-800/50 bg-black/40">
                        <i id="icon_${uniqueId}" class="fa-solid fa-triangle-exclamation mr-2 text-yellow-400"></i>
                        <span>等待授权: <span class="text-opsAccent font-mono">${data.tool}</span></span>
                    </div>
                    <div class="p-2 font-mono text-gray-400 bg-black/20">${escapeHTML(data.cmd)}</div>
                    <div class="p-2 flex gap-2 border-t border-yellow-800/50" id="approval_btns_${uniqueId}">
                        <button onclick="submitApproval('${data.id}', true, '${uniqueId}')" class="bg-green-600 hover:bg-green-500 text-white px-3 py-1 rounded">允许</button>
                        <button onclick="submitApproval('${data.id}', false, '${uniqueId}')" class="bg-red-600 hover:bg-red-500 text-white px-3 py-1 rounded">拒绝</button>
                        <label class="flex items-center text-gray-400 ml-2"><input type="checkbox" id="auto_approve_${data.id}" class="mr-1"> 本次自动允许</label>
                    </div>
                    <div id="res_${uniqueId}" class="hidden p-2 text-gray-400 font-mono whitespace-pre-wrap border-t border-gray-800 bg-black/50 text-[10px]"></div>
                </div>`;
                execContainer.insertAdjacentHTML('beforeend', html);
                scrollToBottom();
            }
            else if (data.type === 'tool_start') {
                execContainer.classList.remove('hidden');
                statusEl.classList.add('hidden'); // 隐藏通用状态
                
                const uniqueId = `execLog_${currentAiBubbleId}_${data.id}`;
                const html = `
                <div class="mt-2 text-xs border border-gray-700 rounded bg-gray-900 overflow-hidden" id="card_${uniqueId}">
                    <div class="flex items-center text-gray-400 p-2 border-b border-gray-800 bg-black/40">
                        <i id="icon_${uniqueId}" class="fa-solid fa-circle-notch fa-spin mr-2 text-opsAccent"></i>
                        <span>正在执行: <span class="text-opsAccent font-mono">${data.tool}</span></span>
                    </div>
                    <div class="p-2 font-mono text-gray-500 bg-black/20">${escapeHTML(data.cmd)}</div>
                    <div id="res_${uniqueId}" class="hidden p-2 text-gray-400 font-mono whitespace-pre-wrap border-t border-gray-800 bg-black/50 text-[10px]"></div>
                </div>`;
                execContainer.insertAdjacentHTML('beforeend', html);
                scrollToBottom();
            }
            else if (data.type === 'tool_end') {
                const uniqueId = `execLog_${currentAiBubbleId}_${data.id}`;
                const iconEl = document.getElementById(`icon_${uniqueId}`);
                const resEl = document.getElementById(`res_${uniqueId}`);
                
                if(iconEl) {
                    iconEl.className = "fa-solid fa-check mr-2 text-opsSuccess";
                }
                if(resEl) {
                    resEl.innerHTML = `<span class="text-gray-600">Return: </span><br>${escapeHTML(data.result)}`;
                    resEl.classList.remove('hidden');
                }
                scrollToBottom();
            }
            else if (data.type === 'chunk') {
                statusEl.classList.add('hidden'); // 开始打字就隐藏 status
                currentAiMarkdown += data.content;
                // 用 marked 渲染 markdown 到目标 div
                document.getElementById(currentAiBubbleId + '_text').innerHTML = DOMPurify.sanitize(marked.parse(currentAiMarkdown));
                scrollToBottom();
            }
            else if (data.type === 'error') {
                statusEl.innerText = "❌ " + data.content;
                statusEl.classList.remove('hidden');
                statusEl.classList.remove('text-gray-400');
                statusEl.classList.add('text-opsAlert');
            }
            else if (data.type === 'done') {
                if (!statusEl.classList.contains('text-opsAlert')) {
                    statusEl.classList.add('hidden');
                }
            }
        }

                                // --- 辅助 UI ---
                                function appendAIBubbleSkeleton(sid = currentSessionId) {
                                    const bubbleId = 'ai_' + Date.now() + Math.floor(Math.random()*1000);
                                    const execId = 'exec_' + Date.now() + Math.floor(Math.random()*1000);
                                    const chatContainer = document.getElementById('chatContainer_' + sid);  
                                    const timeStr = new Date().toLocaleString();
                        
                                    const html = `
                                    <div class="flex items-start space-x-3 mb-4">
                                        <div class="w-8 h-8 rounded-full bg-opsAccent flex items-center justify-center text-opsDark text-sm font-bold shadow-lg flex-shrink-0 mt-1"><i class="fa-solid fa-bolt"></i></div>
                                        <div class="flex-1 max-w-4xl space-y-2">
                                            <!-- 执行轨迹容器 -->
                                            <div id="${execId}" class="hidden bg-gray-800/40 rounded-lg px-4 py-2 border border-dashed border-gray-700 shadow-sm">
                                                <div class="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">🤖 引擎执行轨迹 (Execution Path)</div>
                                            </div>
                
                                            <!-- 主回复气泡 -->
                                            <div class="bg-gray-800/80 rounded-lg rounded-tl-none px-5 py-4 shadow-md border border-gray-700 text-sm leading-relaxed">
                                                <div id="${bubbleId}_status" class="text-xs text-opsAccent animate-pulse font-mono"><i class="fa-solid fa-satellite-dish mr-1"></i>正在连接到大脑...</div>
                                                <div id="${bubbleId}_text" class="markdown-body"></div>
                                            </div>
                                            <div class="text-[9px] text-gray-500 mt-1 pl-1">${timeStr}</div>
                                        </div>
                                    </div>`;
                                    chatContainer.insertAdjacentHTML('beforeend', html);
                                    if(sid === currentSessionId) scrollToBottom();
                                    return { bubbleId, execId };
                                }        // 插入用户气泡
        function appendUserBubble(text) {
            const chatContainer = document.getElementById('chatContainer_' + currentSessionId);
            const timeStr = new Date().toLocaleString();
            const html = `
            <div class="flex items-start justify-end space-x-3 mb-4">
                <div class="flex flex-col items-end">
                    <div class="bg-gray-800 rounded-lg rounded-tr-none px-4 py-3 max-w-2xl shadow-md border border-gray-700 text-sm whitespace-pre-wrap">${escapeHTML(text)}</div>
                    <div class="text-[9px] text-gray-500 mt-1">${timeStr}</div>
                </div>
                <div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold shadow-lg flex-shrink-0">U</div>
            </div>`;
            chatContainer.insertAdjacentHTML('beforeend', html);
            scrollToBottom();
        }

        function addSystemMessage(text) {
            addSystemMessageTo(currentSessionId, text);
        }

        function addSystemMessageTo(sid, text) {
            const chatContainer = document.getElementById('chatContainer_' + sid);
            if(chatContainer) {
                chatContainer.insertAdjacentHTML('beforeend', `<div class="text-center text-xs text-gray-500 font-mono my-2">${text}</div>`);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }

        function renderHistoricalUserBubble(sid, text, timestamp) {
            const chatContainer = document.getElementById('chatContainer_' + sid);
            if(!chatContainer) return;
            const timeStr = timestamp ? new Date(timestamp).toLocaleString() : new Date().toLocaleString();
            const html = `
            <div class="flex items-start justify-end space-x-3 mb-4 opacity-70 hover:opacity-100 transition">
                <div class="flex flex-col items-end">
                    <div class="bg-gray-800 rounded-lg rounded-tr-none px-4 py-3 max-w-2xl shadow-md border border-gray-700 text-sm whitespace-pre-wrap">${escapeHTML(text)}</div>
                    <div class="text-[9px] text-gray-500 mt-1">${timeStr}</div>
                </div>
                <div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold shadow-lg flex-shrink-0">U</div>
            </div>`;
            chatContainer.insertAdjacentHTML('beforeend', html);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function renderHistoricalAIBubble(sid, markdownText, timestamp) {
            const chatContainer = document.getElementById('chatContainer_' + sid);
            if(!chatContainer) return;
            const timeStr = timestamp ? new Date(timestamp).toLocaleString() : new Date().toLocaleString();
            const html = `
            <div class="flex items-start space-x-3 mb-4 opacity-70 hover:opacity-100 transition">
                <div class="w-8 h-8 rounded-full bg-opsAccent flex items-center justify-center text-opsDark text-sm font-bold shadow-lg flex-shrink-0 mt-1"><i class="fa-solid fa-bolt"></i></div>
                <div class="flex-1 max-w-4xl space-y-2">
                    <div class="bg-gray-800/80 rounded-lg rounded-tl-none px-5 py-4 shadow-md border border-gray-700 text-sm leading-relaxed">
                        <div class="markdown-body">${DOMPurify.sanitize(marked.parse(markdownText))}</div>
                    </div>
                    <div class="text-[9px] text-gray-500 mt-1 pl-1">${timeStr}</div>
                </div>
            </div>`;
            chatContainer.insertAdjacentHTML('beforeend', html);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        // 快捷键支持
        function handleEnter(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        }

        function scrollToBottom() {
            const chatContainer = document.getElementById('chatContainer_' + currentSessionId);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function escapeHTML(str) {
            return str.replace(/[&<>'"]/g, tag => ({'&': '&amp;','<': '&lt;','>': '&gt;',"'": '&#39;','"': '&quot;'}[tag]));
        }

        // ---【新功能】告警通道配置 ---
        async function saveNotificationConfig() {
            const wechat = document.getElementById('wechatWebhookInput').value.trim();
            const dingtalk = document.getElementById('dingtalkWebhookInput').value.trim();
            const email = document.getElementById('emailInput').value.trim();
            const msgObj = document.getElementById('notificationSaveMsg');

            try {
                // 先获取当前完整配置，避免覆盖未展示的字段
                let currentConfig = {};
                try {
                    const getRes = await fetch(`${apiBaseUrl}/config/notifications`);
                    const getData = await getRes.json();
                    if (getRes.ok && getData.status === 'success') {
                        currentConfig = getData.data;
                    }
                } catch(e) { /* 获取失败则使用默认值 */ }

                const payload = {
                    ...currentConfig,
                    wechat_webhook: wechat,
                    wechat_enabled: !!wechat,
                    dingtalk_webhook: dingtalk,
                    dingtalk_enabled: !!dingtalk,
                    email_address: email,
                    email_enabled: !!email
                };

                const response = await fetch(`${apiBaseUrl}/config/notifications`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (response.ok) {
                    msgObj.classList.remove('hidden');
                    setTimeout(() => { 
                        msgObj.classList.add('hidden'); 
                        toggleModal('notificationModal');
                    }, 1500);
                }
            } catch (e) { alert("保存失败: " + e.message); }
        }

        // ---【新功能】RAG 知识库文档管理 (大盘模式) ---
        let currentKbFiles = [];

        async function fetchKnowledgeDocuments() {
            const listEl = document.getElementById('kbDocList');
            if(!listEl) return;
            listEl.innerHTML = '<div class="text-center text-sm text-gray-500 italic mt-20"><i class="fa-solid fa-spinner fa-spin mr-2"></i>正在加载向量数据...</div>';
            
            try {
                const response = await fetch(`${apiBaseUrl}/knowledge/list`);
                const data = await response.json();
                if (response.ok && data.status === 'success') {
                    currentKbFiles = data.data.files;
                    document.getElementById('kbDocCount').innerText = currentKbFiles.length;
                    renderKbList(currentKbFiles);
                }
            } catch (e) {
                listEl.innerHTML = `<div class="text-center text-xs text-opsAlert mt-10">加载失败: ${e.message}</div>`;
            }
        }
        
        function filterKbList() {
            const query = document.getElementById('kbSearchInput').value.toLowerCase();
            const filtered = currentKbFiles.filter(f => f.toLowerCase().includes(query));
            renderKbList(filtered);
        }

        function renderKbList(files) {
            const listEl = document.getElementById('kbDocList');
            if (files.length === 0) {
                listEl.innerHTML = '<div class="text-center text-sm text-gray-600 mt-20 italic">未能找到符合条件的文档记录。</div>';
                return;
            }
            
            listEl.innerHTML = files.map(file => `
                <div class="flex items-center bg-gray-800/50 hover:bg-gray-800 border border-gray-700/50 p-4 rounded-lg text-sm group transition">
                    <div class="flex-[3] flex items-center text-gray-300">
                        <i class="fa-solid fa-file-pdf text-xl text-opsAlert mr-3 opacity-80" style="display: ${file.endsWith('.pdf') ? 'inline-block' : 'none'}"></i>
                        <i class="fa-solid fa-file-word text-xl text-blue-500 mr-3 opacity-80" style="display: ${file.endsWith('.docx') ? 'inline-block' : 'none'}"></i>
                        <i class="fa-solid fa-file-lines text-xl text-gray-500 mr-3 opacity-80" style="display: ${!file.endsWith('.pdf') && !file.endsWith('.docx') ? 'inline-block' : 'none'}"></i>
                        <span class="font-mono truncate" title="${file}">${file}</span>
                    </div>
                    <div class="flex-1 text-center">
                        <span class="bg-opsSuccess/20 text-opsSuccess border border-opsSuccess/30 px-2 py-0.5 rounded-full text-xs"><i class="fa-solid fa-check-circle mr-1"></i>已向量化</span>
                    </div>
                    <div class="w-24 text-center">
                        <button onclick="deleteKnowledgeDocument('${file}')" class="text-gray-500 hover:text-white hover:bg-opsAlert/80 w-8 h-8 rounded transition" title="从数据库彻底抹除"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </div>
            `).join('');
        }

        async function deleteKnowledgeDocument(filename) {
            if(!confirm(`⚠️ 危险操作：\n\n确定要从知识库中彻底删除文档 "${filename}" 吗？\n这将会清除该文件对应的所有高维向量索引，AI 将失去相关的排障记忆。`)) return;
            
            try {
                const response = await fetch(`${apiBaseUrl}/knowledge/${encodeURIComponent(filename)}`, { method: 'DELETE' });
                const data = await response.json();
                if (response.ok && data.status === 'success') {
                    fetchKnowledgeDocuments();
                } else {
                    alert('删除失败: ' + data.message);
                }
            } catch(e) { alert('请求异常: ' + e.message); }
        }

        function updateKbFileLabel() {
            const input = document.getElementById('kbFileInput');
            const label = document.getElementById('kbFileName');
            if (input.files.length > 0) {
                label.classList.remove('hidden');
                label.innerText = Array.from(input.files).map(f => f.name).join('\n');
            } else {
                label.classList.add('hidden');
                label.innerText = '';
            }
        }

        async function uploadKnowledgeDocument() {
            const fileInput = document.getElementById('kbFileInput');
            const msgObj = document.getElementById('kbUploadMsg');
            
            if (!fileInput.files || fileInput.files.length === 0) {
                msgObj.innerText = '⚠️ 请至少选择一个文档，或直接将文件拖拽至上方虚线框内。';
                msgObj.className = 'text-opsAlert text-xs text-center mt-4 bg-gray-900/80 p-3 rounded-lg border border-opsAlert/50';
                msgObj.classList.remove('hidden');
                return;
            }

            msgObj.className = 'text-gray-300 text-xs text-center mt-4 bg-gray-900/80 p-3 rounded-lg border border-gray-700';
            msgObj.classList.remove('hidden');
            
            let successCount = 0;
            let failCount = 0;

            for (let i = 0; i < fileInput.files.length; i++) {
                const file = fileInput.files[i];
                msgObj.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-opsAccent mr-2"></i>正在向量化处理: <b>${file.name}</b> (${i+1}/${fileInput.files.length})`;
                
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch(`${apiBaseUrl}/knowledge/upload`, {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    if (response.ok && data.status === 'success') {
                        successCount++;
                    } else {
                        failCount++;
                        console.error("上传失败:", file.name, data.message);
                    }
                } catch (e) {
                    failCount++;
                    console.error("请求异常:", file.name, e);
                }
            }
            
            fileInput.value = '';
            updateKbFileLabel();
            fetchKnowledgeDocuments();
            
            if (failCount === 0) {
                msgObj.innerHTML = `<span class="text-opsSuccess"><i class="fa-solid fa-check-circle mr-1"></i> 全部 ${successCount} 个文档已成功切片并存入知识库！</span>`;
                setTimeout(() => { msgObj.classList.add('hidden'); }, 5000);
            } else {
                msgObj.innerHTML = `<span class="text-yellow-400"><i class="fa-solid fa-triangle-exclamation mr-1"></i> 处理完毕：${successCount} 成功, ${failCount} 失败 (详情请查看控制台)。</span>`;
            }
        }

        // ---【新功能】Cron 自动化巡检管理 ---
        function openCronModal() {
            toggleModal('cronModal');
            fetchCronJobs();
        }

        async function fetchCronJobs() {
            const listEl = document.getElementById('cronJobList');
            listEl.innerHTML = '<div class="text-center text-xs text-gray-500 mt-5"><i class="fa-solid fa-spinner fa-spin mr-1"></i>加载中...</div>';
            
            try {
                const response = await fetch(`${apiBaseUrl}/cron/list`);
                const data = await response.json();
                if (response.ok && data.status === 'success') {
                    const jobs = data.data.jobs;
                    if (jobs.length === 0) {
                        listEl.innerHTML = '<div class="text-center text-xs text-gray-600 mt-5 italic">目前没有定时计划。</div>';
                    } else {
                        listEl.innerHTML = jobs.map(job => `
                            <div class="bg-gray-800 border border-gray-700 p-3 rounded hover:border-opsAccent transition group">
                                <div class="flex justify-between items-center mb-1">
                                    <div class="font-bold text-xs text-opsAccent truncate mr-2" title="${job.id}">
                                        <i class="fa-solid fa-server text-gray-500 mr-1"></i>${escapeHTML(job.target_host)}
                                    </div>
                                    <button onclick="deleteCronJob('${job.id}')" class="text-gray-500 hover:text-opsAlert transition"><i class="fa-solid fa-trash"></i></button>
                                </div>
                                <div class="text-[10px] text-gray-400 font-mono mb-1">ID: ${job.id}</div>
                                <div class="flex justify-between items-center text-[10px]">
                                    <span class="bg-black text-opsSuccess border border-gray-700 px-1.5 py-0.5 rounded">${escapeHTML(job.agent_profile)}</span>
                                    <span class="text-gray-500">下次执行: ${new Date(job.next_run_time).toLocaleString()}</span>
                                </div>
                            </div>
                        `).join('');
                    }
                }
            } catch(e) {
                listEl.innerHTML = `<div class="text-center text-xs text-opsAlert mt-5">加载失败: ${e.message}</div>`;
            }
        }

        async function addCronJob() {
            const expr = document.getElementById('cronExpr').value.trim();
            const host = document.getElementById('cronHost').value.trim();
            const user = document.getElementById('cronUser').value.trim();
            const pwd = document.getElementById('cronPwd').value;
            const profile = document.getElementById('cronProfile').value;
            const message = document.getElementById('cronMessage').value.trim();
            const errBox = document.getElementById('cronError');
            const btn = document.getElementById('btnSaveCron');

            if (!expr || !host || !message) {
                errBox.innerText = "请填写完整 Cron表达式、目标主机和巡检指令。";
                errBox.classList.remove('hidden');
                return;
            }

            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i>提交中...';
            btn.disabled = true;
            errBox.classList.add('hidden');

            try {
                const response = await fetch(`${apiBaseUrl}/cron/add`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        cron_expr: expr, 
                        host: host, 
                        username: user, 
                        password: pwd, 
                        agent_profile: profile, 
                        message: message 
                    })
                });
                
                const data = await response.json();
                if (response.ok && data.status === 'success') {
                    // 清空表单，除了主机等默认配置
                    document.getElementById('cronMessage').value = '';
                    fetchCronJobs(); // 刷新列表
                    alert(data.message);
                } else {
                    errBox.innerText = data.detail || data.message || "提交失败";
                    errBox.classList.remove('hidden');
                }
            } catch(e) {
                errBox.innerText = "网络异常: " + e.message;
                errBox.classList.remove('hidden');
            } finally {
                btn.innerHTML = '<i class="fa-solid fa-paper-plane mr-1"></i>提交巡检计划';
                btn.disabled = false;
            }
        }

        async function deleteCronJob(jobId) {
            if (!confirm(`确定要取消计划 ${jobId} 吗？`)) return;
            try {
                const response = await fetch(`${apiBaseUrl}/cron/${jobId}`, { method: 'DELETE' });
                if (response.ok) {
                    fetchCronJobs();
                } else {
                    alert('删除失败');
                }
            } catch(e) { alert("网络异常: " + e.message); }
        }


                function switchSession(sid) {
                    currentSessionId = sid;
                    const s = sessions[sid];
                    if (!s) return;
                    currentHost = s.host; currentRemark = s.remark; isReadWriteMode = s.isReadWriteMode;
                    
                    // Sync selected skills with the current session's actual skills
                    // skills stored per-session, no global sync needed
        
                    document.querySelectorAll('[id^="chatContainer_"]').forEach(el => el.classList.add('hidden'));
                    const activeChat = document.getElementById('chatContainer_' + sid);
            if(activeChat) activeChat.classList.remove('hidden');
            
            const _el_welcomeBox = document.getElementById('welcomeBox'); if(_el_welcomeBox) _el_welcomeBox.classList.add('hidden');
            const _el_noSessionHint = document.getElementById('noSessionHint'); if(_el_noSessionHint) _el_noSessionHint.classList.add('hidden');
            const _el2_topBadge = document.getElementById('topBadge'); if(_el2_topBadge) _el2_topBadge.classList.remove('hidden');
            const _elT_topMountedSkillsCount = document.getElementById('topMountedSkillsCount'); if(_elT_topMountedSkillsCount) _elT_topMountedSkillsCount.innerText = s.skills.length;
            
            if (s.selectedModel) {
                const modelSelect = document.getElementById('modelSelector');
                // Check if the model actually exists in the options to avoid blanking out
                let exists = false;
                for(let i=0; i<modelSelect.options.length; i++) {
                    if(modelSelect.options[i].value === s.selectedModel) exists = true;
                }
                if(exists) modelSelect.value = s.selectedModel;
            }

            updateModeUI();
            updateHeartbeatUI();
            renderSidebar();
            scrollToBottom();
        }

        function filterSessions() {
            renderSidebar();
        }

        function renderSidebar() {
            const wrapper = document.getElementById('activeSessionsWrapper');
            const searchInput = document.getElementById('sessionSearchInput');
            const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';

            let keys = Object.keys(sessions);

            if (searchTerm) {
                keys = keys.filter(sid => {
                    const s = sessions[sid];
                    const searchStr = `${s.host} ${s.remark || ''} ${s.user || ''} ${s.group_name || ''}`.toLowerCase();
                    return searchStr.includes(searchTerm);
                });
            }

            if(Object.keys(sessions).length === 0) {
                wrapper.innerHTML = '';
                const _el2_noSessionHint = document.getElementById('noSessionHint'); if(_el2_noSessionHint) _el2_noSessionHint.classList.remove('hidden');
                const _el2_welcomeBox = document.getElementById('welcomeBox'); if(_el2_welcomeBox) _el2_welcomeBox.classList.remove('hidden');
                const _el_topBadge = document.getElementById('topBadge'); if(_el_topBadge) _el_topBadge.classList.add('hidden');
                document.getElementById('topSessionName').innerHTML = '待命状态...';
                return;
            } else if (keys.length === 0 && Object.keys(sessions).length > 0) {
                 wrapper.innerHTML = '<div class="text-xs text-gray-500 text-center py-4">未找到匹配的会话</div>';
                 return;
            }

            const _el2_noSessionHint = document.getElementById('noSessionHint'); if(_el2_noSessionHint) _el2_noSessionHint.classList.add('hidden');

            // #21: Group sessions by group_name
            const groups = {};
            keys.forEach(sid => {
                const s = sessions[sid];
                const groupName = s.group_name || '未分组';
                if (!groups[groupName]) groups[groupName] = [];
                groups[groupName].push(sid);
            });

            let html = '';
            const groupNames = Object.keys(groups).sort((a, b) => a === '未分组' ? 1 : b === '未分组' ? -1 : a.localeCompare(b));

            for (const groupName of groupNames) {
                const groupSids = groups[groupName];
                const isCollapsed = collapsedGroups.has(groupName);
                const chevron = isCollapsed ? 'fa-chevron-right' : 'fa-chevron-down';

                // Only show group headers when there are multiple groups
                if (groupNames.length > 1) {
                    html += `<div class="flex items-center px-2 py-1 mt-1 cursor-pointer text-[10px] text-gray-500 hover:text-gray-300 transition select-none" onclick="toggleSidebarGroup('${escapeHTML(groupName)}')">
                        <i class="fa-solid ${chevron} mr-1.5 w-2.5 text-center text-[8px]"></i>
                        <span class="uppercase tracking-wider font-bold">${escapeHTML(groupName)}</span>
                        <span class="ml-auto bg-gray-800 text-gray-500 px-1.5 rounded text-[9px]">${groupSids.length}</span>
                    </div>`;
                }

                if (!isCollapsed) {
                    for (const sid of groupSids) {
                        const s = sessions[sid];
                        const isActive = (sid === currentSessionId);
                        const bgClass = isActive ? 'bg-gray-800 border-opsAccent shadow-[0_0_10px_rgba(137,180,250,0.2)]' : 'bg-gray-900/50 hover:bg-gray-800 border-transparent hover:border-gray-700';
                        const nameDisplay = s.remark ? `[`+s.remark+`] `+s.host : s.host;

                        let icon = 'fa-server text-opsSuccess';
                        if(s.protocol === 'virtual') icon = 'fa-box-open text-purple-400';
                        if(s.agentProfile === 'dba') icon = 'fa-database text-blue-400';
                        if(s.agentProfile === 'security') icon = 'fa-shield-halved text-opsAlert';
                        if(s.agentProfile === 'master') icon = 'fa-crown text-yellow-400';

                        const dot = isActive ? '<div class="w-1.5 h-1.5 rounded-full bg-opsAccent shadow-[0_0_6px_#89b4fa] mr-2"></div>' : '';
                        html += `
                        <div class="${bgClass} rounded px-3 py-2 flex items-center mb-1 cursor-pointer border transition group" onclick="switchSession('${sid}')">
                            <i class="fa-solid ${icon} mr-3 w-4 text-center"></i>
                            <div class="flex-1 overflow-hidden">
                                <div class="text-sm font-bold text-white truncate">${escapeHTML(nameDisplay)}</div>
                                <div class="text-[10px] text-gray-400 truncate font-mono">${escapeHTML(s.user)}@${escapeHTML(s.host)}</div>
                            </div>
                            ${dot}
                            <button class="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-opsAlert px-1.5 py-1 transition" onclick="disconnectSession('${sid}', event)"><i class="fa-solid fa-power-off"></i></button>
                        </div>`;
                    }
                }
            }

            wrapper.innerHTML = html;
        }

        function toggleSidebarGroup(groupName) {
            if (collapsedGroups.has(groupName)) {
                collapsedGroups.delete(groupName);
            } else {
                collapsedGroups.add(groupName);
            }
            renderSidebar();
        }

        async function disconnectSession(sid, event) {
            event.stopPropagation();
            if(!confirm("确定终止此连接吗？")) return;
            fetch('/api/v1/disconnect/' + sid, {method: 'DELETE'}).catch(()=>{});
            delete sessions[sid];
            const chatBox = document.getElementById('chatContainer_' + sid);
            if(chatBox) chatBox.remove();
            
            const remaining = Object.keys(sessions);
            if(remaining.length > 0) {
                if(currentSessionId === sid) switchSession(remaining[0]);
                else renderSidebar();
            } else {
                currentSessionId = null;
                renderSidebar();
            }
        }

        // ---【新功能】历史资产通讯录 (Address Book) ---
        async function loadSavedAssets() {
            const panel = document.getElementById('addressBookPanel');
            panel.classList.toggle('hidden');
            if (panel.classList.contains('hidden')) return;
            
            try {
                const response = await fetch(`${apiBaseUrl}/assets/saved`);
                const data = await response.json();
                
                if (response.ok && data.status === 'success') {
                    const assets = data.data.assets;
                    if (assets.length === 0) {
                        panel.innerHTML = '<div class="text-center text-xs text-gray-500 italic p-2">通讯录为空。成功连接过的资产会自动保存在这里。</div>';
                        return;
                    }
                    
                    panel.innerHTML = assets.map((a, index) => {
                        const icon = a.protocol === 'ssh' ? 'fa-server text-opsSuccess' : 'fa-box-open text-purple-400';
                        // 将资产数据转换为安全的 JSON 字符串供点击事件使用
                        const assetJson = btoa(unescape(encodeURIComponent(JSON.stringify(a))));

                        return `
                        <div class="flex items-center justify-between p-2 hover:bg-gray-800 rounded cursor-pointer border border-transparent hover:border-gray-700" onclick="fillFormFromAsset('${assetJson}')">
                            <div class="flex items-center space-x-3">
                                <i class="fa-solid ${icon} w-4 text-center"></i>
                                <div>
                                    <div class="text-xs font-bold text-gray-200">${escapeHTML(a.remark || '未命名资产')}</div>
                                    <div class="text-[10px] text-gray-500 font-mono">${escapeHTML(a.host)}:${a.port}</div>
                                </div>
                            </div>
                            <span class="text-[9px] bg-black border border-gray-700 px-1 py-0.5 rounded text-gray-400">${escapeHTML(a.protocol.toUpperCase())}</span>
                        </div>`;
                    }).join('');
                }
            } catch(e) {
                panel.innerHTML = `<div class="text-center text-xs text-opsAlert p-2">加载失败: ${e.message}</div>`;
            }
        }
        
        async function fillFormFromAsset(indexOrBase64) {
            try {
                let a;
                if (typeof indexOrBase64 === 'number' || /^\d+$/.test(indexOrBase64)) {
                    a = loadedAssetsList[parseInt(indexOrBase64)];
                } else {
                    // base64 encoded JSON from Address Book
                    a = JSON.parse(decodeURIComponent(escape(atob(indexOrBase64))));
                }
                if (!a) return;
                
                document.getElementById('connRemark').value = a.remark || '';
                document.getElementById('connHost').value = a.host || '';
                document.getElementById('connPort').value = a.port || '';
                document.getElementById('connUser').value = a.username || '';
                document.getElementById('connPwd').value = a.password || '';
                document.getElementById('connAgentProfile').value = a.agent_profile || 'default';
                
                let category = 'linux';
                if (a.extra_args && a.extra_args.device_type) {
                    category = a.extra_args.device_type;
                } else if (a.protocol === 'winrm') {
                    category = 'windows';
                } else if (a.protocol === 'virtual') {
                    category = 'api'; // Default fallback for old virtual
                }
                document.getElementById('connAssetCategory').value = category;
                handleAssetCategoryChange(); // Trigger UI update
                
                if(a.extra_args) {
                    if (a.extra_args.database) document.getElementById('connDbName').value = a.extra_args.database;
                    if (a.extra_args.enable_password) document.getElementById('connEnablePwd').value = a.extra_args.enable_password;
                    if (a.extra_args.auth_header) document.getElementById('connAuthHeader').value = a.extra_args.auth_header;
                    if (a.extra_args.heartbeat_prompt) document.getElementById('connHeartbeatPrompt').value = a.extra_args.heartbeat_prompt;
                    else document.getElementById('connHeartbeatPrompt').value = '';
                    
                    // Clear out these handled keys from extraArgs text area
                    const remainingArgs = { ...a.extra_args };
                    delete remainingArgs.device_type;
                    delete remainingArgs.database;
                    delete remainingArgs.enable_password;
                    delete remainingArgs.auth_header;
                    delete remainingArgs.heartbeat_prompt;
                    
                    if(Object.keys(remainingArgs).length > 0) {
                        document.getElementById('connExtraArgs').value = JSON.stringify(remainingArgs);
                    } else {
                        document.getElementById('connExtraArgs').value = '';
                    }
                } else {
                    document.getElementById('connExtraArgs').value = '';
                }
                
                // 恢复技能勾选
                currentLoadedRegistry = []; // force refresh
                await loadSkillsRegistry(new Set(a.skills || []));
                
                switchView('chatView');
                toggleModal('connModal');
                
            } catch(e) { console.error("解析资产数据失败", e); }
        }

        // --- 视图路由切换 ---
        function switchView(viewId) {
            // Update Navigation Highlighting
            document.querySelectorAll('.nav-item').forEach(el => {
                if(el.dataset.view === viewId) {
                    el.classList.add('bg-gray-800', 'text-opsAccent');
                    el.classList.remove('text-gray-400', 'text-gray-500');
                } else {
                    el.classList.remove('bg-gray-800', 'text-opsAccent');
                    el.classList.add('text-gray-400');
                }
            });

            // Update View Containers
            document.querySelectorAll('.view-container').forEach(el => {
                if (el.id === viewId) {
                    el.classList.remove('hidden');
                    if (viewId === 'chatView') el.classList.add('flex');
                    else el.classList.add('flex', 'flex-col');
                } else {
                    el.classList.add('hidden');
                    el.classList.remove('flex', 'flex-col');
                }
            });
            
            // Trigger View Specific Data Loading
            if (viewId === 'assetView') loadAssetVault();
            if (viewId === 'cronView') fetchCronJobs();
            if (viewId === 'skillsView') openSkillOverview();
        }

        // 初始化默认视图
        document.addEventListener('DOMContentLoaded', async () => {
            fetchAvailableModels();
            switchView('chatView');
            
            // Sync active sessions from backend to survive F5 refresh
            try {
                const res = await fetch(`${apiBaseUrl}/sessions/active`);
                const sessionData = await res.json();
                if (res.ok && sessionData.status === 'success') {
                    sessions = sessionData.data.sessions;
                    for (const sid in sessions) {
                        // Hydrate the stored per-host model selection
                        const savedHostModel = localStorage.getItem('opscore_model_' + sessions[sid].host);
                        if(savedHostModel) {
                            sessions[sid].selectedModel = savedHostModel;
                        } else {
                            sessions[sid].selectedModel = localStorage.getItem('opscore_default_model') || 'gemini-3.1-pro-preview';
                        }
                        
                        const chatHtml = `<div id="chatContainer_${sid}" class="absolute inset-0 overflow-y-auto p-6 space-y-6 hidden"></div>`;
                        document.getElementById('mainChatWrapper').insertAdjacentHTML('beforeend', chatHtml);
                        addSystemMessageTo(sid, `🔄 [会话恢复] 已成功从后台恢复该会话 (SID: ${sid})。`);
                        
                        // Fetch history for this session
                        try {
                            const histRes = await fetch(`${apiBaseUrl}/session/${sid}/history`);
                            const histData = await histRes.json();
                            if (histRes.ok && histData.status === 'success' && histData.data.messages) {
                                histData.data.messages.forEach(msg => {
                                    if (msg.role === 'user' && msg.content) {
                                        renderHistoricalUserBubble(sid, msg.content, msg.timestamp);
                                    } else if (msg.role === 'assistant' && msg.content) {
                                        renderHistoricalAIBubble(sid, msg.content, msg.timestamp);
                                    }
                                });
                            }
                        } catch (e) { console.error("获取历史记录失败", e); }
                    }
                    const sids = Object.keys(sessions);
                    if (sids.length > 0) {
                        switchSession(sids[0]);
                    } else {
                        renderSidebar();
                    }
                }
            } catch (e) { console.error("同步会话失败", e); }
            
            // 恢复缓存的连接表单状态
            const cached = localStorage.getItem('opscore_conn_cache');
            if (cached) {
                try {
                    const data = JSON.parse(cached);
                    if(data.remark) document.getElementById('connRemark').value = data.remark;
                    if(data.host) document.getElementById('connHost').value = data.host;
                    if(data.port) document.getElementById('connPort').value = data.port;
                    if(data.user) document.getElementById('connUser').value = data.user;
                    if(data.pwd) document.getElementById('connPwd').value = data.pwd;
                    if(data.allowMod !== undefined) document.getElementById('connAllowMod').checked = data.allowMod;
                    if(data.agentProfile) document.getElementById('connAgentProfile').value = data.agentProfile;
                    
                    if(data.category) {
                        document.getElementById('connAssetCategory').value = data.category;
                    } else if (data.protocol === 'virtual') {
                        document.getElementById('connAssetCategory').value = 'api';
                    }
                    handleAssetCategoryChange();
                    
                    if(data.extraArgs) {
                        if(data.extraArgs.database) document.getElementById('connDbName').value = data.extraArgs.database;
                        if(data.extraArgs.enable_password) document.getElementById('connEnablePwd').value = data.extraArgs.enable_password;
                        if(data.extraArgs.auth_header) document.getElementById('connAuthHeader').value = data.extraArgs.auth_header;
                        if(data.extraArgs.heartbeat_prompt) document.getElementById('connHeartbeatPrompt').value = data.extraArgs.heartbeat_prompt;
                        
                        const remaining = { ...data.extraArgs };
                        delete remaining.device_type; delete remaining.database; delete remaining.enable_password; delete remaining.auth_header; delete remaining.heartbeat_prompt;
                        if(Object.keys(remaining).length > 0) {
                            document.getElementById('connExtraArgs').value = JSON.stringify(remaining);
                        }
                    }
                    
                    if(data.skills && Array.isArray(data.skills)) {
                        currentLoadedRegistry = [];
                        await loadSkillsRegistry(new Set(data.skills));
                    }
                } catch(e) {}
            }
        });

        // --- 重新：资产金库加载 (渲染为大型卡片网格) ---
        async function deleteAsset(assetId, event) {
            event.stopPropagation();
            if(!confirm("确定要从金库中删除这个资产吗？")) return;
            try {
                const response = await fetch(`${apiBaseUrl}/assets/${assetId}`, { method: 'DELETE' });
                const data = await response.json();
                if(response.ok && data.status === 'success') {
                    loadAssetVault();
                } else {
                    alert("删除失败: " + data.message);
                }
            } catch(e) { alert("网络异常"); }
        }

        async function loadAssetVault() {
            const grid = document.getElementById('assetGrid');
            grid.innerHTML = '<div class="text-gray-500 italic p-4 col-span-full"><i class="fa-solid fa-spinner fa-spin mr-2"></i>正在加载资产网关...</div>';
            
            try {
                const response = await fetch(`${apiBaseUrl}/assets/saved`);
                const data = await response.json();
                
                if (response.ok && data.status === 'success') {
                    const assets = data.data.assets;
                    loadedAssetsList = assets; // Save to global
                    const _elT_statTotalAssets = document.getElementById('statTotalAssets'); if(_elT_statTotalAssets) _elT_statTotalAssets.innerText = assets.length;
                    
                    if (assets.length === 0) {
                        grid.innerHTML = '<div class="text-gray-500 italic p-4 col-span-full">金库为空。请点击右上角「纳管新资产」。</div>';
                        return;
                    }
                    
                    grid.innerHTML = assets.map((a, index) => {
                        let icon = 'fa-server text-opsSuccess';
                        let protoBadge = 'SSH 直连';
                        if(a.protocol === 'virtual') {
                            icon = 'fa-box-open text-purple-400';
                            protoBadge = '虚拟凭证';
                        }
                        if(a.agent_profile === 'dba') icon = 'fa-database text-blue-400';
                        if(a.agent_profile === 'security') icon = 'fa-shield-halved text-opsAlert';
                        
                        
                        
                        return `
                        <div class="bg-opsPanel border border-gray-800 rounded-xl p-5 hover:border-opsAccent transition group shadow-lg flex flex-col relative">
                            <div class="flex justify-between items-start mb-3">
                                <div class="font-bold text-lg text-white group-hover:text-opsAccent transition truncate pr-2">
                                    <i class="fa-solid ${icon} mr-2"></i>${escapeHTML(a.remark || '未命名资产')}
                                </div>
                                <span class="bg-gray-800 text-gray-400 border border-gray-700 px-2 py-0.5 rounded text-[10px] font-bold whitespace-nowrap">${protoBadge}</span>
                            </div>
                            
                            <div class="text-xs text-gray-400 mb-2 font-mono flex items-center">
                                <i class="fa-solid fa-network-wired w-4 text-center mr-1 opacity-50"></i> ${escapeHTML(a.host)}:${a.port}
                            </div>
                            <div class="text-xs text-gray-400 mb-4 font-mono flex items-center">
                                <i class="fa-solid fa-user w-4 text-center mr-1 opacity-50"></i> ${escapeHTML(a.username || '--')}
                            </div>
                            
                            <div class="mt-auto flex justify-between items-center border-t border-gray-800 pt-3">
                                <div class="text-[10px] text-gray-500">
                                    <i class="fa-solid fa-puzzle-piece mr-1"></i>${(a.skills || []).length} Skills
                                </div>
                                <div class="flex space-x-2">
                                    <button onclick="deleteAsset(${a.id}, event)" class="text-xs bg-red-900/30 text-opsAlert font-bold px-2 py-1.5 rounded hover:bg-red-900 transition" title="删除">
                                        <i class="fa-solid fa-trash"></i>
                                    </button>
                                    <button onclick="fillFormFromAsset(${index})" class="text-xs bg-opsAccent text-opsDark font-bold px-3 py-1.5 rounded hover:bg-white transition">
                                        <i class="fa-solid fa-bolt mr-1"></i>唤醒连线/编辑
                                    </button>
                                </div>
                            </div>
                        </div>`;
                    }).join('');
                }
            } catch(e) {
                grid.innerHTML = `<div class="text-opsAlert p-4 col-span-full">加载失败: ${e.message}</div>`;
            }
        }
        
        // 覆盖原有的打开大看板逻辑，将它渲染到主内容区
        async function openSkillOverview() {
            const container = document.getElementById('skillOverviewContent');
            if(!container) return; // 如果在其他视图被调用
            const registry = await fetchSkills();
            
            if (!registry) {
                container.innerHTML = `<div class="text-opsAlert text-center mt-10">获取数据失败。后端离线。</div>`;
                return;
            }

            container.innerHTML = `<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">` + registry.map(skill => `
                <div class="bg-opsPanel border border-gray-800 rounded-xl p-5 hover:border-opsAccent transition group shadow-lg flex flex-col relative">
                    <div class="flex justify-between items-start mb-3">
                        <div class="font-bold text-lg text-white group-hover:text-opsAccent transition truncate">
                            <i class="fa-solid fa-microchip mr-2 text-gray-500 group-hover:text-opsAccent"></i>${escapeHTML(skill.name)}
                        </div>
                        <div class="flex flex-col items-end space-y-1">
                            <span class="bg-gray-800 text-gray-400 border border-gray-700 px-2 py-0.5 rounded text-[9px] font-mono whitespace-nowrap">${escapeHTML(skill.source_type || 'Unknown')}</span>
                            <span class="bg-opsSuccess/20 text-opsSuccess border border-opsSuccess/30 px-2 py-0.5 rounded text-xs font-bold whitespace-nowrap">${skill.tool_count} 指令</span>
                        </div>
                    </div>
                    
                    <div class="text-[10px] text-gray-500 mb-4 font-mono bg-black/50 p-1.5 rounded border border-gray-800 truncate" title="${escapeHTML(skill.source_path)}">
                        <i class="fa-regular fa-folder-open mr-1.5 text-opsAccent"></i>${escapeHTML(skill.source_path)}
                    </div>

                    <div class="text-sm text-gray-400 mb-6 flex-1 line-clamp-3">${escapeHTML(skill.description)}</div>
                    
                    <div class="mt-auto pt-4 border-t border-gray-800">
                        <div class="flex justify-between items-center mb-3">
                            <button onclick="readFullSkillMd('${escapeHTML(skill.id)}')" class="text-xs text-opsAccent hover:text-white transition flex items-center">
                                <i class="fa-brands fa-readme mr-1"></i>阅读文档
                            </button>
                            ${skill.is_market ? `
                            <button onclick="migrateSkill('${escapeHTML(skill.source_path).replace(/\\/g, '/')}', '${escapeHTML(skill.id)}')" class="text-xs bg-opsAccent/20 text-opsAccent hover:bg-opsAccent hover:text-black px-3 py-1 rounded transition flex items-center">
                                <i class="fa-solid fa-cloud-arrow-down mr-1"></i>复制到我的私有库
                            </button>
                            ` : `
                            <span class="text-[10px] text-opsSuccess"><i class="fa-solid fa-check-circle mr-1"></i>已就绪</span>
                            `}
                        </div>
                        <div class="flex flex-wrap gap-1.5">
                            ${skill.tools.slice(0, 3).map(t => `
                                <div class="bg-black/50 border border-gray-700 rounded px-2 py-1 flex items-center">
                                    <i class="fa-solid fa-bolt text-blue-400/70 mr-1.5 text-[10px]"></i>
                                    <span class="font-mono text-gray-300 text-[10px] truncate max-w-[120px]">${escapeHTML(t)}</span>
                                </div>
                            `).join('')}
                            ${skill.tools.length > 3 ? `<div class="text-[10px] text-gray-500 mt-1">+${skill.tools.length - 3} 更多</div>` : ''}
                        </div>
                    </div>
                </div>
            `).join('') + `</div>`;
        }

        // --- 测试连通性 ---
        async function testConnection() {
            const el = document.getElementById('connGroupName');
            const groupName = (el ? el.value.trim() : '') || '未分组';
            const remark = document.getElementById('connRemark').value.trim();
            const host = document.getElementById('connHost').value.trim();
            const portStr = document.getElementById('connPort').value;
            const port = portStr ? parseInt(portStr) : (document.getElementById('connAssetCategory').value === 'api' ? 443 : 22);
            const user = document.getElementById('connUser').value.trim();
            const pwd = document.getElementById('connPwd').value;
            const allowMod = document.getElementById('connAllowMod').checked;
            
            const category = document.getElementById('connAssetCategory').value;
            let protocol = 'virtual';
            if (category === 'linux') protocol = 'ssh';
            if (category === 'windows') protocol = 'winrm';
            
            let extraArgs = { device_type: category };
            if (category === 'database') extraArgs.database = document.getElementById('connDbName').value.trim();
            if (category === 'network') extraArgs.enable_password = document.getElementById('connEnablePwd').value;
            if (category === 'api') extraArgs.auth_header = document.getElementById('connAuthHeader').value.trim();

            const customHb = document.getElementById('connHeartbeatPrompt').value.trim();
            if (customHb) extraArgs.heartbeat_prompt = customHb;

            const extraArgsStr = document.getElementById('connExtraArgs').value.trim();
            if(extraArgsStr) {
                try { 
                    const parsed = JSON.parse(extraArgsStr); 
                    extraArgs = { ...extraArgs, ...parsed };
                }
                catch(e) { alert('Invalid JSON in extra arguments'); return; }
            }
            
            const agentProfile = document.getElementById('connAgentProfile').value;
            const checkedSkills = Array.from(document.querySelectorAll('#skillsCheckboxList input:checked')).map(el => el.value);

            const btn = document.getElementById('testConnBtn');
            const errBox = document.getElementById('connError');

            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> 测试中...';
            btn.disabled = true;
            errBox.classList.add('hidden');

            try {
                const response = await fetch(`${apiBaseUrl}/connect/test`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ host: host, port: port, username: user, password: pwd, allow_modifications: allowMod, active_skills: checkedSkills, agent_profile: agentProfile, remark: remark, protocol: protocol, extra_args: extraArgs, group_name: groupName })
                });
                
                const data = await response.json();
                
                if(response.ok && data.status === 'success') {
                    errBox.innerHTML = `<span class="text-opsSuccess">${data.message}</span>`;
                    errBox.classList.remove('hidden', 'text-opsAlert');
                } else {
                    errBox.innerHTML = `<span class="text-opsAlert">${data.message || data.detail || '测试失败'}</span>`;
                    errBox.classList.remove('hidden');
                }
            } catch(e) {
                errBox.innerHTML = `<span class="text-opsAlert">网络异常: ${e.message}</span>`;
                errBox.classList.remove('hidden');
            } finally {
                btn.innerHTML = '<i class="fa-solid fa-stethoscope mr-1"></i>连通性测试';
                btn.disabled = false;
            }
        }


async function clearChatHistory() {
    if (!currentSessionId) {
        alert("请先选择一个活跃会话！");
        return;
    }
    if (!confirm("确定要清空当前会话的历史记录吗？此操作不可恢复。")) {
        return;
    }
    try {
        const response = await fetch(`${apiBaseUrl}/session/${currentSessionId}/history`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (response.ok && data.status === 'success') {
            const chatBox = document.getElementById(`chatContainer_${currentSessionId}`);
            if (chatBox) {
                chatBox.innerHTML = '';
            }
            alert("历史记录已清空");
        } else {
            alert("清空失败: " + data.message);
        }
    } catch (e) {
        alert("网络异常: " + e.message);
    }
}

async function exportChatHistory() {
    if (!currentSessionId) {
        alert("请先选择一个活跃会话！");
        return;
    }
    try {
        const response = await fetch(`${apiBaseUrl}/session/${currentSessionId}/history`);
        const data = await response.json();
        if (response.ok && data.status === 'success') {
            const messages = data.data.messages;
            if (messages.length === 0) {
                alert("当前会话没有可导出的历史记录。");
                return;
            }
            let exportContent = `# Chat History for Session: ${currentRemark || currentHost || currentSessionId}

`;
            messages.forEach(msg => {
                const role = msg.role === 'user' ? 'User' : 'AI Assistant';
                exportContent += `## ${role}
${msg.content}

---

`;
            });
            
            const blob = new Blob([exportContent], { type: 'text/markdown;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `chat_history_${currentSessionId}.md`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } else {
            alert("导出失败: " + data.message);
        }
    } catch (e) {
        alert("网络异常: " + e.message);
    }
}

window.submitApproval = async function(toolCallId, isApproved, uniqueId) {
    const autoApprove = document.getElementById(`auto_approve_${toolCallId}`)?.checked || false;
    const btns = document.getElementById(`approval_btns_${uniqueId}`);
    if (btns) btns.innerHTML = `<span class="text-${isApproved ? 'green' : 'red'}-400">已${isApproved ? '允许' : '拒绝'}...</span>`;
    try {
        const response = await fetch(`${apiBaseUrl}/session/${currentSessionId}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool_call_id: toolCallId, approved: isApproved, auto_approve_all: autoApprove })
        });
        if (!response.ok) {
            console.error('Approval failed');
            if (btns) btns.innerHTML = `<span class="text-red-400">提交失败</span>`;
        }
    } catch (e) {
        console.error(e);
        if (btns) btns.innerHTML = `<span class="text-red-400">提交异常</span>`;
    }
}
