import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('typeof getNodeParam === \\\'function\\\'', 'typeof getNodeParam === \'function\'')
text = text.replace('getNodeParam(itKey, \\\'summary\\\',', 'getNodeParam(itKey, \'summary\',')
text = text.replace('getNodeParam(itKey, \\\'mechanism\\\',', 'getNodeParam(itKey, \'mechanism\',')
text = text.replace('getNodeParam(itKey, \\\'key_point\\\',', 'getNodeParam(itKey, \'key_point\',')
text = text.replace('getNodeParam(itKey, \\\'details\\\',', 'getNodeParam(itKey, \'details\',')
text = text.replace('getNodeParam(itKey, \\\'narration\\\',', 'getNodeParam(itKey, \'narration\',')

text = text.replace('getNodeParam(node.key, \\\'summary\\\',', 'getNodeParam(node.key, \'summary\',')
text = text.replace('getNodeParam(node.key, \\\'mechanism\\\',', 'getNodeParam(node.key, \'mechanism\',')
text = text.replace('getNodeParam(node.key, \\\'key_point\\\',', 'getNodeParam(node.key, \'key_point\',')
text = text.replace('getNodeParam(node.key, \\\'details\\\',', 'getNodeParam(node.key, \'details\',')
text = text.replace('getNodeParam(node.key, \\\'narration\\\',', 'getNodeParam(node.key, \'narration\',')

text = text.replace('getNodeParam(chNode.key, \\\'narration\\\',', 'getNodeParam(chNode.key, \'narration\',')
text = text.replace('getNodeParam(itNode.key, \\\'summary\\\',', 'getNodeParam(itNode.key, \'summary\',')
text = text.replace('getNodeParam(itNode.key, \\\'mechanism\\\',', 'getNodeParam(itNode.key, \'mechanism\',')
text = text.replace('getNodeParam(itNode.key, \\\'key_point\\\',', 'getNodeParam(itNode.key, \'key_point\',')
text = text.replace('getNodeParam(itNode.key, \\\'narration\\\',', 'getNodeParam(itNode.key, \'narration\',')

text = text.replace('|| \\\'\\\')', '|| \'\')')
text = text.replace(': (it.summary || \\\'\\\')', ': (it.summary || \'\')')
text = text.replace(': (it.mechanism || \\\'\\\')', ': (it.mechanism || \'\')')
text = text.replace(': (it.key_point || \\\'\\\')', ': (it.key_point || \'\')')
text = text.replace(': (it.details || \\\'\\\')', ': (it.details || \'\')')
text = text.replace(': (it.narration || \\\'\\\')', ': (it.narration || \'\')')

text = text.replace(': (node.data?.summary || \\\'\\\')', ': (node.data?.summary || \'\')')
text = text.replace(': (node.data?.mechanism || \\\'\\\')', ': (node.data?.mechanism || \'\')')
text = text.replace(': (node.data?.key_point || \\\'\\\')', ': (node.data?.key_point || \'\')')
text = text.replace(': (node.data?.details || \\\'\\\')', ': (node.data?.details || \'\')')
text = text.replace(': (node.data?.narration || \\\'\\\')', ': (node.data?.narration || \'\')')

text = text.replace(': (currentScenes[cIdx]?.narration || \\\'\\\')', ': (currentScenes[cIdx]?.narration || \'\')')
text = text.replace(': (itNode.data?.summary || \\\'\\\')', ': (itNode.data?.summary || \'\')')
text = text.replace(': (itNode.data?.mechanism || \\\'\\\')', ': (itNode.data?.mechanism || \'\')')
text = text.replace(': (itNode.data?.key_point || \\\'\\\')', ': (itNode.data?.key_point || \'\')')
text = text.replace(': (itNode.data?.narration || \\\'\\\')', ': (itNode.data?.narration || \'\')')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print('Fixed!')
