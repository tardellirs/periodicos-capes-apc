"""
Add primary_area field to each journal by mapping main_discipline → CAPES area.

Grouped areas (user request):
  Engenharias I/II/III/IV → "Engenharias"
  Medicina I/II/III       → "Medicina"
  Ciências Biológicas I/II/III → "Ciências Biológicas"

Fallback for journals without main_discipline (IEEE, Royal Society):
  Use the best Qualis area (qualis_best stratum), picking the most frequent area
  among all Qualis classifications at that stratum.
"""

import json
import re
from pathlib import Path
from collections import Counter

OUT_DIR = Path(__file__).parent.parent / "data" / "01_processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PUBLISHER_FILES = [
    "acm.json", "ieee.json", "springer_nature.json",
    "elsevier.json", "wiley.json", "acs.json", "royal_society.json",
]

# ─── CAPES area mapping ───────────────────────────────────────────────────────
# Target names use grouped forms where applicable

DISCIPLINE_MAP: dict[str, str] = {
    # ── Computer Science ──────────────────────────────────────────────────────
    "computer science":                         "Computação",
    "computational intelligence":               "Computação",
    "computer science for engineering":         "Computação",
    "computer science  & information technology": "Computação",
    "computer science & information technology":"Computação",
    "security":                                 "Computação",
    "multimedia and hci":                       "Computação",
    "medical computing & informatics":          "Computação",
    "theory":                                   "Computação",
    "networks, communications and architecture": "Computação",

    # ── Chemistry ─────────────────────────────────────────────────────────────
    "chemistry":                                "Química",
    "analytical chemistry":                     "Química",
    "inorganic chemistry":                      "Química",
    "organic chemistry":                        "Química",
    "physical and theoretical chemistry":       "Química",
    "materials chemistry":                      "Química",
    "electrochemistry":                         "Química",
    "catalysis":                                "Química",
    "colloids":                                 "Química",
    "spectroscopy":                             "Química",
    "general chemistry":                        "Química",
    "medicinal chemistry":                      "Farmácia",

    # ── Engineering ───────────────────────────────────────────────────────────
    "engineering":                              "Engenharias",
    "mechanical engineering":                   "Engenharias",
    "civil and structural engineering":         "Engenharias",
    "chemical engineering, general":            "Engenharias",
    "chemical engineering: process and industrial": "Engenharias",
    "signal processing and control":            "Engenharias",
    "production engineering":                   "Engenharias",
    "computational engineering":                "Engenharias",
    "networks, communications and architecture":"Engenharias",
    "transportation":                           "Engenharias",
    "aerospace":                                "Engenharias",
    "alternative / renewable energy":           "Engenharias",
    "nuclear energy":                           "Engenharias",
    "ocean engineering":                        "Engenharias",
    "membranes and separation technology":      "Engenharias",
    "powder technology":                        "Engenharias",
    "microelectronics and hardware":            "Engenharias",
    "biomechanics":                             "Engenharias",
    "control systems technology":               "Engenharias",
    "general & introductory civil engineering & construction": "Engenharias",
    "general & introductory chemical engineering": "Engenharias",
    "optics":                                   "Engenharias",
    "sensors":                                  "Engenharias",
    "remote sensing":                           "Engenharias",
    "physical sciences & engineering":          "Engenharias",

    # ── Medicine ──────────────────────────────────────────────────────────────
    "medicine":                                 "Medicina",
    "medicine & public health":                 "Medicina",
    "oncology":                                 "Medicina",
    "endocrinology":                            "Medicina",
    "cardiology":                               "Medicina",
    "radiology/radiography":                    "Medicina",
    "neurology/neuropsychiatry":                "Medicina",
    "general & internal medicine":              "Medicina",
    "gastroenterology and hepatology":          "Medicina",
    "hematology":                               "Medicina",
    "infectious diseases":                      "Medicina",
    "obstetrics and gynecology":                "Medicina",
    "anesthesiology and pain medicine":         "Medicina",
    "medicine: research and experimental":      "Medicina",
    "general surgery":                          "Medicina",
    "thoracic surgery":                         "Medicina",
    "pediatrics and neonatology":               "Medicina",
    "ophthalmology/optometry":                  "Medicina",
    "urology":                                  "Medicina",
    "emergency medicine":                       "Medicina",
    "pathology":                                "Medicina",
    "otolaryngology":                           "Medicina",
    "arthritis & rheumatism":                   "Medicina",
    "respiratory medicine":                     "Medicina",
    "dermatology":                              "Medicina",
    "geriatrics and gerontology":               "Medicina",
    "nephrology":                               "Medicina",
    "plastic surgery":                          "Medicina",
    "vascular surgery":                         "Medicina",
    "transplantation":                          "Medicina",
    "allergy":                                  "Medicina",
    "pediatric surgery":                        "Medicina",
    "spine surgery":                            "Medicina",
    "colorectal surgery":                       "Medicina",
    "complementary medicine":                   "Medicina",
    "oral and maxillofacial surgery":           "Medicina",
    "radiation":                                "Medicina",
    "forensic & legal medicine":                "Medicina",
    "health and medical science - general":     "Medicina",
    "biomedicine":                              "Medicina",

    # ── Life Sciences / Biology ───────────────────────────────────────────────
    "life sciences":                            "Ciências Biológicas",
    "biochemistry":                             "Ciências Biológicas",
    "cell and developmental biology":           "Ciências Biológicas",
    "genetics and genomics":                    "Ciências Biológicas",
    "immunology":                               "Ciências Biológicas",
    "microbiology":                             "Ciências Biológicas",
    "mathematical and theoretical biology":     "Ciências Biológicas",
    "fungal biology":                           "Ciências Biológicas",
    "parasitology":                             "Ciências Biológicas",
    "virology":                                 "Ciências Biológicas",
    "zoology":                                  "Ciências Biológicas",

    # ── Mathematics ───────────────────────────────────────────────────────────
    "mathematics":                              "Matemática / Probabilidade e Estatística",
    "mathematics & statistics":                 "Matemática / Probabilidade e Estatística",
    "statistics":                               "Matemática / Probabilidade e Estatística",
    "smathematics":                             "Matemática / Probabilidade e Estatística",

    # ── Psychology ────────────────────────────────────────────────────────────
    "psychology":                               "Psicologia",
    "psychology - general":                     "Psicologia",
    "cognitive science":                        "Psicologia",
    "behavioral and cognitive neuroscience":    "Psicologia",
    "mental health":                            "Psicologia",
    "social & behavioral sciences":             "Psicologia",
    "applied psychology":                       "Psicologia",
    "developmental and educational psychology": "Psicologia",

    # ── Neuroscience ──────────────────────────────────────────────────────────
    "neuroscience":                             "Ciências Biológicas",

    # ── Materials ─────────────────────────────────────────────────────────────
    "materials science":                        "Materiais",
    "multidisciplinary materials":              "Materiais",
    "metals":                                   "Materiais",
    "polymers":                                 "Materiais",
    "composites":                               "Materiais",
    "ceramics":                                 "Materiais",
    "biomaterials":                             "Materiais",
    "functional materials":                     "Materiais",
    "energy materials":                         "Materiais",
    "metallurgy and minerals processing":       "Materiais",
    "surface science":                          "Materiais",

    # ── Earth Sciences / Geosciences ──────────────────────────────────────────
    "earth sciences":                           "Geociências",
    "geology":                                  "Geociências",
    "geochemistry & mineralogy":                "Geociências",
    "geophysics":                               "Geociências",
    "applied geosciences":                      "Geociências",
    "earth, space & environmental sciences":    "Geociências",
    "oceanography":                             "Geociências",
    "palaeontology":                            "Geociências",
    "atmospheric sciences":                     "Geociências",
    "quaternary science & geomorphology":       "Geociências",
    "planetary sciences":                       "Astronomia / Física",
    "earthquake":                               "Geociências",

    # ── Physics / Astronomy ───────────────────────────────────────────────────
    "physics":                                  "Astronomia / Física",
    "astronomy and astrophysics":               "Astronomia / Física",
    "condensed matter physics":                 "Astronomia / Física",
    "nuclear and high energy physics":          "Astronomia / Física",
    "nonlinear and statistical physics":        "Astronomia / Física",
    "astronomia / física":                      "Astronomia / Física",

    # ── Economics / Business ──────────────────────────────────────────────────
    "economics":                                "Economia",
    "finance":                                  "Economia",
    "energy: policy and economics":             "Economia",
    "business and management":                  "Administração Pública e de Empresas, Ciências Contábeis e Turismo",
    "business, economics, finance & accounting":"Administração Pública e de Empresas, Ciências Contábeis e Turismo",
    "accounting":                               "Administração Pública e de Empresas, Ciências Contábeis e Turismo",
    "marketing":                                "Administração Pública e de Empresas, Ciências Contábeis e Turismo",
    "decision sciences":                        "Administração Pública e de Empresas, Ciências Contábeis e Turismo",
    "tourism, hospitality, sport and leisure":  "Administração Pública e de Empresas, Ciências Contábeis e Turismo",

    # ── Social Sciences ───────────────────────────────────────────────────────
    "social sciences":                          "Interdisciplinar",
    "social science - general":                 "Interdisciplinar",
    "humanities":                               "Interdisciplinar",
    "cultural and media studies":               "Comunicação e Informação e Museologia",
    "library and information science":          "Comunicação e Informação e Museologia",
    "linguistics":                              "Linguística e Literatura",

    # ── Education ─────────────────────────────────────────────────────────────
    "education":                                "Educação",

    # ── Environment ───────────────────────────────────────────────────────────
    "environment":                              "Ciências Ambientais",
    "environmental science and technology":     "Ciências Ambientais",
    "environmental management":                 "Ciências Ambientais",
    "water resources":                          "Ciências Ambientais",
    "energy: sustainability and environment":   "Ciências Ambientais",
    "water resource management":                "Ciências Ambientais",

    # ── Pharmacy / Pharmacology ───────────────────────────────────────────────
    "pharmacology":                             "Farmácia",
    "pharmaceutical sciences":                  "Farmácia",
    "pharmacology and pharmacy":                "Farmácia",
    "pharmacy":                                 "Farmácia",
    "toxicology":                               "Farmácia",

    # ── Nursing / Health ─────────────────────────────────────────────────────
    "nursing":                                  "Enfermagem",
    "nursing, dentistry & healthcare":          "Saúde Coletiva",
    "health studies":                           "Saúde Coletiva",
    "health professions":                       "Saúde Coletiva",
    "social and economic medicine":             "Saúde Coletiva",
    "epidemiology/preventive medicine/public health": "Saúde Coletiva",

    # ── Dentistry ────────────────────────────────────────────────────────────
    "dentistry":                                "Odontologia",

    # ── Agriculture / Food ────────────────────────────────────────────────────
    "agriculture, aquaculture & food science":  "Ciências Agrárias I",
    "agriculture science, general":             "Ciências Agrárias I",
    "soil science":                             "Ciências Agrárias I",
    "forest science":                           "Ciências Agrárias I",
    "plant science":                            "Ciências Agrárias I",
    "food science":                             "Ciência de Alimentos",
    "nutrition":                                "Nutrição",

    # ── Biodiversity / Ecology ────────────────────────────────────────────────
    "ecology":                                  "Biodiversidade",
    "marine and freshwater biology":            "Biodiversidade",
    "entomology":                               "Biodiversidade",

    # ── Veterinary ────────────────────────────────────────────────────────────
    "veterinary science":                       "Medicina Veterinária",
    "veterinary medicine":                      "Medicina Veterinária",
    "animal science":                           "Zootecnia / Recursos Pesqueiros",

    # ── Other specific ────────────────────────────────────────────────────────
    "law":                                      "Direito",
    "law & criminology":                        "Direito",
    "criminology and criminal justice":         "Direito",
    "philosophy":                               "Filosofia",
    "religious studies":                        "Ciências da Religião e Teologia",
    "geography":                                "Geografia",
    "geography, planning and development":      "Geografia",
    "history":                                  "História",
    "political science and international relation": "Ciência Política e Relações Internacionais",
    "archaeology":                              "Antropologia / Arqueologia",
    "general & introductory anthropology":      "Antropologia / Arqueologia",
    "biotechnology":                            "Biotecnologia",
    "art & applied arts":                       "Artes",
    "rehabilitation":                           "Educação Física, Fisioterapia, Fonoaudiologia e Terapia Ocupacional",
    "sports sciences":                          "Educação Física, Fisioterapia, Fonoaudiologia e Terapia Ocupacional",
    # Fix remaining garbled Springer values (exact lowercase)
    "wliitfhe sspcireinngceers":                "Ciências Biológicas",
    "s#hne/da with springer":                  "Engenharias",
    "de snygsinteemersi nagnd the korean institute of electr": "Engenharias",
    "#snp/rianger":                            "Geociências",
    "e&a rttehc hscnioelnocgeys and the korean society of o": "Geociências",
    "dli fwei tshc isepnrciensger":            "Ciências Biológicas",
    "wcitohm sppurtinegr esrcience":           "Computação",
    "yg, ecoog-praupbhliyshed with springer":  "Geografia",
    "#n/a":                                    None,
    "energy science and technology":            "Engenharias",
    "energy":                                   "Engenharias",
    "psychiatry":                               "Medicina",
    "orthopaedics":                             "Medicina",
    # Garbled Springer OCR values → decoded meanings
    "esaprrtihn gsecriences":                   "Geociências",           # Earth Sciences
    "wcithhe mspisrtnryger":                    "Química",               # Chemistry with Springer
    "wcithhe mspisritnryger":                   "Química",
    "belinsghiende ewriitnhg springer":         "Engenharias",
    "wliitfhe sspcireenngceers":                "Ciências Biológicas",   # Life Sciences
    "wliitfhe sspcireenngceers":                "Ciências Biológicas",
    "eetyn,g cinoe-peuribnlgished with springer": "Engenharias",
    "nEdn vEiarortnhm Seynsttem Science of the University o".lower(): "Ciências Ambientais",
    "belnisghineede wriinthg springer":         "Engenharias",
    "bclihsheemdi swtriyth springer":           "Química",              # Chemistry with Springer
    "ym, caoth-peumbalitsihcsed with springer": "Matemática / Probabilidade e Estatística",
    "iecnagl i&ne sepraincge sciences, co-published with sp": "Engenharias",
    "de snygsinteemesi nagnd the korean institute of electr": "Engenharias",
    "ie snygsinteemesi nagnd the korean institute of electr": "Engenharias",
    "iennegeirninege,r icnog-published with springer":  "Engenharias",
    "teionngi,n ceoe-rpiunbglished with springer":      "Engenharias",
    "leisnhgeinde weritinhg springer":          "Engenharias",
    "ecaor-tphu sbcliisehnecde swith springer": "Geociências",          # Earth Sciences
    "ol-ipfeu bslcisiehnecde wsith springer":   "Ciências Biológicas",  # Life Sciences
    "gspeorignrgaepry":                         "Geografia",
    "gspeorignrgaeprhy":                        "Geografia",
    "oe-npguibnleisehreindg with springer":     "Engenharias",
    "c-phuebmliisshtreyd with springer":        "Química",
    "e&a rteh hscnioenogelycs and the korean society of o": "Engenharias",
    "e&a rteh hscnioelocgeys and the korean society of o":  "Engenharias",
    "dli fwei tshc iseprnciensger":             "Ciências Biológicas",
    "wcitohm sppurtinger esrcience":            "Computação",
    "sehnevdir ownitmhe snptringer":            "Ciências Ambientais",
    "yg, ecoog-raupbhliyshed with springer":    "Geografia",
    "yg, ecoog-rapubhliyshed with springer":    "Geografia",
}


