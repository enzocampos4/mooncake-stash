#!/bin/bash
cd /home/ubuntu/hermesmed-questoes

echo "=== PRE-DEPLOY CHECK ==="

# 1. Regenera sessao-index.json
python3 -c "
import json, os
idx = {}
for s in ['clinica-medica','cirurgia','pediatria','ginecologia','obstetricia','medicina-preventiva']:
    with open(f'data/{s}.json') as f:
        d = json.load(f)
    for q in d.get('questoes', []):
        b = q.get('banca','') or q.get('instituicao','') or ''
        a = q.get('ano',0)
        if not isinstance(a, int):
            try: a = int(a)
            except: a = 0
        idx[q['id']] = {
            'area': s,
            'area_nome': {'clinica-medica':'Clinica Medica','cirurgia':'Cirurgia','pediatria':'Pediatria','ginecologia':'Ginecologia','obstetricia':'Obstetricia','medicina-preventiva':'Medicina Preventiva'}[s],
            'sub': q.get('subarea','').strip() or 'Geral',
            'subsub': q.get('sub_subarea','').strip() or '',
            'banca': b,
            'ano': a,
            'fonte': q.get('fonte','') or '',
        }
with open('data/sessao-index.json', 'w') as f:
    json.dump(idx, f, indent=2, ensure_ascii=False)
print(f'[1/4] INDICE: {len(idx)} questoes')
"

# 2. Bancas suspeitas
python3 -c "
import json
with open('data/sessao-index.json') as f:
    idx = json.load(f)
from collections import Counter
bancas = Counter(v['banca'] for v in idx.values() if v['banca'])
suspeitas = [(b,c) for b,c in bancas.items() if '(' in b or any(d in b for d in '0123456789' if d.isdigit())]
print(f'[2/4] BANCAS: {len(bancas)} unicas, {len(suspeitas)} suspeitas')
for b,c in sorted(suspeitas, key=lambda x:-x[1]):
    print(f'  \"{b}\" ({c})')
"

# 3. Subtopicos
python3 -c "
import json
with open('data/sessao-index.json') as f:
    idx = json.load(f)
c = sum(1 for v in idx.values() if v['subsub'])
s = sum(1 for v in idx.values() if not v['subsub'])
print(f'[3/4] SUBTOPICOS: {c} com, {s} sem ({c*100//(c+s)}%)')
"

# 4. Geral por area
python3 -c "
import json
with open('data/sessao-index.json') as f:
    idx = json.load(f)
from collections import Counter
areas = Counter(v['area_nome'] for v in idx.values())
print('[4/4] AREAS:')
for a, c in areas.most_common():
    print(f'  {c:4d} x {a}')
print(f'  TOTAL: {sum(areas.values())}')
"

echo "=== OK ==="
