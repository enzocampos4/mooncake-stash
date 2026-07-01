#!/usr/bin/env python3
"""
Reclassifica todas as 588 questões usando a hierarquia do Estratégia MED.
- Separa Ginecologia de Obstetrícia
- Standalone specialties (Oftalmologia, Ortopedia, etc)
- Área-aware keyword matching para subcategorias
"""
import json, os, re, glob
from collections import defaultdict

BASE = os.path.expanduser('~/hermesmed-questoes')

# ─── 1. Load hierarchy ───
with open(os.path.join(BASE, 'data', 'assuntos-estrategia.json')) as f:
    HIERARCHY = json.load(f)

# Build lookup: area_nome -> slug
AREA_SLUGS = {}
for slug, info in HIERARCHY.items():
    AREA_SLUGS[info['nome']] = slug

# ─── 2. PDF area → target slug mapping ───
# Some PDFs label "Ginecologia e Obstetrícia" — we must split
AREA_PDF_MAP = {
    'Clínica Médica': 'clinica-medica',
    'Cirurgia': 'cirurgia',
    'Pediatria': 'pediatria',
    'Ginecologia e Obstetrícia': None,  # will split below
    'Medicina Preventiva': 'medicina-preventiva',
    'Oftalmologia': 'oftalmologia',
    'Ortopedia': 'ortopedia',
    'Otorrinolaringologia': 'otorrino',
    'Psiquiatria': 'psiquiatria',
    'Dermatologia': 'clinica-medica',
    'Nefrologia': 'clinica-medica',
    'Neurologia': 'clinica-medica',
    'Infectologia': 'clinica-medica',
    'Cardiologia': 'clinica-medica',
    'Reumatologia': 'clinica-medica',
    'Pneumologia': 'clinica-medica',
    'Hepatologia': 'clinica-medica',
    'Endocrinologia': 'clinica-medica',
    'Hematologia': 'clinica-medica',
    'Gastroenterologia': 'clinica-medica',
    'Pediatria -  Otorrinolaringologia': 'otorrino',
    'Cirurgia - Hepatologia': 'cirurgia',
}

STANDALONE_AREAS = {k: v['nome'] for k, v in HIERARCHY.items() if k not in ('cirurgia', 'clinica-medica', 'ginecologia', 'obstetricia', 'medicina-preventiva', 'pediatria')}

# ─── 3. Ginecologia vs Obstetrícia classifier ───
GO_KEYWORDS = {
    'obstetricia': [
        'gestaç', 'gravide', 'parto', 'puerpério', 'aborto',
        'pré-natal', 'prenatal', 'cesárea', 'partograma',
        'trabalho de parto', 'amniorrexe', 'dilataç', 'contraç',
        'placenta', 'cório', 'amnion', 'cordão umbilical',
        'féto', 'fetal', 'nascimento', 'natimorto',
        'macrossomia', 'oligoidrâmnio', 'polidrâmnio',
        'doença hipertensiva específica da gestação', 'dheg',
        'pré-eclâmps', 'eclâmpsia', 'síndrome hellp',
        'diabetes gestacional', 'gestacional',
        'aloimunizaç', 'rh', 'incompatibilidade',
        'lóquios', 'aleitamento materno', 'amamentaç',
        'episiotomia', 'dequitadura', 'mioma e gestaç',
        'hcg', 'beta-hcg', 'ultrassonografia obstétrica',
        'usg obstétrica', 'doppler fetal', 'cardiotocografia',
        'vasa prévia', 'placenta prévia', 'descolamento prematuro de placenta',
        'sofrimento fetal', 'apgar', 'bradicardia fetal',
        'puerpério fisiológico', 'puerpério patológico',
        'gesta', 'gesta:', 'g:', 'gestações', 'primigesta',
        'multigesta', 'nuligesta', 'embrião', 'embrionário',
        'medicina fetal',
    ],
    'ginecologia': [
        'útero', 'ovário', 'tubas', 'endométrio', 'miométrio',
        'cérvice', 'colo uterino', 'colo do útero',
        'menstruaç', 'menopausa', 'climatério',
        'ciclo menstrual', 'anovulaç', 'sangramento uterino anormal',
        'dismenorreia', 'amenorreia', 'síndrome dos ovários policísticos',
        'sop', 'hirsutismo', 'endometriose', 'adenomiose',
        'mioma', 'leiomioma', 'pólipo endometrial',
        'papanicolau', 'citologia oncótica', 'hpv',
        'câncer de colo', 'câncer de ovário',
        'câncer de endométrio', 'neoplasia intraepitelial cervical',
        'nic', 'isterectomia', 'ooforectomia',
        'salphingo', 'laqueadura', 'diu', 'contracepç',
        'anticoncepcional', 'infertilidade conjugal',
        'reprodução assistida', 'fertilizaç',
        'corrimento vaginal', 'vaginose', 'candidíase vaginal',
        'tricomoníase', 'doença inflamatória pélvica', 'dip',
        'mama', 'mamografia', 'nódulo mamário', 'câncer de mama',
        'mastologia', 'mastite', 'fibroadenoma',
        'incontinência urinária', 'prolapso', 'uroginecologia',
        'sexualiade', 'dispareunia', 'vaginismo',
        'tireoide e ciclo', 'prolactina', 'hiperprolactinemia',
        'terapia hormonal', 'reposição hormonal', 'th',
        'atividade sexual', 'istmocele',
        'colposcopia', 'histeroscopia', 'videolaparoscopia ginecológica',
    ]
}