# ─── Title-based overrides (for journals without main_discipline) ─────────────
TITLE_MAP: dict[str, str] = {
    # Springer Nature (garbled main_discipline)
    "acta geodaetica et geophysica":                    "Geociências",
    "acta mathematica hungarica":                       "Matemática / Probabilidade e Estatística",
    "acta oceanologica sinica":                         "Geociências",
    "advances in manufacturing":                        "Engenharias",
    "analysis mathematica":                             "Matemática / Probabilidade e Estatística",
    "applied geophysics":                               "Geociências",
    "archives of pharmacal research":                   "Farmácia",
    "asia-pacific journal of atmospheric sciences":     "Geociências",
    "astrodynamics":                                    "Astronomia / Física",
    "biochip journal":                                  "Biotecnologia",
    "biologia futura":                                  "Ciências Biológicas",
    "building simulation":                              "Engenharias",
    "chinese geographical science":                     "Geografia",
    "community ecology":                                "Biodiversidade",
    "current medical science":                          "Medicina",
    "current robotics reports":                         "Computação",
    "current treatment options in infectious diseases": "Medicina",
    "current treatment options in rheumatology":        "Medicina",
    "earthquake engineering and engineering vibration": "Engenharias",
    "food science and biotechnology":                   "Ciência de Alimentos",
    "frontiers in energy":                              "Engenharias",
    "frontiers of computer science":                    "Computação",
    "frontiers of earth science":                       "Geociências",
    "frontiers of environmental science & engineering": "Ciências Ambientais",
    "frontiers of materials science":                   "Materiais",
    "frontiers of mechanical engineering":              "Engenharias",
    "frontiers of structural and civil engineering":    "Engenharias",
    "genes & genomics":                                 "Ciências Biológicas",
    "international journal of automotive technology":   "Engenharias",
    "international journal of precision engineering and manufacturing-green": "Engenharias",
    "journal of mechanical science and technology":     "Engenharias",
    "journal of meteorological research":               "Geociências",
    "journal of ocean university of china":             "Geociências",
    "journal of oceanology and limnology":              "Geociências",
    "journal of shanghai jiaotong university (science)": "Engenharias",
    "journal of the korean physical society":           "Astronomia / Física",
    "journal of zhejiang university-science a":         "Engenharias",
    "journal of zhejiang university-science b":         "Ciências Biológicas",
    "machine intelligence research":                    "Computação",
    "molecular & cellular toxicology":                  "Farmácia",
    "neohelicon":                                       "Linguística e Literatura",
    "periodica mathematica hungarica":                  "Matemática / Probabilidade e Estatística",
    "power technology and engineering":                 "Engenharias",
    "science china chemistry":                          "Química",
    "science china earth sciences":                     "Geociências",
    "science china information sciences":               "Computação",
    "science china materials":                          "Materiais",
    "science china physics, mechanics & astronomy":     "Astronomia / Física",
    "science china technological sciences":             "Engenharias",
    "smart grids and sustainable energy":               "Engenharias",
    "toxicology and environmental health sciences":     "Ciências Ambientais",
    # Elsevier
    "journal of substance use and addiction treatment": "Saúde Coletiva",
    "marine geoscience and energy resources":           "Geociências",
    "mental health & prevention":                       "Psicologia",
    "neuropsychiatrie de l'enfance et de l'adolescence": "Medicina",
    "operative techniques in orthopaedics":             "Medicina",
    "seminars in arthroplasty: jses":                   "Medicina",
    "spanish journal of psychiatry and mental health":  "Psicologia",
    "vascular diseases":                                "Medicina",
    # Royal Society
    "philosophical transactions a":    "Astronomia / Física",
    "philosophical transactions b":    "Ciências Biológicas",
    "proceedings a":                   "Astronomia / Física",
    "proceedings b":                   "Ciências Biológicas",
    "biology letters":                 "Ciências Biológicas",
    "interface":                       "Engenharias",
    "interface focus":                 "Ciências Biológicas",
    "open biology":                    "Ciências Biológicas",
    "royal society open science":      "Interdisciplinar",
    "notes and records":               "História",
    # Wiley
    "advances in digestive medicine":                   "Medicina",
    "chemkon":                                          "Química",
    "current protocols in bioinformatics":              "Computação",
    "current protocols in cell biology":                "Ciências Biológicas",
    "current protocols in cytometry":                   "Ciências Biológicas",
    "current protocols in essential laboratory techniques": "Ciências Biológicas",
    "current protocols in human genetics":              "Ciências Biológicas",
    "current protocols in immunology":                  "Ciências Biológicas",
    "current protocols in microbiology":                "Ciências Biológicas",
    "current protocols in molecular biology":           "Ciências Biológicas",
    "current protocols in mouse biology":               "Ciências Biológicas",
    "current protocols in neuroscience":                "Ciências Biológicas",
    "current protocols in nucleic acid chemistry":      "Química",
    "current protocols in pharmacology":                "Farmácia",
    "current protocols in plant biology":               "Ciências Biológicas",
    "current protocols in protein science":             "Ciências Biológicas",
    "current protocols in stem cell biology":           "Ciências Biológicas",
    "current protocols in toxicology":                  "Farmácia",
    "philosophical perspectives":                       "Filosofia",
    "sociology lens (former isbn  14676443)":           "Sociologia",
    "alcohol: clinical and experimental research  (former isbn 15300277)": "Medicina",
    "current protocols":                                "Ciências Biológicas",
    "current protocols in chemical biology":            "Química",
    "journal of experimental zoology part a: ecological and intergrative physiology (former isbn 19325231)": "Ciências Biológicas",
}


