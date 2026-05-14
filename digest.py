#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import feedparser
import google.generativeai as genai
import datetime
from time import sleep, struct_time
from calendar import timegm

# ──────────────────────────────────────────────────────────────────────
# CONFIGURATION — Edit this section to match your interests and feeds
# ──────────────────────────────────────────────────────────────────────

DAYS_BACK = 8  # How far back to look for papers
RELEVANCE_THRESHOLD = 2  # Minimum score to include (papers below this are noise)
API_SLEEP = 2.5  # Seconds between API calls (respect free-tier rate limits)

# Keyword pre-filter: a paper must contain at least one of these words
# (case-insensitive) in its title OR abstract to be sent to Gemini.
# This dramatically reduces API calls on broad feeds like Nature or Science.
# Set to an empty list to disable and send everything to Gemini.
KEYWORDS = []
#Keywords currently disabled, as computational gain is not huge, but may miss out on important papers
'''
KEYWORDS = [
    # ── Durable general terms (future-proof) ──
    # These catch new methods regardless of their brand name
    "protein", "peptide",
    "biomolecular", "biophysical",
    "structure prediction", "structure evaluation", "structural modeling",
    "quality assessment", "scoring function",
    "protein design", "binder design", "de novo design", "sequence design",
    "inverse folding", "fold prediction", "protein engineering",
    "protein-protein interaction", "binding interface", "interface design",
    "peptide binder", "peptide design", "peptide-protein",
    "protein-ligand", "ligand binding",
    "molecular dynamics", "force field", "coarse-grained",
    "directed evolution", "fitness landscape",
    "diffusion model", "generative model", "foundation model",
    "deep learning", "machine learning", "neural network",
    "language model", "protein function",
    "all-atom", "biomolecular complex",
    "cryo-em", "cryo-electron", "x-ray crystallography",
    "enzyme design", "catalytic", "active site",
    # Structural biology metrics & terms
    "plddt", "iptm", "ptm score", "predicted aligned error",
    "lddt", "dockq", "rmsd",
    "backbone", "side-chain", "tertiary structure", "quaternary structure",
    "folding", "misfolding", "conformational", "binding affinity",
    "fold-switching", "multi-state",
    "docking", "homology model", "contact map", "distance map",
    "sequence-structure", "structure-function",
    "high-throughput screening", "experimental characterization",
    # GPCRs & signaling
    "gpcr", "g protein-coupled", "g-protein-coupled", "coupled receptor",
    "receptor activation", "receptor signaling", "receptor signalling",
    "allosteric", "allostery",
    "arrestin", "g protein coupling", "signal transduction",
    "transmembrane", "membrane receptor",
    # Chemokine / specific receptors
    "chemokine", "cxcr", "cxcl", "endothelin",
    "chemotaxis", "chemotactic",
    # Molecular biology / library methods
    "golden gate", "gene synthesis", "oligopool", "oligo pool",
    "gene library", "dna assembly", "dna library",
    "deep mutational scanning", "mutational scanning", "variant library",
    "recombinase",
    # Synthetic biology
    "synthetic receptor", "synthetic cell", "car-t", "car t cell",
    "chimeric receptor", "synnotch",

    # ── Ephemeral tool names (helpful now, may become stale) ──
    # Keep these but don't rely on them — the general terms above
    # will catch the next generation of tools too
    "alphafold", "boltz", "esmfold", "rosettafold", "openfold",
    "rosetta", "proteinmpnn", "rfdiffusion", "rf diffusion", "chroma",
    "colabdesign", "colabfold", "ligandmpnn", "frameflow", "bindcraft",
    "binderflow", "pxdesign", "dynamicmpnn", "atomworks",
]
'''

