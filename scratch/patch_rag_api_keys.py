import os

def patch_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    old_key = "const apiKey = process.env.OPENAI_API_KEY || process.env.CLSG_OPENAI_API_KEY;"
    new_key = "const apiKey = (req.body && req.body.apiKey) || process.env.OPENAI_API_KEY || process.env.CLSG_OPENAI_API_KEY;"

    if old_key in content:
        content = content.replace(old_key, new_key)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Patched {filepath}")
    else:
        print(f"Could not find old_key in {filepath}")

patch_file("api/rag_chat.js")
patch_file("api/rag_ingest.js")
