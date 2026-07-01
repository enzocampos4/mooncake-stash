#!/usr/bin/env python3
"""
Extract questions from ENAMED simulated exam PDFs (Caderno de Respostas)
and create JSON files for the HermesMed question bank.

Usage:
    python3 scripts/extract_simulado.py <pdf_path> [--edicao N]
"""

import fitz  # pymupdf
import json
import os
import re
import sys
from pathlib import Path

# Build regex for question start: flexible format (1 or 2 digits)
# Handles:
#   "01\t– (Estratégia MED"  (tab + en-dash)  – 1º, 3º, 11º
#   "01.\t (Estratégia MED"  (period + tab)   – 5º
#   "1.\t(Estratégia MED"    (period + tab)   – 9º
Q_START = re.compile(r'(\d{1,2})\s*(?:[.–]\s*\t|\t\s*[.–])\s*\(Estratégia MED')

# Build regex for Gabarito
GABARITO_PATTERN = re.compile(r'Gabarito:\s*([A-D])', re.MULTILINE)

# Build regex for start of alternatives (single-line match to find their positions)
ALT_START = re.compile(r'^([A-D])\)\t', re.MULTILINE)

# Build regex for COMENTÁRIOS (flexible: plural/singular, with/without colon, with/without subtopic)
# Also handles "RESOLUÇÃO COMENTADA" (alternative format in some 9º simulado questions)
# Handles:
#   "COMENTÁRIOS:" — standard
#   "COMENTÁRIOS (SUBTÓPICO – PROF):" — with subtopic
#   "COMENTÁRIO" — singular, no colon
#   "RESOLUÇÃO COMENTADA" — alternative format
COMENTARIOS_PATTERN = re.compile(r'^\s*(?:COMENTÁRIOS?(?:\s*\([^)]*\))?:?\s*\n|RESOLUÇÃO COMENTADA\s*\n)', re.MULTILINE)

# Categories and subcategories from Estratégia MED subject divisions
AREAS_MAP = {
    "cirurgia": "Cirurgia",
    "clínica médica": "Clínica Médica",
    "clinica médica": "Clínica Médica",
    "ginecologia": "Ginecologia e Obstetrícia",
    "obstetrícia": "Ginecologia e Obstetrícia",
    "ginecologia e obstetrícia": "Ginecologia e Obstetrícia",
    "medicina preventiva": "Medicina Preventiva",
    "pediatria": "Pediatria",
    "ortopedia": "Ortopedia",
    "dermatologia": "Dermatologia",
    "oftalmologia": "Oftalmologia",
    "otorrinolaringologia": "Otorrinolaringologia",
    "otorrino": "Otorrinolaringologia",
    "psiquiatria": "Psiquiatria",
    "infectologia": "Infectologia",
    "medicina intensiva": "Medicina Intensiva",
    "terapia intensiva": "Medicina Intensiva",
    "emergência": "Emergência",
    "medicina de emergência": "Emergência",
    "nefrologia": "Nefrologia",
    "reumatologia": "Reumatologia",
    "geriatria": "Geriatria",
    "medicina do trabalho": "Medicina Preventiva",
    "medicina legal": "Medicina Preventiva",
    "bioética": "Medicina Preventiva",
    "neurologia": "Clínica Médica",
    "cardiologia": "Clínica Médica",
    "pneumologia": "Clínica Médica",
    "gastroenterologia": "Clínica Médica",
    "endocrinologia": "Clínica Médica",
    "hematologia": "Clínica Médica",
    "oncologia": "Clínica Médica",
}


def normalize_area(raw_area):
    """Map the area string from the PDF to a canonical area."""
    raw_lower = raw_area.strip().lower()
    if raw_lower in AREAS_MAP:
        return AREAS_MAP[raw_lower]
    return raw_area.strip()


def extract_question_text(pdf_path):
    """Extract all text from a PDF."""
    doc = fitz.open(pdf_path)
    full_text = ""
    for i in range(len(doc)):
        page = doc[i]
        full_text += page.get_text() + "\n"
    doc.close()
    return full_text


def split_questions(full_text):
    """Split the full PDF text into individual question blocks."""
    # Find all positions where questions start
    matches = list(Q_START.finditer(full_text))
    
    questions = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block = full_text[start:end].strip()
        questions.append(block)
    
    return questions