# Your scientific profile — be specific, the LLM uses this verbatim.
INTERESTS = """
I am a PhD student working in computational protein design with a focus on
G protein-coupled receptors (GPCRs), chemokine receptor signaling, and
allosteric mechanism engineering.

CRITICAL INTEREST (score 9-10):
- GPCR structure, activation mechanisms, and signaling (especially class A GPCRs)
- Computational design of GPCRs and receptor-peptide signaling complexes
- GPCR allosteric modulation and signal transduction design
- Chemokine receptors (CXCR4, CXCL12) — structure, modulation, oligomerization
- AI/ML-driven protein design methods and benchmarks
- Directed evolution of GPCRs in mammalian or yeast systems

HIGH INTEREST (score 7-8):
- De novo protein binder design (BindCraft, RFdiffusion, PXDesign, ProteinMPNN)
- Protein-peptide binding prediction and affinity ranking
- Multi-state / dynamic protein design and allosteric switches
- Deep mutational scanning of receptors and protein interfaces
- Endothelin receptor structure and activation
- DNA assembly methods (Golden Gate, gene library construction from oligopools)
- Structural biology of receptor-ligand complexes (cryo-EM, crystallography)
- Protein language models for function prediction and design

MODERATE INTEREST (score 5-6):
- General protein structure prediction improvements (AlphaFold, Boltz, scoring metrics)
- Peptide binder design with language models or contrastive learning
- GPCR allostery reviews and general signaling pathway analysis
- Functional genomics platforms and high-throughput variant characterization
- Enzyme design and catalysis
- Molecular dynamics and enhanced sampling methods
- Orthogonal protein-protein interaction design

LOW INTEREST (score 2-4):
- Synthetic cell engineering and synNotch receptors
- CAR-T cell therapy reviews
- Chemotaxis mechanisms (unless tied to receptor design)
- General cancer biology and clinical oncology
- Drug formulation, delivery, pharmacology
"""

