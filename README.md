# Multi-Store Price Updater

This script integrates price updaters for multiple stores (Al-Fatah, Jalal Sons, Metro, Rainbow, and Imtiaz) and provides a streamlined workflow for updating product prices through local CSV operations.

## Project Structure

```
price_updaters/
├── orchestrator.py            # Main orchestrator (runs main.py + Firebase sync)
├── main.py                     # Price update workflow
├── update_firebase.py          # Firebase integration script
├── products.csv               # Input products file
├── test_with_matched.csv      # Test input file
├── consolidated.csv           # Generated consolidated output (root)
├── requirements.txt           # Python dependencies
├── serviceAccountKey.json     # Firebase service account key
├── updaters/                  # Price updater modules
│   ├── __init__.py
│   ├── alfatah_price_updater.py
│   ├── jalalsons_price_updater.py
│   ├── metro_price_updater.py
│   ├── rainbow_price_updater.py
│   └── imtiaz_price_updater.py
├── reports/                   # Generated reports and summaries
│   ├── summary_report_YYYY-MM-DD.txt
│   ├── *_price_comparison_YYYY-MM-DD.csv
│   └── *_updated_YYYY-MM-DD.csv
└── price_updates_YYYY-MM-DD/  # Temporary processing files
    ├── *_products.csv         # Store-specific input splits
    ├── *_price_comparison_YYYY-MM-DD.csv
    └── *_updated_YYYY-MM-DD.csv
```

## Features

- **Automated End-to-End Workflow**: Complete orchestration from price updates to Firebase sync
- Split input CSV by store (Al-Fatah, Jalal Sons, Metro, Rainbow, Imtiaz)
- Generate price comparison CSVs for all stores
- Apply price updates from comparison CSVs to local files
- Merge updated data into a consolidated file
- **Automatic Firebase synchronization** of updated products
- Generate comprehensive summary reports
- Pure local CSV workflow with optional cloud sync

## Requirements

- Python 3.8+
- pandas
- selenium
- Firefox browser (for web scraping)
- webdriver-manager

## Usage

### Quick Start - Complete Automated Workflow (Recommended)

Run the complete price update and Firebase sync workflow:

```bash
python orchestrator.py
```

Or with a custom input file:

```bash
python orchestrator.py products.csv
```

This will:
1. ✅ Update prices from all store websites
2. ✅ Generate consolidated CSV with price changes
3. ✅ Automatically sync updated products to Firebase

### Advanced Options

#### Run Only Price Updates (No Firebase Sync)

```bash
python orchestrator.py --step1-only
```

#### Run Only Firebase Sync (After Manual Review)

```bash
python orchestrator.py --step2-only
```

---

### Manual Workflow - Using main.py Directly

#### Complete Workflow

Run the complete price update workflow:

```bash
python main.py products.csv
```

### Headless Mode

Run in headless mode (no browser UI):

```bash
python main.py products.csv --headless
```

---

### Firebase Integration

After running the price update workflow, sync the consolidated results to Firebase:

```bash
python update_firebase.py
```

**Note**: The orchestrator (`orchestrator.py`) automatically handles this step for you!

### Two-Step Process (Manual Review)

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

The application generates files in an organized structure:

### Root Directory
- `consolidated.csv`: Final consolidated output with all updated products (only products with price changes)

### Reports Directory (`reports/`)
- `summary_report_YYYY-MM-DD.txt`: Comprehensive summary of the price update process
- `[store]_price_comparison_YYYY-MM-DD.csv`: Price comparison CSVs for manual review
- `[store]_updated_YYYY-MM-DD.csv`: Updated product files for each store

### Processing Directory (`price_updates_YYYY-MM-DD/`)
- `[store]_products.csv`: Products extracted from input CSV for each store
- `[store]_price_comparison_YYYY-MM-DD.csv`: Temporary comparison files
- `[store]_updated_YYYY-MM-DD.csv`: Temporary updated files

Where `[store]` can be: alfatah, jalalsons, metro, rainbow, or imtiaz

## Workflow Process

### Recommended: Orchestrator Workflow

**Complete Automated Workflow**
```bash
python orchestrator.py test_with_matched.csv
```
This automatically:
1. Generates price comparisons from store websites
2. Applies updates to create consolidated CSV
3. Syncs updated products to Firebase

**Step-by-Step with Manual Review**
```bash
# Step 1: Price updates only
python orchestrator.py test_with_matched.csv --step1-only

# Review the consolidated.csv file

# Step 2: Firebase sync only
python orchestrator.py --step2-only
```

---

### Manual Workflow (Using main.py)

**Two-Step Workflow with Manual Review**

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

**Complete Price Update Workflow**
```bash
python main.py test_with_matched.csv
```
Runs both steps automatically (generates comparisons and applies all changes)

**Headless Mode**
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

## Firebase Configuration

To use Firebase integration:

1. Obtain your Firebase service account key from Firebase Console
2. Convert it to `.env` format: `python3 convert_json_to_env.py`
3. Update the collection name in `.env` if needed (default: `test_collection`)

The orchestrator will automatically sync products with `price_change_needed = YES` to your Firebase Firestore database.

## Cloud Deployment

For running this application continuously on the cloud (e.g., 3-day operations):

- **AWS Free Tier Deployment**: See `QUICKSTART.md` or `AWS_DEPLOYMENT.md`
- **Features**: 12 months free, t2.micro instance, perfect for long-running tasks
- **Cost**: $0 for first 12 months (within free tier limits)

## Scripts Overview

### orchestrator.py
- **Purpose**: Main entry point for complete workflow automation
- **Features**: Runs price updates + Firebase sync in one command
- **Usage**: `python orchestrator.py [input_csv] [--step1-only|--step2-only]`

### main.py
- **Purpose**: Core price update logic for all stores
- **Features**: Web scraping, price comparison, CSV generation
- **Usage**: `python main.py input.csv [--headless] [--step1-only|--step2-only]`

### update_firebase.py
- **Purpose**: Syncs consolidated CSV to Firebase Firestore
- **Features**: Batch updates, error handling, progress tracking
- **Usage**: `python update_firebase.py` (uses consolidated.csv by default)

### Utility Scripts

#### convert_json_to_env.py
- **Purpose**: Convert Firebase JSON key to `.env` format
- **Usage**: `python3 convert_json_to_env.py`
- **Note**: For secure cloud deployment

#### setup_aws.sh
- **Purpose**: Automated AWS EC2 setup script
- **Usage**: Run on fresh AWS EC2 instance
- **Note**: Installs all dependencies automatically

#### run_in_background.sh
- **Purpose**: Runs orchestrator in background (for multi-day operations)
- **Usage**: `./run_in_background.sh`
- **Note**: Process continues even if SSH disconnects