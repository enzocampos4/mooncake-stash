#!/usr/bin/env python3
"""
Auto-classifica sub_subarea (sub-subcategoria) para TODAS as áreas com subdetalhes.

Por padrão foca em Clínica Médica / Cirurgia / Obstetrícia / Pediatria.
Para habilitar Ginecologia / Medicina Preventiva, basta adicionar `subdetalhes`
em assuntos-estrategia.json e o script passa a cobri-las automaticamente.

Algoritmo:
- Para cada área em data/<slug>.json:
  - Lê apenas as subcategorias que têm subdetalhes em assuntos.json
  - Para cada questão: faz matching de keywords no texto (enunciado + explicação + alternativas)
  - Score: phrase match (+5), short match (+3), palavras individuais (+1)
  - Threshold: >=2 para classificar
"""
import json, os, re
from collections import defaultdict

BASE = os.path.expanduser('~/hermesmed-questoes')
DATA = os.path.join(BASE, 'data')

# ─── 1. Load data ───
with open(os.path.join(DATA, 'assuntos.json')) as f:
    assuntos = json.load(f)


def gerar_keywords(nome):
    """Gera keywords a partir do nome da sub-subcategoria."""
    nome_clean = nome.lower().strip()
    nome_clean = re.sub(r'\([^)]*\)', '', nome_clean)  # remove parenteses
    nome_clean = re.sub(r'[^\w\s]', ' ', nome_clean)   # remove pontuação
    words = [w.strip() for w in nome_clean.split() if len(w.strip()) > 2]
    return words


def build_kw_map(subdetalhes_dict):
    """Constroi {sub_subarea_nome: {phrase, words, short}} a partir de subdetalhes."""
    kw_map = {}
    for _, detalhes in subdetalhes_dict.items():
        subcats = detalhes.get('subcategorias', []) if isinstance(detalhes, dict) else detalhes
        for sc in subcats:
            words = gerar_keywords(sc)
            kw_map[sc] = {
                'phrase': sc.lower().strip(),
                'words': words,
                'short': sc.lower().replace('(', '').replace(')', '').strip(),
            }
    return kw_map


def get_subarea_to_slug(area_slug):
    """Subarea nome (ex: 'Cardiologia') -> slug (ex: 'cardiologia')."""
    subarea_to_slug = {}
    cm_subs = assuntos.get(area_slug, {}).get('subcategorias', {})
    if isinstance(cm_subs, dict):
        for sub_slug, sub_info in cm_subs.items():
            subarea_to_slug[sub_info.get('nome', sub_slug)] = sub_slug
    return subarea_to_slug


def classify_area(area_slug):
    """Classifica q.sub_subarea em todas as questões de data/<area_slug>.json."""
    arq = os.path.join(DATA, f'{area_slug}.json')
    if not os.path.exists(arq):
        return None

    with open(arq) as f:
        ar_data = json.load(f)

    subdetalhes = assuntos.get(area_slug, {}).get('subdetalhes', {})
    if not subdetalhes:
        print(f'⏭️  {area_slug}: sem subdetalhes, pulando')
        return None

    subarea_to_slug = get_subarea_to_slug(area_slug)
    kw_map = build_kw_map(subdetalhes)

    stats = defaultdict(lambda: defaultdict(int))
    classified = 0
    unclassified = 0

    for q in ar_data.get('questoes', []):
        subarea_nome = q.get('subarea', '')
        if not subarea_nome:
            continue

        sub_slug = subarea_to_slug.get(subarea_nome)
        if not sub_slug or sub_slug not in subdetalhes:
            continue

        # Filtra keywords: pega apenas da subcategoria correspondente
        sub_kw = {k: v for k, v in kw_map.items() if k in subdetalhes[sub_slug]['subcategorias']}
        if not sub_kw:
            continue

        texto = f"{q.get('enunciado','')} {q.get('explicacao','')} {q.get('correta','')}".lower()
        texto += ' ' + ' '.join(str(v) for v in (q.get('alternativas') or {}).values()).lower()

        best_match = ''
        best_score = 0
        for sub_sub, info in sub_kw.items():
            score = 0
            if info['phrase'] in texto:
                score += 5
            if info['short'] in texto:
                score += 3
            score += sum(1 for w in info['words'] if w in texto)

            if score > best_score:
                best_score = score
                best_match = sub_sub

        if best_match and best_score >= 2:
            q['sub_subarea'] = best_match
            classified += 1
            stats[sub_slug][best_match] += 1
        else:
            q['sub_subarea'] = ''
            unclassified += 1

    with open(arq, 'w') as f:
        json.dump(ar_data, f, ensure_ascii=False, indent=2)

    print(f'✅ {area_slug}: {classified} classificadas / {unclassified} sem match')
    for sub_slug, matches in sorted(stats.items()):
        sub_nome = subdetalhes[sub_slug]['nome']
        total = sum(matches.values())
        print(f'    {sub_nome}: {total} questões')
        for sub_sub, cnt in sorted(matches.items(), key=lambda x: -x[1]):
            print(f'      - {sub_sub}: {cnt}')
    print()
    return classified


# ─── Run for all areas ───
print('🔍 Classificando sub_subarea em todas as áreas com subdetalhes:\n')
TOTAL = 0
for area_slug in assuntos.keys():
    subdetalhes = assuntos[area_slug].get('subdetalhes', {})
    if not subdetalhes:
        continue
    n = classify_area(area_slug)
    if n is not None:
        TOTAL += n

print(f'🎯 Total: {TOTAL} questões classificadas em sub_subarea')
