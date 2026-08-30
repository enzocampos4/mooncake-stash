#!/bin/bash
cd /home/ubuntu/hermesmed-questoes
HAS_ISSUES=0
OUTPUT=""

# 1. Regenera sessao-index.json (sempre)
python3 -c "
import json, os
AREA_NOME = {
    'clinica-medica':'Clinica Medica','cirurgia':'Cirurgia','pediatria':'Pediatria',
    'ginecologia':'Ginecologia','obstetricia':'Obstetricia','medicina-preventiva':'Medicina Preventiva',
    'oftalmologia':'Oftalmologia','ortopedia':'Ortopedia','otorrino':'Otorrinolaringologia',
    'psiquiatria':'Psiquiatria',
}
idx = {}
for s, an in AREA_NOME.items():
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
            'area_nome': an,
            'sub': q.get('subarea','').strip() or 'Geral',
            'subsub': q.get('sub_subarea','').strip() or '',
            'banca': b,
            'ano': a,
            'fonte': q.get('fonte','') or '',
        }
with open('data/sessao-index.json', 'w') as f:
    json.dump(idx, f, indent=2, ensure_ascii=False)
" 2>/dev/null

# 2. Verifica se tem algo pra commitar
if [ -n "$(git status --porcelain)" ]; then
    OUTPUT+="⚠️  Dados foram alterados — sessao-index.json regenerado.\n"
    HAS_ISSUES=1
fi

# 3. Verifica bancas suspeitas
SUS=$(python3 -c "
import json
with open('data/sessao-index.json') as f:
    idx = json.load(f)
from collections import Counter
bancas = Counter(v['banca'] for v in idx.values() if v['banca'])
sus = [(b,c) for b,c in bancas.items() if '(' in b or any(d.isdigit() for d in b)]
if sus:
    for b,c in sorted(sus, key=lambda x:-x[1]):
        print(f'{b} ({c})')
" 2>/dev/null)
if [ -n "$SUS" ]; then
    OUTPUT+="⚠️  Bancas suspeitas:\n$SUS\n"
    HAS_ISSUES=1
fi

# 4. Verifica % de subtopicos
PCT=$(python3 -c "
import json
with open('data/sessao-index.json') as f:
    idx = json.load(f)
c = sum(1 for v in idx.values() if v['subsub'])
s = sum(1 for v in idx.values() if not v['subsub'])
print(c*100//(c+s))
" 2>/dev/null)
if [ "$PCT" -lt 70 ]; then
    OUTPUT+="⚠️  Subtopico rate baixo: ${PCT}%\n"
    HAS_ISSUES=1
fi

# 5. Verifica total de questoes
TOTAL=$(python3 -c "
import json
with open('data/sessao-index.json') as f:
    idx = json.load(f)
print(len(idx))
" 2>/dev/null)
if [ "$TOTAL" -ne 31932 ]; then
    OUTPUT+="⚠️  Total de questoes mudou: ${TOTAL} (esperado 31932)\n"
    HAS_ISSUES=1
fi

if [ $HAS_ISSUES -eq 1 ]; then
    echo -e "🔍 Revisão HermesMed:\n$OUTPUT"
    # Auto-deploy se necessario
    if [ -n "$(git status --porcelain data/sessao-index.json)" ]; then
        git add data/sessao-index.json
        git commit -m "auto: sessao-index.json regenerated"
        git push origin main 2>/dev/null
        echo "✅ sessao-index.json atualizado e deploy feito."
    fi
fi
