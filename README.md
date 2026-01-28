# Multi-Store Price Updater

This script integrates price updaters for multiple stores (Al-Fatah, Jalal Sons, Metro, Rainbow, Imtiaz, and Carrefour) and provides a streamlined workflow for updating product prices through local CSV operations.

## Project Structure

```
price_updaters/
├── main.py                     # Price update workflow
├── progress_tracker.py         # Progress tracking for resumable operations
├── products.csv               # Input products file
├── consolidated.csv           # Generated consolidated output (root)
├── requirements.txt           # Python dependencies
├── updaters/                  # Price updater modules
│   ├── __init__.py
│   ├── alfatah_price_updater.py       # Selenium-based (legacy)
│   ├── alfatah_price_updater_fast.py  # HTTP + JSON (fast) ⚡
│   ├── jalalsons_price_updater.py     # Selenium-based (legacy)
│   ├── jalalsons_price_updater_fast.py # HTTP + JSON (fast) ⚡
│   ├── metro_price_updater.py         # Selenium-based (legacy)
│   ├── metro_price_updater_fast.py    # HTTP + JSON (fast) ⚡
│   ├── rainbow_price_updater.py       # Selenium-based (legacy)
│   ├── rainbow_price_updater_fast.py  # HTTP + JSON (fast) ⚡
│   ├── imtiaz_price_updater.py        # Selenium-based
│   └── carrefour_price_updater.py     # Selenium-based
├── reports/                   # Generated reports and summaries
│   ├── summary_report_YYYY-MM-DD.txt
│   ├── *_price_comparison_YYYY-MM-DD.csv
│   ├── *_updated_YYYY-MM-DD.csv
│   └── *_update_report_*.txt
├── price_updates/             # Processing files
│   ├── *_products.csv         # Store-specific input splits
│   ├── *_price_comparison_YYYY-MM-DD.csv
│   ├── *_updated_YYYY-MM-DD.csv
│   └── progress/              # Progress tracking files
│       └── *_progress.csv
└── others/                    # Utility scripts
    ├── convert_json_to_env.py
    ├── firebase_config.py
    └── update_firebase.py
```

## Features

- Split input CSV by store (Al-Fatah, Jalal Sons, Metro, Rainbow, Imtiaz, Carrefour)
- Generate price comparison CSVs for all stores
- Apply price updates from comparison CSVs to local files
- Merge updated data into a consolidated file
- Generate comprehensive summary reports
- **Progress tracking** for resumable operations (can resume after interruption)
- **Fast updaters** using HTTP + JSON parsing for supported stores (no browser required)
- Pure local CSV workflow

## Requirements

- Python 3.8+
- pandas
- selenium
- Chrome browser (for web scraping)
- webdriver-manager

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Complete Workflow

Run the complete price update workflow:

```bash
python main.py products.csv
```

This will:
1. ✅ Split input CSV by store
2. ✅ Update prices from all store websites
3. ✅ Generate comparison CSVs
4. ✅ Apply updates and create consolidated CSV

### Headless Mode

Run in headless mode (no browser UI):

```bash
python main.py products.csv --headless
```

### Two-Step Process (Manual Review)

#### Step 1 Only: Generate Comparison CSVs

Run only the comparison generation step:

```bash
python main.py products.csv --step1-only
```

This will:
1. Split the input CSV by store
2. Generate comparison CSVs for all stores
3. Output the comparison CSVs for manual review

#### Step 2 Only: Apply Updates

After reviewing the comparison CSVs, apply the updates:

```bash
python main.py products.csv --step2-only
```

This will:
1. Apply updates based on the already generated comparison CSVs
2. Generate updated CSVs for all stores
3. Create a consolidated output file

## Input CSV Format

The input CSV must have the following columns:
- `product_id`: Unique identifier for the product
- `store_id`: Store identifier ("Al-Fatah", "Jalal Sons", "Metro", "Rainbow", "Imtiaz", or "Carrefour")
- `original_url`: URL of the product page
- `price`: Current price in the system