# RSS feeds to monitor.
# Add or remove feeds as needed. Each entry is (label, url).
FEEDS = [
    # ── bioRxiv ──
    ("bioRxiv: Cell Biology", "http://hwmaint.biorxiv.highwire.org/cgi/collection/rss?coll_alias=cell_biology"),
    ("bioRxiv: Biophysics", "https://connect.biorxiv.org/biorxiv_xml.php?subject=biophysics"),
    ("bioRxiv: Molecular Biology", "https://connect.biorxiv.org/biorxiv_xml.php?subject=molecular_biology"),
    ("bioRxiv: Biochemistry", "http://connect.biorxiv.org/biorxiv_xml.php?subject=biochemistry"),
    ("bioRxiv: Synthetic Biology", "http://connect.biorxiv.org/biorxiv_xml.php?subject=synthetic_biology"),
    ("bioRxiv: Bioengineering", "http://connect.biorxiv.org/biorxiv_xml.php?subject=bioengineering"),
    ("bioRxiv: Cancer Biology", "https://connect.biorxiv.org/biorxiv_xml.php?subject=cancer_biology"),
    ("bioRxiv: Immunology", "http://connect.biorxiv.org/biorxiv_xml.php?subject=immunology"),

    # ── Science / AAAS ──
    ("Science", "http://www.sciencemag.org/rss/current.xml"),
    ("Science Advances", "http://advances.sciencemag.org/rss/current.xml"),
    ("Science Translational Medicine", "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=stm"),
    ("Science Signaling", "http://stke.sciencemag.org/rss/current.xml"),

    # ── Nature ──
    ("Nature", "http://www.nature.com/nature/current_issue/rss"),
    ("Nature Methods", "http://www.nature.com/nmeth/current_issue/rss"),
    ("Nature Biotechnology", "http://www.nature.com/nbt/current_issue/rss/"),
    ("Nature Chemical Biology", "http://www.nature.com/nchembio/current_issue/rss/"),
    ("Nature Chemistry", "http://www.nature.com/nchem/journal/vaop/ncurrent/rss.rdf"),
    ("Nature Structural & Molecular Biology", "https://www.nature.com/nsmb.rss"),
    ("Nature Communications", "http://feeds.nature.com/ncomms/rss/current"),
    ("Nature Cell Biology", "http://www.nature.com/ncb/current_issue/rss"),
    ("Nature Genetics", "http://www.nature.com/ng/current_issue/rss/"),
    ("Nature Medicine", "http://feeds.nature.com/nm/rss/current"),
    ("Nature Immunology", "http://feeds.nature.com/ni/rss/current"),
    ("Nature Biomedical Engineering", "http://feeds.nature.com/natbiomedeng/rss/current"),
    ("Nature Protocols", "http://feeds.nature.com/nprot/rss/current"),
    ("Nature Reviews Drug Discovery", "http://feeds.nature.com/nrd/rss/current"),
    ("Nature Reviews Cancer", "http://feeds.nature.com/nrc/rss/current"),
    ("Nature Reviews Immunology", "http://feeds.nature.com/nri/rss/current"),
    ("Nature Reviews Molecular Cell Biology", "http://www.nature.com/nrm/current_issue/rss"),

    # ── Nature subject feeds ──
    ("Nature subjects: Protein Design", "http://www.nature.com/subjects/protein-design.rss"),
    ("Nature subjects: Structural Biology", "https://www.nature.com/subjects/structural-biology.rss"),
    ("Nature subjects: Computational Biology", "http://www.nature.com/subjects/computational-biology-and-bioinformatics.rss"),
    ("Nature subjects: Biochemistry", "http://www.nature.com/subjects/biochemistry.rss"),
    ("Nature subjects: Biophysics", "http://www.nature.com/subjects/biophysics.rss"),
    ("Nature subjects: Chemical Biology", "https://www.nature.com/subjects/chemical-biology.rss"),

    # ── Cell Press ──
    ("Cell (current)", "http://www.cell.com/cell/current.rss"),
    ("Cell (in press)", "http://www.cell.com/cell/inpress.rss"),
    ("Cell Chemical Biology", "http://www.cell.com/chemistry-biology/current.rss"),
    ("Cell Research", "http://feeds.nature.com/cr/rss/current"),
    ("Molecular Cell", "http://rss.sciencedirect.com/publication/science/10972765"),
    ("Biophysical Journal", "http://www.cell.com/biophysj/current.rss"),
    ("Trends in Biochemical Sciences", "http://www.cell.com/trends/biochemical-sciences/current.rss"),
    ("Structure", "http://rss.sciencedirect.com/publication/science/09692126"),

    # ── PNAS ──
    ("PNAS", "http://www.pnas.org/rss/current.xml"),
    ("PNAS: Biophysics & Computational Biology", "http://www.pnas.org/rss/Biophysics_and_Computational_Biology.xml"),

    # ── PLOS ──
    ("PLOS Biology", "http://biology.plosjournals.org/perlserv/?request=get-rss&issn=1545-7885&type=new-articles"),
    ("PLOS Computational Biology", "http://www.ploscompbiol.org/article/feed"),

    # ── ScienceDirect / Elsevier ──
    ("J. Molecular Biology", "http://rss.sciencedirect.com/publication/science/00222836"),
    ("J. Structural Biology", "http://rss.sciencedirect.com/publication/science/10478477"),
    ("Current Opinion in Structural Biology", "http://rss.sciencedirect.com/publication/science/0959440X"),
    ("Current Opinion in Chemical Biology", "http://rss.sciencedirect.com/publication/science/13675931"),

    # ── Annual Reviews ──
    ("Annual Review of Biochemistry", "http://www.annualreviews.org/action/showFeed?ui=45mu4&mi=3fndc3&ai=se&jc=biochem&type=etoc&feed=rss"),
    ("Annual Review of Biophysics", "http://www.annualreviews.org/action/showFeed?ui=45mu4&mi=3fndc3&ai=s7&jc=biophys&type=etoc&feed=rss"),
    ("Annual Review of Chem & Biomolecular Eng", "http://www.annualreviews.org/action/showFeed?ui=45mu4&mi=3fndc3&ai=68uv&jc=chembioeng&type=etoc&feed=rss"),

    # ── Other ──
    ("Cellular & Molecular Immunology", "http://feeds.nature.com/cmi/rss/current"),
]

# ──────────────────────────────────────────────────────────────────────
# IMPLEMENTATION
# ──────────────────────────────────────────────────────────────────────

def init_gemini():
    """Configure the Gemini client from environment or .env."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Export it or add it to GitHub Secrets."
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def parse_entry_date(entry) -> datetime.datetime | None:
    """Try to extract a datetime from an RSS entry."""
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if isinstance(val, struct_time):
            return datetime.datetime.utcfromtimestamp(timegm(val))
    # Some feeds put dates in <dc:date> or similar
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                # Very common ISO-ish format
                return datetime.datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass
    return None


def clean_html(raw: str) -> str:
    """Strip HTML tags for a cleaner abstract."""
    return re.sub(r"<[^>]+>", "", raw).strip()


def passes_keyword_filter(title: str, abstract: str) -> bool:
    """Check if title or abstract contains at least one keyword.
    Returns True (pass) if KEYWORDS is empty or a match is found."""
    if not KEYWORDS:
        return True
    text = (title + " " + abstract).lower()
    return any(kw in text for kw in KEYWORDS)


def score_paper(model, title: str, abstract: str) -> int:
    """Ask Gemini to score a paper 0-10 against INTERESTS, with retry."""
    prompt = f"""\