def classificar_gineco_obst(letra_a, explicacao, enunciado, alt_text, area_original):
    if area_original != 'Ginecologia e Obstetrícia':
        return area_original
    
    texto = f"{letra_a} {explicacao} {enunciado} {alt_text}".lower()
    
    score_g = sum(texto.count(kw.lower()) for kw in GO_KEYWORDS['ginecologia'])
    score_o = sum(texto.count(kw.lower()) for kw in GO_KEYWORDS['obstetricia'])
    
    if score_o > score_g:
        return 'Obstetrícia'
    elif score_g > score_o:
        return 'Ginecologia'
    else:
        # Tiebreaker: check placencenta/fetal keywords
        if any(kw in texto for kw in ['feto', 'fetal', 'gestaç', 'parto']):
            return 'Obstetrícia'
        return 'Ginecologia'

# ─── 4. Area-specific subcategory keywords ───
SUBAREA_KW = {
    'cirurgia': {
        'Trauma': ['trauma', 'politrauma', 'atls', 'hematoma', 'lesão traumática'],
        'Hérnias da Parede Abdominal': ['hérnia', 'hernioplastia', 'herniorrafia', 'parede abdominal'],
        'Vesícula e Vias Biliares': ['vesícula', 'colecist', 'coledoco', 'colangiografia', 'via biliar'],
        'Urgências Abdominais': ['abdômen agudo', 'abdome agudo', 'peritonite', 'apendicite', 'laparotomia'],
        'Proctologia': ['hemorroid', 'fístula anal', 'fissura anal', 'câncer de reto', 'procto'],
        'Cirurgia Bariátrica': ['bariátrica', 'bypass gástrico', 'sleeve', 'obesidade mórbida'],
        'Urologia': ['próstata', 'rim', 'bexiga', 'testículo', 'criptorquidia'],
        'Cirurgia Vascular': ['aneurisma', 'carótida', 'trombose venosa', 'tromboflebite', 'vascular'],
        'Cirurgia de Cabeça e Pescoço': ['cabeça e pescoço', 'tireoidectomia', 'paratireoide', 'câncer de tireoide'],
        'Cirurgia Torácica': ['torácica', 'pneumotórax', 'drenagem pleural', 'mediastino'],
        'Cirurgia Plástica': ['plástica', 'reparadora', 'enxerto', 'retalho'],
        'Cirurgia Infantil': ['pediátrica cirúrgica', 'cirurgia pediátrica', 'atresia', 'estenose hipertrófica'],
        'Avaliação Pré-Operatória': ['pré-operatória', 'avaliação pré', 'risco cirúrgico'],
        'Complicações Pós-Operatórias': ['pós-operatória', 'complicaç', 'deiscência', 'infecção de ferida'],
        'Princípios da Anestesiologia': ['anestesia', 'anestésico', 'intubaç', 'bloqueio'],
        'Cicatrização de Feridas': ['cicatrizaç', 'ferida', 'curativo'],
        'Queimaduras': ['queimadura', 'queimado', 'trauma elétrico'],
        'Nutrição em Cirurgia': ['nutrição', 'nutricional', 'jejum', 'pós-operatório dieta'],
        'Megacólon Adquirido': ['megacólon', 'chagas', 'constipaç'],
        'Ostomias Intestinais': ['ostomia', 'colostomia', 'ileostomia'],
    },
    'clinica-medica': {
        'Cardiologia': ['cardíaca', 'coraç', 'hipertens', 'insuficiência cardíaca', 'iam', 'infarto', 'coronária', 'arritmia', 'valvopat', 'ecg', 'eletro', 'choque'],
        'Dermatologia': ['pele', 'dermat', 'erupç', 'exantema', 'pápula', 'vesícula', 'pustulosa', 'urticária', 'psoríase', 'lúpus eritematoso', 'hanseníase', 'lepra', 'melanoma', 'câncer de pele'],
        'Endocrinologia': ['diabetes', 'diabético', 'tireoide', 'adrenal', 'hipófise', 'obesidade', 'síndrome metabólica', 'osteoporose', 'hipoglicemia'],
        'Gastroenterologia': ['esôfago', 'estômago', 'pâncreas', 'intestino', 'dispepsia', 'doença do refluxo', 'gastrite', 'úlcera', 'h. pylori', 'hemorragia digestiva'],
        'Hepatologia': ['fígado', 'cirrose', 'hepatite', 'icterícia', 'insuficiência hepática', 'transplante hepático', 'hepatocarcinoma'],
        'Hematologia': ['anemia', 'leucemia', 'linfoma', 'hemoglobi', 'plaqueta', 'coagula', 'hemostasia', 'transfusão', 'mieloma'],
        'Infectologia': ['hiv', 'aids', 'tuberculose', 'sepse', 'antimicrobiano', 'febre', 'arbovirose', 'dengue', 'chikungunya', 'zika', 'pneumonia', 'vacina', 'antirretroviral'],
        'Nefrologia': ['renal', 'rim', 'nefro', 'diálise', 'hemodiálise', 'glomerulonefrite', 'itulitíase', 'potássio', 'sódio', 'hipernatremia', 'hiponatremia'],
        'Neurologia': ['avc', 'derrame', 'cefaleia', 'convulsão', 'epilepsia', 'demência', 'parkinson', 'alzheimer', 'esclerose múltipla', 'miastenia', 'coma'],
        'Pneumologia': ['pulmonar', 'asma', 'dpoc', 'pleural', 'tromboembolismo', 'tep', 'câncer de pulmão', 'pneumotórax', 'bronquiectasia'],
        'Reumatologia': ['artrite', 'lúpus', 'vasculite', 'gota', 'espondilite', 'reumatóide', 'síndrome de sjögren', 'esclerodermia', 'dermatomiosite'],
    },
    'ginecologia': {
        'Ginecologia básica': ['consulta ginecológica', 'exame ginecológico', 'preventivo', 'papanicolau'],
        'Ginecologia endócrina': ['menarca', 'menopausa', 'climatério', 'ciclo menstrual', 'anovulaç', 'amenorreia', 'sop', 'hirsutismo', 'prolactina'],
        'Infecções em ginecologia': ['corrimento', 'vaginose', 'candidíase', 'tricomoníase', 'dip', 'hpv', 'condiloma'],
        'Oncologia ginecológica': ['câncer de colo', 'câncer de ovário', 'nic', 'neoplasia', 'tumor de', 'ovário', 'endométrio'],
        'Mastologia': ['mama', 'mamografia', 'nódulo mamário', 'câncer de mama', 'fibroadenoma'],
        'Uroginecologia': ['incontinência', 'prolapso', 'bexiga', 'assoalho pélvico'],
        'Ginecologia geral': ['mioma', 'endometriose', 'infertilidade', 'contracepç', 'diu'],
        'Sexualidade': ['sexual', 'dispareunia', 'vaginismo'],
    },
    'obstetricia': {
        'Obstetrícia fisiológica': ['gestaç fisiológica', 'pré-natal fisiológico'],
        'Pré-natal': ['pré-natal', 'prenatal', 'acompanhamento pré'],
        'Parto': ['parto', 'cesárea', 'partograma', 'trabalho de parto', 'contraç'],
        'Puerpério': ['puerpério', 'lóquios', 'aleitamento', 'amamentaç'],
        'Intercorrências obstétricas': ['pré-eclâmpsia', 'eclâmpsia', 'hellp', 'placenta prévia', 'dpp', 'sofrimento fetal', 'aborto'],
        'Doenças associadas à gestação': ['diabetes gestacional', 'gestacional', 'hipertensão gestacional'],
        'Medicina fetal': ['medicina fetal', 'ultrassom', 'doppler', 'cardiotocografia', 'líquido amniótico'],
    },
    'medicina-preventiva': {
        'Sistema Único de Saúde (SUS)': ['sus', 'sistema único de saúde', 'atenção básica', 'referência', 'contra-referência', 'financiamento', 'bpa', 'sia', 'sih'],
        'Medicina de Família e Comunidade': ['atenção primária', 'saúde da família', 'psf', 'nasf', 'acs', 'agente comunitário', 'mfc'],
        'Epidemiologia': ['epidemio', 'incidência', 'prevalência', 'mortalidade', 'morbidade', 'estudo transversal', 'caso-controle', 'coorte', 'ensaioclínico', 'acurácia', 'sensibilidade', 'especificidade', 'valor preditivo', 'rr', 'odds ratio', 'risco relativo'],
        'Ética Médica': ['código de ética', 'sigilo', 'prontuário', 'termo de consentimento', 'ortotanásia', 'eutanásia', 'distana', 'comitê de ética', 'cremem'],
        'Saúde do Trabalhador': ['trabalhador', 'doença ocupacional', 'acidente de trabalho', 'ergonomia', 'lER', 'dort', 'pcmso', 'pcso'],
    },
    'pediatria': {
        'Puericultura': ['puericultura', 'crescimento', 'desenvolvimento', 'marco', 'aleitamento materno', 'vacina na infância', 'curva de crescimento'],
        'Pneumologia Pediátrica': ['bronquiolite', 'asma infantil', 'pneumonia infantil', 'fibrose cística', 'mucoviscidose'],
        'Infectologia Pediátrica': ['febre em criança', 'exantema infantil', 'sarampo', 'rubéola', 'caxumba', 'varicela', 'meningite bacteriana', 'sepse neonatal'],
        'Cardiologia Pediátrica': ['cardiopatia congênita', 'sopro', 'cianose', 'persistência do canal arterial', 'comunicação interventricular', 'tetralogia de fallot'],
        'Gastrologia Pediátrica': ['diarreia infantil', 'desidratação', 'refluxo gastroesofágico', 'doença celíaca', 'alergia alimentar'],
        'Hematologia Pediátrica': ['anemia ferropriva', 'anemia falciforme', 'hemofilia', 'púrpura'],
        'Nefrologia Pediátrica': ['itulactente', 'síndrome nefrótica', 'glomerulonefrite difusa aguda'],
        'Neuropediatria': ['convulsão febril', 'paralisia cerebral', 'atraso do desenvolvimento', 'tdah'],
        'Reumatologia Pediátrica': ['artrite idiopática juvenil', 'febre reumática', 'púrpura de henoch-schönlein'],
        'Endocrinologia pediátrica': ['baixa estatura', 'puberdade precoce', 'hipotireoidismo congênito', 'diabetes tipo 1'],
        'Emergências Pediátricas': ['convulsão', 'obstrução de vias aéreas', 'reanimação pediátrica', 'avaliação primária'],
        'Neonatologia': ['icterícia neonatal', 'recém-nascido', 'prematuro', 'apgar', 'reanimação neonatal', 'triagem neonatal', 'teste do pezinho'],
        'Maus tratos': ['maus-tratos', 'abuso infantil', 'síndrome do bebê sacudido'],
        'Outros': ['síndrome de down', 'erros inatos do metabolismo'],
    },
}

