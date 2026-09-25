import re

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

# Patch 1: sendChatMessage
old_payload_chat = """        const payload = {
            projectId: currentProjectId,
            query: msg,
            history: rollingHistory,
            treeSkeleton: treeSkeleton
        };"""
new_payload_chat = """        const cfg = getLLMConfig();
        const payload = {
            projectId: currentProjectId,
            query: msg,
            history: rollingHistory,
            treeSkeleton: treeSkeleton,
            apiKey: cfg.apiKey
        };"""

if old_payload_chat in content:
    content = content.replace(old_payload_chat, new_payload_chat)
    print("Patched sendChatMessage")
else:
    print("Could not find old_payload_chat")

# Patch 2: triggerRagIngestion
old_payload_ingest = """        const res = await fetch(serverUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            projectId: currentProjectId,
            chunks: chunks
          })
        });"""
new_payload_ingest = """        const cfg = getLLMConfig();
        const res = await fetch(serverUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            projectId: currentProjectId,
            chunks: chunks,
            apiKey: cfg.apiKey
          })
        });"""

if old_payload_ingest in content:
    content = content.replace(old_payload_ingest, new_payload_ingest)
    print("Patched triggerRagIngestion")
else:
    print("Could not find old_payload_ingest")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)