def parse_header(block):
    """Parse the question header and return (area, subarea, enunciado)."""
    # Extract the parenthesized part - flexible format (handles both tab+dash and period+tab)
    paren_match = re.match(r'\d{1,2}\s*(?:[.–]\s*\t|\t\s*[.–])\s*\((Estratégia MED[^)]+)\)\s*(.*)', block, re.DOTALL)
    if not paren_match:
        paren_match = re.match(r'\d{1,2}\s*[.–]\s*\((Estratégia MED[^)]+)\)\s*(.*)', block, re.DOTALL)
    
    if not paren_match:
        return None, None, block
    
    header = paren_match.group(1)
    after_header = paren_match.group(2)
    
    # Extract enunciado: everything before the first alternative (A)\t)
    # First check for the alternatives pattern
    alt_match = re.search(r'\n[A-D]\)\t', after_header)
    if alt_match:
        enunciado = after_header[:alt_match.start()].strip()
    else:
        enunciado = after_header.strip()
    
    # Also remove "COMENTÁRIOS:" or "COMENTÁRIO" or "RESOLUÇÃO COMENTADA" if it somehow made it into enunciado
    coment_match = re.search(r'\n\s*(?:COMENTÁRIOS?:?[\s:]|COMENTÁRIOS?\s*\([^)]*\)[\s:]|RESOLUÇÃO COMENTADA)', enunciado)
    if coment_match:
        enunciado = enunciado[:coment_match.start()].strip()
    
    # Clean up enunciado - remove tab characters and normalize whitespace
    enunciado = re.sub(r'\t', ' ', enunciado)
    enunciado = re.sub(r'  +', ' ', enunciado)
    enunciado = enunciado.strip()
    
    # Parse header fields
    fields = [f.strip() for f in header.split(' – ')]
    
    area = ""
    subarea = ""
    if len(fields) >= 3:
        raw_area = fields[2]
        
        # Strip professor name if present in raw_area (e.g., "Pediatria - Prof. Bruno Calvo")
        raw_area = re.sub(r'\s*-\s*Prof\..*', '', raw_area, flags=re.IGNORECASE).strip()
        
        # Check if there's a subarea (4th field)
        if len(fields) >= 4:
            subarea_full = fields[3]
            # Check if subarea contains "Prof" - if so, it's just professor, no subarea
            if 'Prof' not in subarea_full:
                subarea = subarea_full.split(' - ')[0].strip()
        
        # Handle "Clínica Médica – Neurologia" format in the area field
        if ' – ' in raw_area:
            parts = raw_area.split(' – ')
            raw_area = parts[0]
            if not subarea:
                subarea = parts[1]
        
        area = normalize_area(raw_area)
    
    return area, subarea, enunciado


def parse_alternatives(block):
    """Parse alternatives from the question block, handling multi-line alternatives."""
    alternatives = {}
    lines = block.split('\n')
    current_letter = None
    current_parts = []
    
    for line in lines:
        alt_match = ALT_START.match(line)
        if alt_match:
            # Save previous alternative before starting a new one
            if current_letter:
                alternatives[current_letter] = ' '.join(current_parts).strip()
            current_letter = alt_match.group(1)
            # Everything after "X)\t" on the first line
            first_text = line[alt_match.end():].strip()
            current_parts = [first_text]
        elif current_letter and line.strip():
            # Continuation line — but stop if we hit COMENTÁRIOS, RESOLUÇÃO COMENTADA or Gabarito
            # Must check stripped line because "COMENTÁRIO\n" won't match with trailing \s requirement
            stripped = line.strip()
            if stripped.startswith('COMENTÁRIO') or 'RESOLUÇÃO' in stripped or stripped.startswith('Gabarito:'):
                break
            current_parts.append(line.strip())
    
    # Save the last alternative
    if current_letter:
        alternatives[current_letter] = ' '.join(current_parts).strip()
    
    return alternatives


def get_correct_answer(block):
    """Extract the correct answer letter from the block."""
    match = GABARITO_PATTERN.search(block)
    if match:
        return match.group(1)
    return None


def get_explanation(block):
    """Extract the explanation/COMENTÁRIOS section (handles singular/plural, with/without colon)."""
    match = COMENTARIOS_PATTERN.search(block)
    if not match:
        return None
    
    # Extract everything after COMENTÁRIOS header
    start = match.end()
    explanation = block[start:].strip()
    
    # Remove trailing "Gabarito: X" if present
    explanation = GABARITO_PATTERN.sub('', explanation).strip()
    
    return explanation if explanation else None


def extract_images_from_pdf(pdf_path, output_dir, simulado_id, questao_num, page_range):
    """Extract images from a range of pages in the PDF."""
    doc = fitz.open(pdf_path)
    images = []
    img_idx = 1
    
    for page_num in page_range:
        page = doc[page_num]
        image_list = page.get_images()
        
        for img in image_list:
            xref = img[0]
            base_image = doc.extract_image(xref)
            img_bytes = base_image["image"]
            img_ext = base_image["ext"]
            
            # Skip tiny images (logos, icons under 5KB)
            if len(img_bytes) < 5 * 1024:
                continue
            
            # filename: q{numero}_img{idx}.{ext}
            img_filename = f"q{questao_num}_img{img_idx}.{img_ext}"
            img_path = os.path.join(output_dir, img_filename)
            
            with open(img_path, "wb") as f:
                f.write(img_bytes)
            
            images.append(f"data/simulados/imgs/{simulado_id}/{img_filename}")
            img_idx += 1
    
    doc.close()
    return images