# ─── 5. Load all questions ───
simfiles = sorted(glob.glob(os.path.join(BASE, 'data', 'simulados', '*-simulado.json')))
all_questions = []
for path in simfiles:
    with open(path) as f:
        data = json.load(f)
    edicao = os.path.basename(path).replace('-simulado.json', '')
    for q in data.get('questoes', []):
        q['_simulado'] = f"{edicao}-simulado"
        q['_edicao'] = edicao
        all_questions.append(q)

print(f"Total: {len(all_questions)} questions loaded\n")

# ─── 6. Reclassify ───
by_slug = defaultdict(list)
stats = defaultdict(lambda: {'gineco': 0, 'obstetricia': 0})

for q in all_questions:
    area_orig = q.get('area', '').strip()
    area_clean = classificar_gineco_obst(
        q.get('correta', ''), q.get('explicacao', ''),
        q.get('enunciado', ''), str(q.get('alternativas', {})),
        area_orig
    )
    
    # Map to slug
    slug = AREA_PDF_MAP.get(area_clean)
    if not slug:
        slug = AREA_SLUGS.get(area_clean)
    if not slug:
        # Try splitting composite names like "Pediatria - Otorrinolaringologia"
        if ' - ' in area_clean or ' -  ' in area_clean:
            parts = re.split(r'\s*-\s*', area_clean)
            main_area = parts[0].strip()
            slug = AREA_SLUGS.get(main_area)
            q['_split_warning'] = True
        if not slug:
            print(f"  ⚠️  '{area_clean}' (orig: '{area_orig}') → slug '{slug}'")
            slug = area_clean.lower().replace(' ', '-')
    
    q['area'] = area_clean
    
    # Subarea matching (area-aware)
    subarea_kw = SUBAREA_KW.get(slug, {})
    best_sub = ''
    best_score = 0
    texto = f"{q.get('enunciado','')} {q.get('explicacao','')} {q.get('correta','')}".lower()
    texto += ' ' + ' '.join(str(v) for v in (q.get('alternativas') or {}).values()).lower()
    
    for sub, kws in subarea_kw.items():
        score = sum(1 for kw in kws if kw.lower() in texto)
        if score > best_score:
            best_score = score
            best_sub = sub
    
    q['subarea'] = best_sub if best_score > 0 else ''
    q['_area_slug'] = slug
    by_slug[slug].append(q)
    
    if area_orig == 'Ginecologia e Obstetrícia' and area_clean != area_orig:
        stats[slug]['gineco'] += 1
        if slug == 'ginecologia':
            pass