You are a strict scientific literature assistant.
Rate the relevance of this paper to the researcher profile below.
Output ONLY a single integer from 0 to 10. No text, no explanation.

--- RESEARCHER PROFILE ---
{INTERESTS}

--- PAPER ---
Title: {title}
Abstract: {abstract[:3000]}
"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = model.generate_content(prompt)
            score = int(re.search(r"\d+", resp.text).group())
            return min(max(score, 0), 10)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower():
                wait = 40 * (attempt + 1)
                print(f"  ⏳ Rate limited, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                sleep(wait)
            else:
                print(f"  ⚠ Scoring failed for '{title[:60]}…': {e}")
                return 0
    print(f"  ⚠ Gave up after {max_retries} retries for '{title[:60]}…'")
    return 0


def fetch_and_score(model, cutoff: datetime.datetime):
    """Iterate over all feeds and return scored papers."""
    results = []
    seen_titles = set()
    skipped_by_keyword = 0
    scored_count = 0

    for label, url in FEEDS:
        print(f"\n📡 {label}")
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"  ⚠ Feed error: {e}")
            continue

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            # Date filtering (if parseable)
            pub_date = parse_entry_date(entry)
            if pub_date and pub_date < cutoff:
                continue

            abstract = clean_html(entry.get("description", "") or entry.get("summary", ""))
            if len(abstract) < 50:
                # Skip entries with no real abstract
                continue

            # Keyword pre-filter (skip Gemini call if no keyword match)
            if not passes_keyword_filter(title, abstract):
                skipped_by_keyword += 1
                continue

            sleep(API_SLEEP)
            score = score_paper(model, title, abstract)
            scored_count += 1
            link = entry.get("link", "")
            date_str = pub_date.strftime("%Y-%m-%d") if pub_date else "n/a"

            if score >= RELEVANCE_THRESHOLD:
                print(f"  ✅ [{score}/10] {title[:80]}")
                results.append({
                    "score": score,
                    "title": title,
                    "link": link,
                    "abstract": abstract[:600],
                    "date": date_str,
                    "source": label,
                })
            else:
                print(f"  ── [{score}/10] {title[:80]}")

    print(f"\n📊 Stats: {scored_count} papers scored by Gemini, "
          f"{skipped_by_keyword} skipped by keyword filter")
    results.sort(key=lambda p: p["score"], reverse=True)
    return results


def write_digest(papers: list, output_path: str = "digest_content.md"):
    """Write the Markdown digest as a ranked list grouped by importance tier."""
    today = datetime.date.today().isoformat()
    lines = [
        f"# 📚 Weekly Research Digest — {today}\n",
        f"**Papers scanned across {len(FEEDS)} feeds · "
        f"Showing {len(papers)} papers scoring ≥ {RELEVANCE_THRESHOLD}/10, "
        f"ranked by relevance**\n",
    ]

    if not papers:
        lines.append("\n_No papers met the relevance threshold this week._\n")
    else:
        # Group into tiers
        tiers = [
            ("🔴 Critical (9-10)", lambda p: p["score"] >= 9),
            ("🟠 High Interest (7-8)", lambda p: 7 <= p["score"] <= 8),
            ("🟡 Moderate Interest (5-6)", lambda p: 5 <= p["score"] <= 6),
            ("🟢 Low Interest (2-4)", lambda p: 2 <= p["score"] <= 4),
        ]

        for tier_label, tier_filter in tiers:
            tier_papers = [p for p in papers if tier_filter(p)]
            if not tier_papers:
                continue

            lines.append(f"\n## {tier_label} — {len(tier_papers)} papers\n")
            for p in tier_papers:
                lines.append(f"**[{p['score']}/10] {p['title']}**")
                lines.append(f"{p['source']} · {p['date']} · 🔗 {p['link']}\n")
                lines.append(f"> {p['abstract']}…\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n📝 Digest written to {output_path} ({len(papers)} papers)")


# ──────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    model = init_gemini()
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=DAYS_BACK)
    print(f"🔍 Looking for papers published after {cutoff.date()}")

    papers = fetch_and_score(model, cutoff)
    write_digest(papers)