def assign_images_to_questions(pdf_path, simulado_dir, simulado_id, questions_info):
    """
    For each question, find which pages contain its content
    and extract images from those pages.
    """
    doc = fitz.open(pdf_path)
    
    # Build mapping: for each question, find the page range
    # We need to map text positions to pages
    full_text = ""
    page_starts = []  # character offset of each page start in full_text
    
    for i in range(len(doc)):
        page_starts.append(len(full_text))
        full_text += doc[i].get_text() + "\n"
    
    doc.close()
    
    # Find each question's start position in full_text
    q_starts = [m.start() for m in Q_START.finditer(full_text)]
    
    updated_questions = []
    
    for idx, q_info in enumerate(questions_info):
        q_start = q_starts[idx]
        q_end = q_starts[idx + 1] if idx + 1 < len(q_starts) else len(full_text)
        
        # Find which pages cover this question's range
        relevant_pages = set()
        for pi in range(len(page_starts) - 1):
            ps = page_starts[pi]
            pe = page_starts[pi + 1]
            # Check if any overlap between this page and the question's range
            if (ps <= q_start < pe) or (ps < q_end <= pe) or (q_start <= ps and pe <= q_end):
                relevant_pages.add(pi)
        
        # Also check the last page
        if page_starts[-1] <= q_end:
            relevant_pages.add(len(page_starts) - 1)
        
        # Extract images from these pages
        img_dir = os.path.join(simulado_dir, "imgs", simulado_id)
        os.makedirs(img_dir, exist_ok=True)
        
        images = extract_images_from_pdf(
            pdf_path, img_dir, simulado_id, 
            q_info["numero"], list(relevant_pages)
        )
        
        q_info["imagens"] = images
        updated_questions.append(q_info)
    
    return updated_questions


def process_simulado(pdf_path, edicao=1):
    """Process a simulado PDF and create the JSON data."""
    
    print(f"📄 Processando {edicao}º Simulado: {os.path.basename(pdf_path)}")
    
    simulado_id = f"{edicao}-simulado"
    
    # Output paths (relative to repo)
    repo_dir = os.path.expanduser("~/hermesmed-questoes")
    simulado_dir = os.path.join(repo_dir, "data", "simulados")
    os.makedirs(simulado_dir, exist_ok=True)
    os.makedirs(os.path.join(simulado_dir, "imgs", simulado_id), exist_ok=True)
    
    # Extract text
    print("  📖 Extraindo texto do PDF...")
    full_text = extract_question_text(pdf_path)
    
    # Split into questions
    print("  🔍 Separando questões...")
    question_blocks = split_questions(full_text)
    print(f"     → {len(question_blocks)} questões encontradas")
    
    questions_data = []
    
    for idx, block in enumerate(question_blocks):
        q_num = idx + 1
        
        # Parse header
        area, subarea, enunciado = parse_header(block)
        
        # Parse alternatives
        alternativas = parse_alternatives(block)
        
        # Get correct answer
        correta = get_correct_answer(block)
        
        # Get explanation
        explicacao = get_explanation(block)
        
        # Clean up enunciado - remove tab characters and normalize whitespace
        if enunciado:
            enunciado = re.sub(r'\t', ' ', enunciado)
            enunciado = re.sub(r'  +', ' ', enunciado)
            enunciado = enunciado.strip()
        
        # Clean alternatives
        clean_alts = {}
        for letter, text in alternativas.items():
            text = re.sub(r'\t', ' ', text)
            text = re.sub(r'  +', ' ', text)
            clean_alts[letter] = text.strip()
        
        # Clean explanation
        if explicacao:
            explicacao = re.sub(r'\t', ' ', explicacao)
            explicacao = re.sub(r'  +', ' ', explicacao)
            explicacao = explicacao.strip()
        
        q_id = f"s{edicao}-{q_num:03d}"
        if not area:
            area = "Geral"
        
        q_data = {
            "id": q_id,
            "numero": q_num,
            "area": area,
            "enunciado": enunciado,
            "alternativas": clean_alts,
            "correta": correta,
            "explicacao": explicacao,
            "fonte": f"ESTRATÉGIA MED 2026 ENAMED {edicao}ª",
        }
        
        questions_data.append(q_data)
        print(f"     ✓ Q{q_num:02d}: {area} - {'/'.join(clean_alts.keys())} alternativas", end="")
        if subarea:
            print(f" [{subarea}]", end="")
        print()
    
    # Assign images
    print("  🖼️ Extraindo imagens...")
    questions_data = assign_images_to_questions(
        pdf_path, simulado_dir, simulado_id, questions_data
    )
    
    img_total = sum(len(q.get("imagens", [])) for q in questions_data)
    print(f"     → {img_total} imagens extraídas")
    
    # Build final JSON
    simulado_json = {
        "simulado": f"{edicao}º Simulado Residência Médica - ENAMED",
        "data": "2026-02-01",  # approximate, will be refined
        "edicao": edicao,
        "total_questoes": len(questions_data),
        "questoes": questions_data
    }
    
    # Save JSON
    output_path = os.path.join(simulado_dir, f"{simulado_id}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(simulado_json, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ {edicao}º Simulado salvo em: {output_path}")
    print(f"   📊 {len(questions_data)} questões, {img_total} imagens")
    
    return simulado_json


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract questions from ENAMED simulado PDFs")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--edicao", type=int, default=1, help="Edition/number of the simulado")
    
    args = parser.parse_args()
    
    process_simulado(args.pdf_path, args.edicao)
