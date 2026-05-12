#!/usr/bin/env python3
"""Regenerate .well-known/skills/index.json and commit."""

import json, os, re, subprocess

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(root)

skills = []
for d in sorted(os.listdir('.')):
    if not d.startswith('clickzetta-') or not os.path.isdir(d):
        continue
    skill_md = os.path.join(d, 'SKILL.md')
    if not os.path.exists(skill_md):
        continue
    content = open(skill_md).read()
    desc_match = re.search(r'description:\s*\|?\s*\n(.*?)(?=\n\s*\w+:|\n---)', content, re.DOTALL)
    if not desc_match:
        desc_match = re.search(r'description:\s*[>|]?\s*\n?\s*(.+?)(?=\n\s*\w+:|\n---)', content)
    desc = desc_match.group(1).strip().split('\n')[0].strip() if desc_match else ''
    files = ['SKILL.md']
    refs_dir = os.path.join(d, 'references')
    if os.path.isdir(refs_dir):
        for f in sorted(os.listdir(refs_dir)):
            if f.endswith('.md'):
                files.append(f'references/{f}')
    skills.append({'name': d, 'description': desc, 'files': files})

os.makedirs('.well-known/skills', exist_ok=True)
index_path = '.well-known/skills/index.json'
with open(index_path, 'w') as f:
    json.dump({'skills': skills}, f, ensure_ascii=False, indent=2)
    f.write('\n')

print(f'✓ Generated {index_path} ({len(skills)} skills)')

# Auto commit and push
diff = subprocess.run(['git', 'diff', '--stat', index_path], capture_output=True, text=True).stdout
if not diff:
    print('✓ No changes, already up to date')
else:
    subprocess.run(['git', 'add', index_path], check=True)
    subprocess.run(['git', 'commit', '-m', f'chore: update skills index ({len(skills)} skills)'], check=True)
    subprocess.run(['git', 'push'], check=True)
    print('✓ Committed and pushed')
