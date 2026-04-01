# aspects.py
# GTNH Thaumcraft Aspects 
# List provided by @Ducked on discord

PRIMALS = {"Aer", "Ignis", "Aqua", "Terra", "Ordo", "Perditio"}

all_aspects = [
    "Aer", "Ignis", "Aqua", "Terra", "Ordo", "Perditio",
    "Lux", "Motus", "Tempesta", "Vacuos", "Gelum", "Venenum",
    "Permutatio", "Potentia", "Vitreus", "Victus",
    "Fames", "Herba", "Limus", "Bestia", "Mortuus", "Sano",
    "Iter", "Metallum", "Praecantatio", "Primordium", "Radio", "Tempus",
    "Tenebrae", "Vinculum", "Volatus", "Alienis", "Arbor", "Astrum",
    "Auram", "Caelum", "Corpus", "Exanimis", "Gula", "Infernus",
    "Magneto", "Spiritus", "Superbia", "Vitium", "Cognitio", "Desidia",
    "Luxuria", "Sensus", "Aequalitas", "Humanus", "Invidia", "Stronito",
    "Vesania", "Gloria", "Instrumentum", "Lucrum", "Messis", "Perfodio",
    "Fabrico", "Machina", "Meto", "Nebrisum", "Pannus", "Telum",
    "Terminus", "Tutamen", "Electrum", "Ira", "Tabernus"
]

aspect_parents = {
    # Tier 1 (Primal + Primal)
    "Lux": ["Aer", "Ignis"],
    "Motus": ["Aer", "Ordo"],
    "Tempesta": ["Aer", "Aqua"],
    "Vacuos": ["Aer", "Perditio"],
    "Gelum": ["Perditio", "Ignis"],
    "Venenum": ["Perditio", "Aqua"],
    "Permutatio": ["Perditio", "Ordo"],
    "Potentia": ["Ordo", "Ignis"],
    "Vitreus": ["Ordo", "Terra"],
    "Victus": ["Terra", "Aqua"],
    
    # Tier 2
    "Fames": ["Victus", "Vacuos"],
    "Herba": ["Victus", "Terra"],
    "Limus": ["Victus", "Aqua"],
    "Bestia": ["Victus", "Motus"],
    "Mortuus": ["Victus", "Perditio"],
    "Sano": ["Victus", "Ordo"],
    "Iter": ["Motus", "Terra"],
    "Metallum": ["Terra", "Vitreus"],
    "Praecantatio": ["Vacuos", "Potentia"],
    "Primordium": ["Vacuos", "Motus"],
    "Radio": ["Lux", "Potentia"],
    "Tempus": ["Vacuos", "Ordo"],
    "Tenebrae": ["Vacuos", "Lux"],
    "Vinculum": ["Motus", "Perditio"],
    "Volatus": ["Aer", "Motus"],
    
    # Tier 3
    "Alienis": ["Vacuos", "Tenebrae"],
    "Arbor": ["Aer", "Herba"],
    "Astrum": ["Caelum", "Lux"],
    "Auram": ["Praecantatio", "Aer"],
    "Caelum": ["Vitreus", "Metallum"],
    "Corpus": ["Mortuus", "Bestia"],
    "Exanimis": ["Mortuus", "Motus"],
    "Gula": ["Fames", "Vacuos"],
    "Infernus": ["Ignis", "Praecantatio"],
    "Magneto": ["Metallum", "Iter"],
    "Spiritus": ["Mortuus", "Victus"],
    "Superbia": ["Volatus", "Vacuos"],
    "Vitium": ["Praecantatio", "Perditio"],
    
    # Tier 4
    "Cognitio": ["Ignis", "Spiritus"],
    "Desidia": ["Vinculum", "Spiritus"],
    "Luxuria": ["Corpus", "Fames"],
    "Sensus": ["Spiritus", "Aer"],
    
    # Tier 5
    "Aequalitas": ["Cognitio", "Ordo"],
    "Humanus": ["Bestia", "Cognitio"],
    "Invidia": ["Sensus", "Fames"],
    "Stronito": ["Perditio", "Cognitio"],
    "Vesania": ["Cognitio", "Vitium"],
    
    # Tier 6 (Humanus-based)
    "Gloria": ["Humanus", "Iter"],
    "Instrumentum": ["Humanus", "Ordo"],
    "Lucrum": ["Humanus", "Fames"],
    "Messis": ["Herba", "Humanus"],
    "Perfodio": ["Humanus", "Terra"],
    
    # Tier 7 (Instrumentum-based)
    "Fabrico": ["Humanus", "Instrumentum"],
    "Machina": ["Motus", "Instrumentum"],
    "Meto": ["Messis", "Instrumentum"],
    "Nebrisum": ["Perfodio", "Lucrum"],
    "Pannus": ["Instrumentum", "Bestia"],
    "Telum": ["Instrumentum", "Ignis"],
    "Tutamen": ["Instrumentum", "Terra"],
    
    # Tier 8
    "Electrum": ["Potentia", "Machina"],
    "Ira": ["Telum", "Ignis"],
    "Tabernus": ["Tutamen", "Iter"],
    "Terminus": ["Lucrum", "Alienis"],
}

COMBINED = set(aspect_parents.keys())


def get_children(aspect):
    return {asp for asp, parents in aspect_parents.items() if aspect in parents}


def get_all_connections(aspect):
    parents = set(aspect_parents.get(aspect, []))
    children = get_children(aspect)
    return parents | children


def validate_aspects():
    issues = []
    all_known = PRIMALS | COMBINED
    
    for asp, parents in aspect_parents.items():
        if len(parents) != 2:
            issues.append(f"'{asp}' has {len(parents)} parents (expected 2)")
        
        for p in parents:
            if p not in all_known:
                issues.append(f"'{asp}' has unknown parent '{p}'")
        
        if asp in parents:
            issues.append(f"'{asp}' lists itself as parent")
    
    return issues