def map_discipline(raw: str | None) -> str | None:
    """Map a raw main_discipline string to a CAPES area name."""
    if not raw:
        return None
    key = raw.strip().lower()
    if key in DISCIPLINE_MAP:
        return DISCIPLINE_MAP[key]

    # Fuzzy fallback: check if any keyword appears in the discipline string
    KEYWORDS = [
        ("computer",       "Computação"),
        ("software",       "Computação"),
        ("information technology", "Computação"),
        ("engineer",       "Engenharias"),
        ("mechanic",       "Engenharias"),
        ("electric",       "Engenharias"),
        ("chemical eng",   "Engenharias"),
        ("civil eng",      "Engenharias"),
        ("physic",         "Astronomia / Física"),
        ("astrono",        "Astronomia / Física"),
        ("math",           "Matemática / Probabilidade e Estatística"),
        ("statistic",      "Matemática / Probabilidade e Estatística"),
        ("chemi",          "Química"),
        ("medic",          "Medicina"),
        ("surgery",        "Medicina"),
        ("oncol",          "Medicina"),
        ("cardio",         "Medicina"),
        ("pharmac",        "Farmácia"),
        ("drug",           "Farmácia"),
        ("nursi",          "Enfermagem"),
        ("psycho",         "Psicologia"),
        ("biolog",         "Ciências Biológicas"),
        ("biochem",        "Ciências Biológicas"),
        ("genetic",        "Ciências Biológicas"),
        ("ecolog",         "Biodiversidade"),
        ("environ",        "Ciências Ambientais"),
        ("earth sci",      "Geociências"),
        ("geologi",        "Geociências"),
        ("geophysi",       "Geociências"),
        ("geograph",       "Geografia"),
        ("econom",         "Economia"),
        ("business",       "Administração Pública e de Empresas, Ciências Contábeis e Turismo"),
        ("management",     "Administração Pública e de Empresas, Ciências Contábeis e Turismo"),
        ("social sci",     "Interdisciplinar"),
        ("material",       "Materiais"),
        ("food",           "Ciência de Alimentos"),
        ("nutri",          "Nutrição"),
        ("dent",           "Odontologia"),
        ("veterin",        "Medicina Veterinária"),
        ("agricultur",     "Ciências Agrárias I"),
        ("biotechn",       "Biotecnologia"),
        ("law",            "Direito"),
        ("legal",          "Direito"),
        ("art",            "Artes"),
        ("philosoph",      "Filosofia"),
        ("histor",         "História"),
        ("linguist",       "Linguística e Literatura"),
        ("education",      "Educação"),
    ]
    for kw, area in KEYWORDS:
        if kw in key:
            return area

    return None