# Stats
print("\n📊 Resultado da reclassificação:")
for slug in sorted(by_slug.keys()):
    subs = defaultdict(int)
    for q in by_slug[slug]:
        if q['subarea']:
            subs[q['subarea']] += 1
    sub_list = sorted(subs.items(), key=lambda x: -x[1])[:8]
    sub_str = ' | '.join(f"{s}:{c}" for s, c in sub_list)
    print(f"  {slug}: {len(by_slug[slug])} questões  [{sub_str}]{'...' if len(subs) > 8 else ''}")

# ─── 7. Write area files ───
print("\n✍️  Escrevendo arquivos:")
for slug, questions in by_slug.items():
    path = os.path.join(BASE, 'data', f'{slug}.json')
    with open(path, 'w') as f:
        json.dump({"questoes": questions}, f, ensure_ascii=False, indent=2)
    print(f"  {slug}.json — {len(questions)} questões")

# ─── 7b. Proper slug function ───
def slugify(s):
    """Generate a clean URL-safe slug from Portuguese text."""
    s = s.lower().strip()
    replacements = {
        'á':'a','à':'a','â':'a','ã':'a','ä':'a',
        'é':'e','è':'e','ê':'e','ë':'e',
        'í':'i','ì':'i','î':'i','ï':'i',
        'ó':'o','ò':'o','ô':'o','õ':'o','ö':'o',
        'ú':'u','ù':'u','û':'u','ü':'u',
        'ç':'c','ñ':'n',
        '/':'-','(':'',')':'','"':'',',':'',':':''
    }
    for f, t in replacements.items():
        s = s.replace(f, t)
    s = re.sub(r'[^a-z0-9-]', '-', s)
    s = re.sub(r'-+', '-', s)
    s = s.strip('-')
    return s

