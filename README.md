# Multi-Store Price Updater

This script integrates price updaters for multiple stores (Al-Fatah, Jalal Sons, Metro, Rainbow, and Imtiaz) and provides a streamlined workflow for updating product prices through local CSV operations.

## Features

- Split input CSV by store (Al-Fatah, Jalal Sons, Metro, Rainbow, Imtiaz)
- Generate price comparison CSVs for all stores
- Apply price updates from comparison CSVs to local files
- Merge updated data into a consolidated file
- Generate comprehensive summary reports
- Pure local CSV workflow (no external database dependencies)

## Requirements

- Python 3.8+
- pandas
- selenium
- Firefox browser (for web scraping)
- webdriver-manager

## Usage

### Complete Workflow

Run the complete price update workflow:

```bash
python main.py products.csv
```

### Headless Mode

Run in headless mode (no browser UI):

```bash
python main.py products.csv --headless
```

### Two-Step Process

#### Step 1 Only: Generate Comparison CSVs

Run only the comparison generation step:

```bash
python main.py products.csv --step1-only
```

This will:
1. Split the input CSV by store
2. Generate comparison CSVs for both stores
3. Output the comparison CSVs for manual review

#### Step 2 Only: Apply Updates

After reviewing the comparison CSVs, apply the updates:

```bash
python main.py products.csv --step2-only
```

This will:
1. Apply updates based on the already generated comparison CSVs
2. Generate updated CSVs for both stores
3. Create a consolidated output file

## Input CSV Format

The input CSV must have the following columns:
- `product_id`: Unique identifier for the product
- `store_id`: Store identifier ("Al-Fatah", "Jalal Sons", "Metro", "Rainbow", or "Imtiaz")
- `original_url`: URL of the product page
- `price`: Current price in the system

## Output Files

All output files are saved in a date-stamped directory (`price_updates_YYYY-MM-DD`):

- `[store]_products.csv`: Products extracted from input CSV for each store
- `[store]_price_comparison_YYYY-MM-DD.csv`: Price comparison CSVs for manual review
- `[store]_updated_YYYY-MM-DD.csv`: Updated product files for each store
- `consolidated_updated_YYYY-MM-DD.csv`: Consolidated output with all updated products
- `summary_report_YYYY-MM-DD.txt`: Summary of the price update process

Where `[store]` can be: alfatah, jalalsons, metro, rainbow, or imtiaz

## Workflow Process

### Two-Step Workflow (Recommended)

**Step 1: Generate Price Comparisons**
```bash
python main.py test_with_matched.csv --step1-only
```
This creates comparison CSVs with columns: `product_id`, `old_price`, `new_price`, `price_change_needed`

**Step 2: Apply Updates (After Manual Review)**
```bash
python main.py test_with_matched.csv --step2-only
```
This applies updates only for products marked with `price_change_needed = YES`

### Complete Workflow
```bash
python main.py test_with_matched.csv
```
Runs both steps automatically (generates comparisons and applies all changes)

### Headless Mode
```bash
python main.py test_with_matched.csv --headless
```
Runs without browser UI (faster execution)

## Supported Stores

- **Al-Fatah** (alfatah.pk)
- **Jalal Sons** (jalalsons.com.pk)
- **Metro** (metro-online.pk)  
- **Rainbow** (rainbowcc.com.pk)
- **Imtiaz** (shop.imtiaz.com.pk)