_AREA_GROUP = [
    # Order matters: longer/more-specific first to avoid substring bugs
    (re.compile(r"\bENGENHARIAS IV\b"),         "Engenharias"),
    (re.compile(r"\bENGENHARIAS III\b"),        "Engenharias"),
    (re.compile(r"\bENGENHARIAS II\b"),         "Engenharias"),
    (re.compile(r"\bENGENHARIAS I\b"),          "Engenharias"),
    (re.compile(r"\bMEDICINA III\b"),           "Medicina"),
    (re.compile(r"\bMEDICINA II\b"),            "Medicina"),
    (re.compile(r"\bMEDICINA I\b"),             "Medicina"),
    (re.compile(r"\bCIÊNCIAS BIOLÓGICAS III\b"),"Ciências Biológicas"),
    (re.compile(r"\bCIÊNCIAS BIOLÓGICAS II\b"), "Ciências Biológicas"),
    (re.compile(r"\bCIÊNCIAS BIOLÓGICAS I\b"),  "Ciências Biológicas"),
]

_AREA_TITLE_CASE = {
    "ADMINISTRAÇÃO PÚBLICA E DE EMPRESAS, CIÊNCIAS CONTÁBEIS E TURISMO":
        "Administração Pública e de Empresas, Ciências Contábeis e Turismo",
    "ANTROPOLOGIA / ARQUEOLOGIA":               "Antropologia / Arqueologia",
    "ARQUITETURA, URBANISMO E DESIGN":          "Arquitetura, Urbanismo e Design",
    "ARTES":                                    "Artes",
    "ASTRONOMIA / FÍSICA":                      "Astronomia / Física",
    "BIODIVERSIDADE":                           "Biodiversidade",
    "BIOTECNOLOGIA":                            "Biotecnologia",
    "CIÊNCIA DE ALIMENTOS":                     "Ciência de Alimentos",
    "CIÊNCIA POLÍTICA E RELAÇÕES INTERNACIONAIS": "Ciência Política e Relações Internacionais",
    "CIÊNCIAS AGRÁRIAS I":                      "Ciências Agrárias I",
    "CIÊNCIAS AMBIENTAIS":                      "Ciências Ambientais",
    "COMPUTAÇÃO":                               "Computação",
    "COMUNICAÇÃO E INFORMAÇÃO E MUSEOLOGIA":    "Comunicação e Informação e Museologia",
    "DIREITO":                                  "Direito",
    "ECONOMIA":                                 "Economia",
    "EDUCAÇÃO":                                 "Educação",
    "EDUCAÇÃO FÍSICA, FISIOTERAPIA, FONOAUDIOLOGIA E TERAPIA OCUPACIONAL":
        "Educação Física, Fisioterapia, Fonoaudiologia e Terapia Ocupacional",
    "ENFERMAGEM":                               "Enfermagem",
    "ENSINO":                                   "Ensino",
    "FARMÁCIA":                                 "Farmácia",
    "FILOSOFIA":                                "Filosofia",
    "GEOCIÊNCIAS":                              "Geociências",
    "GEOGRAFIA":                                "Geografia",
    "HISTÓRIA":                                 "História",
    "INTERDISCIPLINAR":                         "Interdisciplinar",
    "LINGUíSTICA E LITERATURA":                 "Linguística e Literatura",
    "MATEMÁTICA / PROBABILIDADE E ESTATÍSTICA": "Matemática / Probabilidade e Estatística",
    "MATERIAIS":                                "Materiais",
    "MEDICINA VETERINÁRIA":                     "Medicina Veterinária",
    "NUTRIÇÃO":                                 "Nutrição",
    "ODONTOLOGIA":                              "Odontologia",
    "PLANEJAMENTO URBANO E REGIONAL / DEMOGRAFIA": "Planejamento Urbano e Regional / Demografia",
    "PSICOLOGIA":                               "Psicologia",
    "QUÍMICA":                                  "Química",
    "SAÚDE COLETIVA":                           "Saúde Coletiva",
    "SERVIÇO SOCIAL":                           "Serviço Social",
    "SOCIOLOGIA":                               "Sociologia",
    "ZOOTECNIA / RECURSOS PESQUEIROS":          "Zootecnia / Recursos Pesqueiros",
    "CIÊNCIAS DA RELIGIÃO E TEOLOGIA":          "Ciências da Religião e Teologia",
    "CIÊNCIAS E HUMANIDADES PARA A EDUCAÇÃO BÁSICA": "Ciências e Humanidades para a Educação Básica",
}