Example:
```csv
product_id,store_id,original_url,price,name
abc123,Carrefour,https://www.carrefour.pk/mafpak/en/special-rice/guard-spr-kernel-sella-basmati-1kg/p/134539,470,Guard Rice 1kg
def456,Al-Fatah,https://alfatah.pk/products/example,350,Example Product
```

## Output Files

The application generates files in an organized structure:

### Root Directory
- `consolidated.csv`: Final consolidated output with all updated products (only products with price changes)

### Reports Directory (`reports/`)
- `summary_report_YYYY-MM-DD.txt`: Comprehensive summary of the price update process
- `[store]_price_comparison_YYYY-MM-DD.csv`: Price comparison CSVs for manual review
- `[store]_updated_YYYY-MM-DD.csv`: Updated product files for each store
- `[store]_update_report_*.txt`: Detailed update reports per store

### Processing Directory (`price_updates/`)
- `[store]_products.csv`: Products extracted from input CSV for each store
- `[store]_price_comparison_YYYY-MM-DD.csv`: Comparison files
- `[store]_updated_YYYY-MM-DD.csv`: Updated files
- `progress/[store]_progress.csv`: Progress tracking for resumable operations

Where `[store]` can be: alfatah, jalalsons, metro, rainbow, imtiaz, or carrefour

## Workflow Examples

### Complete Workflow
```bash
python main.py products.csv
```
Runs both steps automatically (generates comparisons and applies all changes)

### Two-Step Workflow with Manual Review

**Step 1: Generate Price Comparisons**
```bash
python main.py products.csv --step1-only
```
This creates comparison CSVs with columns: `product_id`, `old_price`, `new_price`, `price_change_needed`

**Step 2: Apply Updates (After Manual Review)**
```bash
python main.py products.csv --step2-only
```
This applies updates only for products marked with `price_change_needed = YES`

### Headless Mode
```bash
python main.py products.csv --headless
```
Runs without browser UI (faster execution)

## Supported Stores

| Store | Website | Store ID | Updater Type |
|-------|---------|----------|-------------|
| Al-Fatah | alfatah.pk | `Al-Fatah` | ⚡ Fast (HTTP) |
| Jalal Sons | jalalsons.com.pk | `Jalal Sons` | ⚡ Fast (HTTP) |
| Metro | metro-online.pk | `Metro` | ⚡ Fast (HTTP) |
| Rainbow | rainbowcc.com.pk | `Rainbow` | ⚡ Fast (HTTP) |
| Imtiaz | shop.imtiaz.com.pk | `Imtiaz` | 🌐 Selenium |
| Carrefour | carrefour.pk | `Carrefour` | 🌐 Selenium |

## Scripts Overview

### main.py
- **Purpose**: Main entry point for price update workflow
- **Features**: Web scraping, price comparison, CSV generation, multi-store support
- **Usage**: `python main.py input.csv [--headless] [--step1-only|--step2-only]`

### progress_tracker.py
- **Purpose**: Tracks progress for resumable operations
- **Features**: Saves processed product IDs, allows resuming after interruption

### updaters/*.py
- **Purpose**: Store-specific price extraction logic
- **Stores**: alfatah, jalalsons, metro, rainbow, imtiaz, carrefour
- **Two versions available**:
  - **Standard (`*_price_updater.py`)**: Selenium-based scraping with browser automation
  - **Fast (`*_price_updater_fast.py`)**: HTTP requests + JSON parsing (no browser required) ⚡
- **Fast versions used by default** for: Al-Fatah, Jalal Sons, Metro, Rainbow
- **Selenium-only** (no fast version yet): Imtiaz, Carrefour
- **Features**: Anti-bot detection, retry logic, progress tracking

## Progress Tracking

The system automatically tracks progress for each store. If the script is interrupted:
- Progress is saved in `price_updates/progress/[store]_progress.csv`
- When you restart, already processed products are skipped
- Simply run the same command again to resume

## Comparison CSV Format

Generated comparison CSVs contain:
| Column | Description |
|--------|-------------|
| `product_id` | Product identifier |
| `old_price` | Price from input CSV |
| `new_price` | Price scraped from website |
| `price_change_needed` | `YES`, `NO`, or `ERROR - [reason]` |

Only products with `price_change_needed = YES` are included in the consolidated output.