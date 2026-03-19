# Multi-Store Price Updater

This script integrates price updaters for multiple stores (Al-Fatah, Jalal Sons, Metro, Rainbow, Imtiaz, and Carrefour). It splits an input CSV by store, scrapes current prices from each store's website, generates price comparison reports, and creates a consolidated output CSV.

## Requirements

- Python 3.8+
- Install dependencies: `pip install -r requirements.txt`

## Run the complete price update workflow

```bash
python main.py products.csv
```

## Full Firebase -> Scrape -> Firebase Pipeline

This repository now supports a full 3-step pipeline:

1. Export products from Firebase into root `products.csv`
2. Run all store updaters to generate `consolidated.csv`
3. Push consolidated price updates back to Firebase

### One-command pipeline (recommended for cloud)

```bash
python run_pipeline.py
```

### Useful pipeline flags

```bash
# Dry run (print commands only)
python run_pipeline.py --dry-run

# Skip Firebase export step
python run_pipeline.py --skip-fetch

# Skip Firebase update step
python run_pipeline.py --skip-firebase-update

# Run Selenium in headed mode
python run_pipeline.py --no-headless
```

### Node dependencies (required for Firebase scripts)

```bash
npm install
```

## Input CSV Format

The input CSV must have these columns:
- `product_id`: Unique identifier
- `store_id`: Store identifier ("Al-Fatah", "Jalal Sons", "Metro", "Rainbow", "Imtiaz", or "Carrefour")
- `original_url`: URL of the product page
- `price`: Current price in the system

## Output Files

- `consolidated.csv`: Final consolidated output with all updated products (only products with price changes)
- `reports/`: Summary reports and comparison CSVs
- `price_updates/`: Store-specific processing files and progress tracking
