import re

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

bad_str = """          const cardEl = document.getElementById(`node-${node.key}
          } else {
            let savedParams = JSON.parse(localStorage.getItem(`clsg_node_params_${originalProjectId}`) || '{}');
            if (!savedParams[node.key]) savedParams[node.key] = {};
            if (res.summary) savedParams[node.key].summary = res.summary;
            if (res.mechanism) savedParams[node.key].mechanism = res.mechanism;
            if (res.key_point) savedParams[node.key].key_point = res.key_point;
            if (res.details) savedParams[node.key].details = res.details;
            if (res.examples) savedParams[node.key].examples = res.examples;
            localStorage.setItem(`clsg_node_params_${originalProjectId}`, JSON.stringify(savedParams));
            
            const userProjects = JSON.parse(localStorage.getItem('clsg_user_projects') || '{}');
            if (userProjects[originalProjectId]) {
                userProjects[originalProjectId].nodeCustomParams = savedParams;
                localStorage.setItem('clsg_user_projects', JSON.stringify(userProjects));
            }
          }
        }`);"""

good_str = """          const cardEl = document.getElementById(`node-${node.key}`);
          } else {
            let savedParams = JSON.parse(localStorage.getItem(`clsg_node_params_${originalProjectId}`) || '{}');
            if (!savedParams[node.key]) savedParams[node.key] = {};
            if (res.summary) savedParams[node.key].summary = res.summary;
            if (res.mechanism) savedParams[node.key].mechanism = res.mechanism;
            if (res.key_point) savedParams[node.key].key_point = res.key_point;
            if (res.details) savedParams[node.key].details = res.details;
            if (res.examples) savedParams[node.key].examples = res.examples;
            localStorage.setItem(`clsg_node_params_${originalProjectId}`, JSON.stringify(savedParams));
            
            const userProjects = JSON.parse(localStorage.getItem('clsg_user_projects') || '{}');
            if (userProjects[originalProjectId]) {
                userProjects[originalProjectId].nodeCustomParams = savedParams;
                localStorage.setItem('clsg_user_projects', JSON.stringify(userProjects));
            }
          }
"""

content = content.replace(bad_str, good_str)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Syntax fixed")
