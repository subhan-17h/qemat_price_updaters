# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Common Commands

### Run complete price update workflow
```bash
python main.py products.csv
```

### Run in headless mode (no browser UI)
```bash
python main.py products.csv --headless
```

### Step 1 only: Generate comparison CSVs (for manual review)
```bash
python main.py products.csv --step1-only
```

### Step 2 only: Apply updates from existing comparison CSVs
```bash
python main.py products.csv --step2-only
```

### Install dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### High-Level Structure

This is a multi-store price updater that scrapes current prices from e-commerce websites and updates a local product database. The workflow is:

1. **Split**: Input CSV is split by store into separate files
2. **Compare**: For each store, scrape prices and generate comparison CSVs
3. **Update**: Apply price changes to local CSV files
4. **Consolidate**: Merge all updates into `consolidated.csv`

### Key Components

**main.py** - Entry point and orchestrator
- `MultiStoreUpdater` class coordinates the entire workflow
- Imports fast versions (HTTP+JSON) for Al-Fatah, Jalal Sons, Metro, Rainbow
- Imports Selenium versions for Imtiaz, Carrefour (no fast version available)
- Supports `--step1-only` and `--step2-only` flags for manual review workflow

**progress_tracker.py** - Resumable operations
- `ProgressTracker` class saves processed product IDs to CSV
- Already-processed products are skipped on re-run
- Progress files stored in `price_updates/progress/[store]_progress.csv`

**updaters/** - Store-specific price extraction modules
Each store has a `*_price_updater.py` (Selenium-based) and optionally `*_price_updater_fast.py` (HTTP+JSON):

| Store | Fast Version | Implementation |
|-------|-------------|----------------|
| Al-Fatah | Yes | Shopify JSON parsing (price in cents) |
| Jalal Sons | Yes | HTTP + BeautifulSoup |
| Metro | Yes | HTTP + JSON API |
| Rainbow | Yes | HTTP + BeautifulSoup |
| Imtiaz | No | Selenium + location dropdown handling |
| Carrefour | No | Selenium-based |

### Two-Step Workflow

The system supports a manual review workflow:

**Step 1** (`--step1-only`): Generates comparison CSVs with columns:
- `product_id`, `old_price`, `new_price`, `price_change_needed`

**Step 2** (`--step2-only`): Applies updates only where `price_change_needed = 'YES'`

This allows manual inspection before applying changes.

### Input CSV Format

Required columns:
- `product_id`: Unique identifier
- `store_id`: "Al-Fatah", "Jalal Sons", "Metro", "Rainbow", "Imtiaz", or "Carrefour"
- `original_url`: Product page URL
- `price`: Current price in the system

### Output Files

- `consolidated.csv`: Root-level file with only products that had price changes
- `reports/`: Summary reports and comparison/updated CSVs
- `price_updates/`: Store-specific processing files and progress tracking
- `price_updates/progress/[store]_progress.csv`: Progress files for resumable operations

### Adding a New Store

To add a new store updater:

1. Create `updaters/[store]_price_updater.py` or `[store]_price_updater_fast.py`
2. Implement `generate_price_comparison(csv_file_path, output_path, delay_seconds, progress_tracker)` function
3. Implement `update_local_from_reviewed_csv(reviewed_csv_path, original_csv_path, output_csv_path)` function
4. Import and add to `main.py`'s `MultiStoreUpdater` class
5. Add store to results dictionary, split logic, and workflow steps
