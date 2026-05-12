#!/usr/bin/env python3
"""Regenerate .well-known/skills/index.json from main branch skill directories."""

import json, os, re

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
    # Extract first line of description from frontmatter
    desc_match = re.search(r'description:\s*\|?\s*\n(.*?)(?=\n\s*\w+:|\n---)', content, re.DOTALL)
    if not desc_match:
        desc_match = re.search(r'description:\s*[>|]?\s*\n?\s*(.+?)(?=\n\s*\w+:|\n---)', content)
    desc = desc_match.group(1).strip().split('\n')[0].strip() if desc_match else ''
    # Collect files
    files = ['SKILL.md']
    refs_dir = os.path.join(d, 'references')
    if os.path.isdir(refs_dir):
        for f in sorted(os.listdir(refs_dir)):
            if f.endswith('.md'):
                files.append(f'references/{f}')
    skills.append({'name': d, 'description': desc, 'files': files})

os.makedirs('.well-known/skills', exist_ok=True)
with open('.well-known/skills/index.json', 'w') as f:
    json.dump({'skills': skills}, f, ensure_ascii=False, indent=2)
    f.write('\n')

print(f'✓ Generated .well-known/skills/index.json ({len(skills)} skills)')