def normalize_area(raw: str) -> str:
    """Normalize a CAPES area string: group numbered variants, apply title case."""
    area = raw.strip()
    for pattern, grouped in _AREA_GROUP:
        if pattern.search(area):
            return grouped
    return _AREA_TITLE_CASE.get(area, area.title() if area.isupper() else area)


def qualis_best_area(journal: dict) -> str | None:
    """Fallback: use the area with the best Qualis stratum.
    Since most journals have the same stratum across all areas, this is
    only meaningful when one area has a strictly better stratum.
    If all strata are tied (most common case), returns None — the caller
    should prefer a title-based mapping instead.
    """
    qualis = journal.get("qualis", [])
    best_strat = journal.get("qualis_best")
    if not qualis or not best_strat:
        return None

    strata_order = ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "C"]
    best_areas = [q["area"] for q in qualis if q["estrato"] == best_strat]

    # If ALL areas share the same stratum, fallback is meaningless → return None
    all_strata = {q["estrato"] for q in qualis}
    if len(all_strata) == 1:
        return None

    # There IS a strictly-best stratum — use it
    if not best_areas:
        return None

    counts = Counter(best_areas)
    max_count = max(counts.values())
    candidates = sorted(a for a, c in counts.items() if c == max_count)
    return normalize_area(candidates[0])


