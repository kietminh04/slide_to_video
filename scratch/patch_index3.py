import re

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update sendChatMessage to handle background project update
# There are 3 places in sendChatMessage where we do:
#          if (currentProjectId === originalProjectId) {
#            clsgChatSessionHistory.push({ role: 'user', content: msg });
#            clsgChatSessionHistory.push({ role: 'assistant', content: cleanReply });
#            saveChatState();
#          }
# We will replace this pattern to include an `else` branch.

pattern_chat = r"(if\s*\(\s*currentProjectId\s*===\s*originalProjectId\s*\)\s*\{\s*clsgChatSessionHistory\.push\(\{\s*role:\s*'user',\s*content:\s*msg\s*\}\);\s*clsgChatSessionHistory\.push\(\{\s*role:\s*'assistant',\s*content:\s*([a-zA-Z0-9_\?\.]+)\s*\}\);\s*saveChatState\(\);\s*\})"

def chat_repl(match):
    full_match = match.group(1)
    var_name = match.group(2)
    new_code = full_match + f""" else {{
            let savedHistory = JSON.parse(localStorage.getItem('clsg_chat_history_' + originalProjectId) || '[]');
            savedHistory.push({{ role: 'user', content: msg }});
            savedHistory.push({{ role: 'assistant', content: {var_name} }});
            localStorage.setItem('clsg_chat_history_' + originalProjectId, JSON.stringify(savedHistory));
            localStorage.setItem('clsg_chat_html_' + originalProjectId, '');
            const userProjects = JSON.parse(localStorage.getItem('clsg_user_projects') || '{{}}');
            if (userProjects[originalProjectId]) {{
              userProjects[originalProjectId].chatHistory = savedHistory;
              userProjects[originalProjectId].chatHtml = '';
              localStorage.setItem('clsg_user_projects', JSON.stringify(userProjects));
            }}
          }}"""
    return new_code

content = re.sub(pattern_chat, chat_repl, content)


# 2. Update triggerManualDeepSummarize
if "window.triggerManualDeepSummarize = async function () {" in content:
    content = content.replace(
        "window.triggerManualDeepSummarize = async function () {",
        "window.triggerManualDeepSummarize = async function () {\n      const originalProjectId = currentProjectId;"
    )

pattern_summary = r"(if\s*\(\s*res\s*&&\s*\(\s*res\.summary\s*\|\|\s*res\.mechanism\s*\)\s*\)\s*\{)([\s\S]*?)(showToast\('✨ Đã bóc tách chi tiết thành công!'\);\s*// Tự động chuyển sang chế độ chi tiết[\s\S]*?\})"

def summary_repl(match):
    before = match.group(1)
    inside = match.group(2)
    after = match.group(3)
    
    # We wrap the UI update in `if (currentProjectId === originalProjectId)`
    new_code = f"""if (res && (res.summary || res.mechanism)) {{
          if (currentProjectId === originalProjectId) {{
            {inside.strip()}
            {after.strip()}
          }} else {{
            let savedParams = JSON.parse(localStorage.getItem(`clsg_node_params_${{originalProjectId}}`) || '{{}}');
            if (!savedParams[node.key]) savedParams[node.key] = {{}};
            if (res.summary) savedParams[node.key].summary = res.summary;
            if (res.mechanism) savedParams[node.key].mechanism = res.mechanism;
            if (res.key_point) savedParams[node.key].key_point = res.key_point;
            if (res.details) savedParams[node.key].details = res.details;
            if (res.examples) savedParams[node.key].examples = res.examples;
            localStorage.setItem(`clsg_node_params_${{originalProjectId}}`, JSON.stringify(savedParams));
            
            const userProjects = JSON.parse(localStorage.getItem('clsg_user_projects') || '{{}}');
            if (userProjects[originalProjectId]) {{
                userProjects[originalProjectId].nodeCustomParams = savedParams;
                localStorage.setItem('clsg_user_projects', JSON.stringify(userProjects));
            }}
          }}
        }}"""
    return new_code

content = re.sub(pattern_summary, summary_repl, content)

# 3. FIX THE UI LEAK!
# If savedHistory is empty, it skips `chatContainer.innerHTML = '';` in loadProjectIntoWorkspace!
ui_leak_pattern = r"(if\s*\(\s*savedHistory\s*&&\s*savedHistory\.length\s*>\s*0\s*\)\s*\{)([\s\S]*?)(chatContainer\.innerHTML\s*=\s*savedHTML;\s*\}\s*else\s*\{)([\s\S]*?)(savedHistory\.forEach\([\s\S]*?\}\);?\s*\})"

def ui_leak_repl(match):
    # We just need to ensure chatContainer.innerHTML is cleared unconditionally at the very start of the try block.
    # Actually, it's already cleared at line 10938!
    # Let's just remove the empty else block. Wait, the `else` block is inside `if (savedHistory && savedHistory.length > 0)`.
    # Let's change the logic to ALWAYS restore chat, or clear it.
    pass

# A better way: replace the whole block in loadProjectIntoWorkspace
restore_chat_regex = r"(// \[FIX\] Khôi phục Chat Session theo từng dự án từ LocalStorage hoặc Cloud Database[\s\S]*?if\s*\(chatContainer\)\s*\{\s*try\s*\{)([\s\S]*?)(catch\s*\(e\)\s*\{\s*console\.warn\(\"\[LoadProject\] Lỗi khôi phục Chat:\",\s*e\);\s*\}\s*\})"

def restore_chat_repl(match):
    start = match.group(1)
    end = match.group(3)
    
    # We write a completely new, clean restore logic
    middle = """
          let savedHistory = JSON.parse(localStorage.getItem('clsg_chat_history_' + projId) || '[]');
          let savedHTML = localStorage.getItem('clsg_chat_html_' + projId) || '';

          if ((!savedHistory || savedHistory.length === 0) && activeProject && activeProject.chatHistory && activeProject.chatHistory.length > 0) {
            savedHistory = activeProject.chatHistory;
            localStorage.setItem('clsg_chat_history_' + projId, JSON.stringify(savedHistory));
          }
          if ((!savedHTML || savedHTML.trim().length === 0) && activeProject && activeProject.chatHtml) {
            savedHTML = activeProject.chatHtml;
            localStorage.setItem('clsg_chat_html_' + projId, savedHTML);
          }

          // [CRITICAL FIX] MUST CLEAR UI FIRST BEFORE RE-POPUPLATING!
          chatContainer.innerHTML = '';
          
          if (savedHistory && savedHistory.length > 0) {
            clsgChatSessionHistory.push(...savedHistory);
            if (savedHTML && savedHTML.trim().length > 0) {
              chatContainer.innerHTML = savedHTML;
            } else {
              savedHistory.forEach(m => {
                const isUser = m.role === 'user';
                const el = document.createElement('div');
                el.className = `chat-msg ${isUser ? 'msg-user' : 'msg-ai'}`;
                el.innerHTML = `
                  <div class="msg-avatar">${isUser ? '👤' : '🤖'}</div>
                  <div class="msg-bubble">${isUser ? escapeHtml(m.content) : m.content}</div>
                `;
                chatContainer.appendChild(el);
              });
            }
            chatContainer.scrollTop = chatContainer.scrollHeight;
          }
        } """
    return start + middle + end

content = re.sub(restore_chat_regex, restore_chat_repl, content)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched successfully!")
