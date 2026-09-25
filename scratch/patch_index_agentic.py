with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

# Part 1: Add new function definitions
old_methods = """      keepOnlyTarget(act) {
        if (!act.chapter) return false;"""

new_methods = """      setNodeConfig(act) {
        const nodes = this.findNodesByCode(act.code);
        if (nodes.length > 0) {
          const target = nodes[0];
          let updated = false;
          if (act.voice !== undefined) { setNodeParam(target.key, 'voice', act.voice); updated = true; }
          if (act.speed !== undefined) { setNodeParam(target.key, 'speed', act.speed); updated = true; }
          if (act.locked !== undefined) { setNodeParam(target.key, 'locked', act.locked); updated = true; }
          if (updated) renderMindmap();
          return updated;
        }
        return false;
      },
      setNarration(act) {
        const nodes = this.findNodesByCode(act.code);
        if (nodes.length > 0) {
          const target = nodes[0];
          setNodeParam(target.key, 'narration', act.narration);
          renderMindmap();
          return true;
        }
        return false;
      },
      requestIllustration(act) {
        const nodes = this.findNodesByCode(act.code);
        if (nodes.length > 0) {
          const target = nodes[0];
          setNodeParam(target.key, 'visual_prompt', act.prompt);
          renderMindmap();
          return true;
        }
        return false;
      },

      keepOnlyTarget(act) {
        if (!act.chapter) return false;"""

if old_methods in content:
    content = content.replace(old_methods, new_methods)
    print("Injected new methods")
else:
    print("Could not find old_methods")

# Part 2: Add into executeBatch
old_exec = """          else if (type === 'keep_only_target') didSomething = this.keepOnlyTarget(act) || didSomething;
          else if (type === 'speak_narration') didSomething = this.speakNarration(act.text || act.narration) || didSomething;
        });"""

new_exec = """          else if (type === 'keep_only_target') didSomething = this.keepOnlyTarget(act) || didSomething;
          else if (type === 'speak_narration') didSomething = this.speakNarration(act.text || act.narration) || didSomething;
          else if (type === 'set_node_config') didSomething = this.setNodeConfig(act) || didSomething;
          else if (type === 'set_narration') didSomething = this.setNarration(act) || didSomething;
          else if (type === 'request_illustration') didSomething = this.requestIllustration(act) || didSomething;
        });"""

if old_exec in content:
    content = content.replace(old_exec, new_exec)
    print("Injected into executeBatch")
else:
    print("Could not find old_exec")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)
