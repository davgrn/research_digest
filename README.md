# 📚 Science Digest — AI-Curated Weekly Literature Review

A lightweight, free pipeline that fetches papers from RSS feeds, uses
**Gemini Flash (free tier)** to score them against your research interests,
and delivers a ranked digest as a GitHub Issue every week.

## How it works

```
RSS Feeds (bioRxiv, PubMed, journals)
        │
        ▼
   digest.py  ←── Gemini 2.0 Flash scores each paper 0-10
        │
        ▼
  digest_content.md
        │
        ▼
  GitHub Actions → creates Issue → email notification
```

## Setup (5 minutes)

### 1. Fork or clone this repo

```bash
git clone https://github.com/YOUR_USERNAME/science-digest.git
cd science-digest
```

### 2. Get a Gemini API key (free)

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click **Create API Key**
3. Copy it — you'll need it in the next step

### 3. Add the key as a GitHub Secret

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `GEMINI_API_KEY`
4. Value: paste your key
5. Click **Add secret**

### 4. Customize your interests and feeds

Edit `digest.py`:

- **`INTERESTS`** — describe your research focus in detail. Be specific
  about what scores high vs. low.
- **`FEEDS`** — add/remove RSS feed URLs. Good sources:
  - [bioRxiv RSS feeds](https://www.biorxiv.org/alertsrss) (by subject)
  - [PubMed RSS](https://pubmed.ncbi.nlm.nih.gov/) — run a search, then
    click "Create RSS" below the search bar
  - Journal TOC feeds (Nature, Science, PNAS, etc.)

### 5. Test it

- **Locally:**
  ```bash
  pip install -r requirements.txt
  export GEMINI_API_KEY="your-key-here"
  python digest.py
  ```
- **On GitHub:** Go to **Actions** → **Weekly Science Digest** → **Run workflow**

## Configuration reference

| Variable              | Default | Description                              |
| --------------------- | ------- | ---------------------------------------- |
| `DAYS_BACK`           | 7       | How many days back to look for papers    |
| `RELEVANCE_THRESHOLD` | 7       | Minimum score to include (0-10)          |
| `API_SLEEP`           | 1.5     | Seconds between Gemini calls (rate limit)|
| `FEEDS`               | —       | List of `(label, rss_url)` tuples        |

## Cost

**$0.** The Gemini 2.0 Flash free tier allows 15 RPM / 1500 requests per
day, which is far more than a weekly scan of a few hundred abstracts.

## Privacy note

The free Gemini API tier may use inputs for model improvement. Since you're
only sending **public paper titles and abstracts**, this is not a concern.
Do **not** send unpublished manuscripts or proprietary data through this
pipeline.

## Tips

- Start with 3-4 feeds and expand once you're happy with the scoring
- If you get too many or too few results, adjust `RELEVANCE_THRESHOLD`
- Add keyword pre-filters in the script to skip obviously irrelevant papers
  before calling the API (saves quota)
- To run twice a week, edit the cron in `.github/workflows/weekly-digest.yml`