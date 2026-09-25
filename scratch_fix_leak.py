import re
import sys

def patch_index_html():
    filepath = "d:\\Project\\Slide to Video\\Mã Nguồn Sudo\\index.html"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Fix 1: CloudDB.save array reference
    content = content.replace(
        "chatHistory: (typeof clsgChatSessionHistory !== 'undefined') ? clsgChatSessionHistory : (project.chatHistory || []),",
        "chatHistory: (typeof clsgChatSessionHistory !== 'undefined') ? [...clsgChatSessionHistory] : (project.chatHistory ? [...project.chatHistory] : []),"
    )

    # Fix 2: autoSaveWorkspaceState array reference
    content = content.replace(
        "activeProject.chatHistory = clsgChatSessionHistory;",
        "activeProject.chatHistory = [...clsgChatSessionHistory];"
    )

    # Fix 3: sendChatMessage async race condition
    if "async function sendChatMessage(text) {" in content:
        content = content.replace(
            "async function sendChatMessage(text) {",
            "async function sendChatMessage(text) {\n      const originalProjectId = currentProjectId;"
        )

        # Before every clsgChatSessionHistory.push in sendChatMessage, check if originalProjectId === currentProjectId
        # There are multiple places.
        # Inside the Q&A cache check:
        # clsgChatSessionHistory.push({ role: 'user', content: msg });
        # clsgChatSessionHistory.push({ role: 'assistant', content: cachedAnswer });
        # saveChatState();
        content = content.replace(
            """        clsgChatSessionHistory.push({ role: 'user', content: msg });
        clsgChatSessionHistory.push({ role: 'assistant', content: cachedAnswer });
        saveChatState();""",
            """        if (currentProjectId === originalProjectId) {
          clsgChatSessionHistory.push({ role: 'user', content: msg });
          clsgChatSessionHistory.push({ role: 'assistant', content: cachedAnswer });
          saveChatState();
        }"""
        )

        # Inside LLM reply:
        content = content.replace(
            """          clsgChatSessionHistory.push({ role: 'user', content: msg });
          clsgChatSessionHistory.push({ role: 'assistant', content: cleanReply });
          saveChatState();""",
            """          if (currentProjectId === originalProjectId) {
            clsgChatSessionHistory.push({ role: 'user', content: msg });
            clsgChatSessionHistory.push({ role: 'assistant', content: cleanReply });
            saveChatState();
          }"""
        )
        
        # Inside fallback reply:
        content = content.replace(
            """          clsgChatSessionHistory.push({ role: 'user', content: msg });
          clsgChatSessionHistory.push({ role: 'assistant', content: localReply });
          saveChatState();""",
            """          if (currentProjectId === originalProjectId) {
            clsgChatSessionHistory.push({ role: 'user', content: msg });
            clsgChatSessionHistory.push({ role: 'assistant', content: localReply });
            saveChatState();
          }"""
        )
        
        # Inside error fallback reply:
        content = content.replace(
            """          clsgChatSessionHistory.push({ role: 'user', content: msg });
          clsgChatSessionHistory.push({ role: 'assistant', content: bubbleEl?.innerHTML || 'Gặp sự cố' });
          saveChatState();""",
            """          if (currentProjectId === originalProjectId) {
            clsgChatSessionHistory.push({ role: 'user', content: msg });
            clsgChatSessionHistory.push({ role: 'assistant', content: bubbleEl?.innerHTML || 'Gặp sự cố' });
            saveChatState();
          }"""
        )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print("Patched index.html successfully.")

patch_index_html()
