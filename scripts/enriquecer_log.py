#!/usr/bin/env python3
"""
Enriquece o estado.json com campos extras no log:
- assunto: nome do tópico (da subarea ou mapeamento específico)
- tipo: "first_contact" ou "revisao" (se parear com o revisao_espacada.json)

Uso: python3 scripts/enriquecer_log.py
"""

import json
import sys
import os
from pathlib import Path

CAMINHO_ESTADO = Path(__file__).parent.parent / "data" / "progresso" / "estado.json"
CAMINHO_REVISAO = Path.home() / ".hermes" / "revisao_espacada.json"

def carregar_revisao():
    """Tenta carregar o revisao_espacada.json para mapear assuntos."""
    if CAMINHO_REVISAO.exists():
        with open(CAMINHO_REVISAO) as f:
            return json.load(f)
    return {}

def enriquecer():
    with open(CAMINHO_ESTADO) as f:
        data = json.load(f)

    revisao = carregar_revisao()
    assuntos_revisao = revisao.get("assuntos", [])
    
    # Mapa: nome do assunto (normalizado) → info do revisao_espacada
    mapa_assuntos = {}
    for a in assuntos_revisao:
        nome_norm = a.get("nome", "").strip().lower()
        if nome_norm:
            mapa_assuntos[nome_norm] = a
    
    # Mapa manual de IDs de questão → assunto específico (quando a subarea é genérica)
    # Formato: "s{simulado}-{numero}" → "nome do assunto"
    mapa_ids = {
        # Simulado 14 — mapeamento do catálogo
        "s14-009": "Cirurgia Torácica",
        "s14-011": "Epidemiologia",
    }

    log = data.get("log", [])
    modificados = 0

    for entry in log:
        qid = entry.get("id", "")
        subarea = entry.get("subarea", "")
        area = entry.get("area", "")
        
        # 1. Determinar o assunto
        # Prioridade: mapeamento por ID > subarea
        if qid in mapa_ids:
            assunto = mapa_ids[qid]
        elif subarea:
            assunto = subarea
        else:
            assunto = "?"
        
        # 2. Tentar cruzar com revisao_espacada pra saber se é first_contact
        tipo = entry.get("tipo", "livre")
        if tipo == "livre" and assuntos_revisao:
            # Verificar se o assunto está na revisão espaçada
            assunto_norm = assunto.strip().lower()
            for a in assuntos_revisao:
                a_nome = a.get("nome", "").strip().lower()
                # Match parcial: se o nome do assunto contém a subarea ou vice-versa
                if assunto_norm in a_nome or a_nome in assunto_norm:
                    if a.get("status") == "first_contact":
                        tipo = "first_contact"
                    else:
                        tipo = "revisao"
                    break
        
        # 3. Atualizar campos se mudou
        if entry.get("assunto") != assunto or entry.get("tipo") != tipo:
            entry["assunto"] = assunto
            entry["tipo"] = tipo
            modificados += 1
    
    if modificados > 0:
        with open(CAMINHO_ESTADO, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ {modificados} logs enriquecidos — campo 'assunto' e 'tipo' adicionados.")
    else:
        print("📭 Nenhum log precisou ser modificado.")
    
    # Mostrar resumo
    print()
    mostrar_resumo(data)

def mostrar_resumo(data):
    log = data.get("log", [])
    from datetime import datetime, timedelta, timezone
    brt = timezone(timedelta(hours=-3))
    hoje = datetime.now(brt).strftime("%Y-%m-%d")
    
    entradas_hoje = [e for e in log if e.get("timestamp","").startswith(hoje)]
    print(f"📅 Logs de hoje ({hoje}): {len(entradas_hoje)}")
    for e in entradas_hoje:
        acerto = "✅" if e.get("acertou") else "❌"
        assunto = e.get("assunto", "?")
        subarea = e.get("subarea", "")
        tipo = e.get("tipo", "📖")
        tipo_emoji = "🔵" if tipo == "first_contact" else ("🔄" if tipo == "revisao" else "📖")
        print(f"  {acerto} {tipo_emoji} {assunto} [{e.get('area','')}] — {e.get('id','')}")

if __name__ == "__main__":
    enriquecer()
