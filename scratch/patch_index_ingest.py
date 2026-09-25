import re

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

old_ingest = """        const response = await fetch('/api/rag_ingest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            projectId: currentProjectId, 
            chunks: chunks 
          })
        });"""

new_ingest = """        const cfg = getLLMConfig();
        const response = await fetch('/api/rag_ingest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            projectId: currentProjectId, 
            chunks: chunks,
            apiKey: cfg.apiKey
          })
        });"""

if old_ingest in content:
    content = content.replace(old_ingest, new_ingest)
    print("Patched triggerRagIngestion")
else:
    print("Could not find old_ingest")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)