# ─── 8. Build assuntos.json ───
assuntos = {}
for slug, info in HIERARCHY.items():
    questions = by_slug.get(slug, [])
    subs = info.get('subcategorias', []) + list(info.get('subdetalhes', {}).keys())
    
    sub_counts = defaultdict(int)
    for q in questions:
        if q['subarea'] and q['subarea'] in subs:
            sub_counts[q['subarea']] += 1
    
    formatted = {}
    for sub in sorted(subs):
        count = sub_counts.get(sub, 0)
        if count > 0:
            formatted[slugify(sub)] = {"nome": sub, "total": count}
    
    # Add subdetalhes if exists
    detalhes = info.get('subdetalhes', {})
    detalhes_formatted = {}
    for cat, subs_list in detalhes.items():
        detalhes_formatted[slugify(cat)] = {
            "nome": cat,
            "subcategorias": subs_list,
            "total_questoes": sub_counts.get(cat, 0)
        }
    
    assuntos[slug] = {
        "nome": info['nome'],
        "total": len(questions),
        "subcategorias": formatted,
        "subdetalhes": detalhes_formatted if detalhes else {}
    }

# Add standalone specialties that might have questions
for slug, nome in STANDALONE_AREAS.items():
    if slug not in assuntos and by_slug.get(slug):
        assuntos[slug] = {
            "nome": nome,
            "total": len(by_slug[slug]),
            "subcategorias": {}
        }

path = os.path.join(BASE, 'data', 'assuntos.json')
with open(path, 'w') as f:
    json.dump(assuntos, f, ensure_ascii=False, indent=2)
print(f"\n✅ assuntos.json — {len(assuntos)} áreas")

# Print final stats
print(f"\n📊 Total: {sum(len(v) for v in by_slug.values())} questões em {len(by_slug)} áreas")
total_sub = sum(1 for qlist in by_slug.values() for q in qlist if q.get('subarea'))
print(f"  {total_sub} com subcategoria atribuída")