def main():
    all_journals_flat = []
    stats = {"mapped": 0, "qualis_fallback": 0, "none": 0}

    for fname in PUBLISHER_FILES:
        fpath = OUT_DIR / fname
        if not fpath.exists():
            continue
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)

        publisher = data.get("publisher", "")

        for j in data["journals"]:
            disc = j.get("main_discipline")
            area = map_discipline(disc)

            if area:
                stats["mapped"] += 1
            else:
                # Try title-based lookup (Springer/Wiley/Elsevier edge cases)
                title_key = (j.get("title") or "").strip().lower()
                area = TITLE_MAP.get(title_key)
                if area:
                    stats["mapped"] += 1
                elif publisher == "IEEE":
                    # IEEE spans Engenharias + Computação.
                    # Use Qualis areas: prefer Computação if present, else Engenharias.
                    qualis_areas = {q["area"] for q in j.get("qualis", [])}
                    area = "Computação" if "COMPUTAÇÃO" in qualis_areas else "Engenharias"
                    stats["mapped"] += 1
                else:
                    area = qualis_best_area(j)
                    if area:
                        stats["qualis_fallback"] += 1
                    else:
                        stats["none"] += 1

            j["primary_area"] = area

            j_copy = dict(j)
            j_copy.pop("participating_institutions", None)
            all_journals_flat.append(j_copy)

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # Save combined
    out_path = OUT_DIR / "all_journals.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_journals_flat, f, ensure_ascii=False, indent=2)

    total = sum(stats.values())
    print(f"primary_area assigned: {total} journals")
    print(f"  Via main_discipline:  {stats['mapped']} ({100*stats['mapped']//total}%)")
    print(f"  Via Qualis fallback:  {stats['qualis_fallback']} ({100*stats['qualis_fallback']//total}%)")
    print(f"  Sem área:             {stats['none']}")

    # Distribution
    from collections import Counter
    areas = Counter(j["primary_area"] for j in all_journals_flat if j.get("primary_area"))
    print("\nTop 20 primary_areas:")
    for area, n in areas.most_common(20):
        print(f"  {n:5d}  {area}")

    # Unmapped disciplines
    no_area = [(j["publisher"], j.get("main_discipline"), j["title"])
               for j in all_journals_flat if not j.get("primary_area")]
    if no_area:
        print(f"\nSem primary_area ({len(no_area)}):")
        for pub, disc, title in no_area[:10]:
            print(f"  [{pub}] {disc!r} — {title}")


if __name__ == "__main__":
    main()
