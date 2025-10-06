#type: ignore

import os
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List

# Import the updater modules
from updaters import alfatah_price_updater as alfatah
from updaters import jalalsons_price_updater as jalalsons
from updaters import rainbow_price_updater as rainbow
from updaters import metro_price_updater as metro
from updaters import imtiaz_price_updater as imtiaz

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MultiStoreUpdater:
    def __init__(self, input_csv_path: str, headless: bool = False):
        """
        Initialize the multi-store updater.
        
        Args:
            input_csv_path (str): Path to the input CSV with products from multiple stores
            headless (bool): Run browsers in headless mode
        """
        self.input_csv_path = input_csv_path
        self.headless = headless
        self.timestamp = datetime.now().strftime('%Y-%m-%d')
        
        # Create output directory for this run
        self.output_dir = f"price_updates"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create reports directory if it doesn't exist
        self.reports_dir = "reports"
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # Store-specific paths
        self.alfatah_csv_path = os.path.join(self.output_dir, "alfatah_products.csv")
        self.jalalsons_csv_path = os.path.join(self.output_dir, "jalalsons_products.csv")
        self.rainbow_csv_path = os.path.join(self.output_dir, "rainbow_products.csv")
        self.metro_csv_path = os.path.join(self.output_dir, "metro_products.csv")
        self.imtiaz_csv_path = os.path.join(self.output_dir, "imtiaz_products.csv")
        
        # Comparison CSVs
        self.alfatah_comparison_path = os.path.join(self.output_dir, f"alfatah_price_comparison_{self.timestamp}.csv")
        self.jalalsons_comparison_path = os.path.join(self.output_dir, f"jalalsons_price_comparison_{self.timestamp}.csv")
        self.rainbow_comparison_path = os.path.join(self.output_dir, f"rainbow_price_comparison_{self.timestamp}.csv")
        self.metro_comparison_path = os.path.join(self.output_dir, f"metro_price_comparison_{self.timestamp}.csv")
        self.imtiaz_comparison_path = os.path.join(self.output_dir, f"imtiaz_price_comparison_{self.timestamp}.csv")
        
        # Output CSVs
        self.alfatah_output_path = os.path.join(self.output_dir, f"alfatah_updated_{self.timestamp}.csv")
        self.jalalsons_output_path = os.path.join(self.output_dir, f"jalalsons_updated_{self.timestamp}.csv")
        self.rainbow_output_path = os.path.join(self.output_dir, f"rainbow_updated_{self.timestamp}.csv")
        self.metro_output_path = os.path.join(self.output_dir, f"metro_updated_{self.timestamp}.csv")
        self.imtiaz_output_path = os.path.join(self.output_dir, f"imtiaz_updated_{self.timestamp}.csv")
        
        # Results tracking
        self.results = {
            "Al-Fatah": {"products": 0, "comparison_generated": False, "updates_applied": False},
            "Jalal Sons": {"products": 0, "comparison_generated": False, "updates_applied": False},
            "Rainbow": {"products": 0, "comparison_generated": False, "updates_applied": False},
            "Metro": {"products": 0, "comparison_generated": False, "updates_applied": False},
            "Imtiaz": {"products": 0, "comparison_generated": False, "updates_applied": False}
        }
    
    def split_input_csv_by_store(self) -> Dict[str, int]:
        """Split the input CSV into store-specific CSVs and return product counts"""
        try:
            logger.info(f"📄 Reading input CSV: {self.input_csv_path}")
            df = pd.read_csv(self.input_csv_path)
            
            # Validate required columns
            required_columns = ['product_id', 'store_id', 'original_url', 'price']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Input CSV is missing required columns: {', '.join(missing_columns)}")
            
            # Split by store_id
            alfatah_df = df[df['store_id'] == 'Al-Fatah']
            jalalsons_df = df[df['store_id'] == 'Jalal Sons']
            rainbow_df = df[df['store_id'] == 'Rainbow']
            metro_df = df[df['store_id'] == 'Metro']
            imtiaz_df = df[df['store_id'] == 'Imtiaz']
            
            # Save store-specific CSVs
            if len(alfatah_df) > 0:
                alfatah_df.to_csv(self.alfatah_csv_path, index=False)
                self.results["Al-Fatah"]["products"] = len(alfatah_df)
                logger.info(f"📊 Found {len(alfatah_df)} Al-Fatah products")
            else:
                logger.warning("⚠️  No Al-Fatah products found in the input CSV")
            
            if len(jalalsons_df) > 0:
                jalalsons_df.to_csv(self.jalalsons_csv_path, index=False)
                self.results["Jalal Sons"]["products"] = len(jalalsons_df)
                logger.info(f"📊 Found {len(jalalsons_df)} Jalal Sons products")
            else:
                logger.warning("⚠️  No Jalal Sons products found in the input CSV")
            
            if len(rainbow_df) > 0:
                rainbow_df.to_csv(self.rainbow_csv_path, index=False)
                self.results["Rainbow"]["products"] = len(rainbow_df)
                logger.info(f"📊 Found {len(rainbow_df)} Rainbow products")
            else:
                logger.warning("⚠️  No Rainbow products found in the input CSV")
            
            if len(metro_df) > 0:
                metro_df.to_csv(self.metro_csv_path, index=False)
                self.results["Metro"]["products"] = len(metro_df)
                logger.info(f"📊 Found {len(metro_df)} Metro products")
            else:
                logger.warning("⚠️  No Metro products found in the input CSV")
            
            if len(imtiaz_df) > 0:
                imtiaz_df.to_csv(self.imtiaz_csv_path, index=False)
                self.results["Imtiaz"]["products"] = len(imtiaz_df)
                logger.info(f"📊 Found {len(imtiaz_df)} Imtiaz products")
            else:
                logger.warning("⚠️  No Imtiaz products found in the input CSV")
            
            return {
                "Al-Fatah": len(alfatah_df),
                "Jalal Sons": len(jalalsons_df),
                "Rainbow": len(rainbow_df),
                "Metro": len(metro_df),
                "Imtiaz": len(imtiaz_df)
            }
        
        except Exception as e:
            logger.error(f"❌ Error splitting input CSV: {e}")
            raise
    
    def generate_price_comparisons(self) -> Dict:
        """Generate price comparison CSVs for all supported stores"""
        results = {}
        
        # Step 1: Generate Al-Fatah comparison
        if self.results["Al-Fatah"]["products"] > 0:
            try:
                logger.info("\n🔄 Generating Al-Fatah price comparison...")
                alfatah_results = alfatah.generate_price_comparison(
                    csv_file_path=self.alfatah_csv_path, 
                    output_path=self.alfatah_comparison_path,
                    delay_seconds=2
                )
                self.results["Al-Fatah"]["comparison_generated"] = True
                results["Al-Fatah"] = alfatah_results
                logger.info("✅ Al-Fatah comparison CSV generated successfully")
            except Exception as e:
                logger.error(f"❌ Error generating Al-Fatah comparison: {e}")
                self.results["Al-Fatah"]["comparison_generated"] = False
        
        # Step 2: Generate Jalal Sons comparison
        if self.results["Jalal Sons"]["products"] > 0:
            try:
                logger.info("\n🔄 Generating Jalal Sons price comparison...")
                jalalsons_results = jalalsons.generate_price_comparison(
                    csv_file_path=self.jalalsons_csv_path, 
                    output_path=self.jalalsons_comparison_path,
                    delay_seconds=3
                )
                self.results["Jalal Sons"]["comparison_generated"] = True
                results["Jalal Sons"] = jalalsons_results
                logger.info("✅ Jalal Sons comparison CSV generated successfully")
            except Exception as e:
                logger.error(f"❌ Error generating Jalal Sons comparison: {e}")
                self.results["Jalal Sons"]["comparison_generated"] = False
        
        # Step 3: Generate Rainbow comparison
        if self.results["Rainbow"]["products"] > 0:
            try:
                logger.info("\n🔄 Generating Rainbow price comparison...")
                rainbow_results = rainbow.generate_price_comparison(
                    csv_file_path=self.rainbow_csv_path, 
                    output_path=self.rainbow_comparison_path,
                    delay_seconds=3
                )
                self.results["Rainbow"]["comparison_generated"] = True
                results["Rainbow"] = rainbow_results
                logger.info("✅ Rainbow comparison CSV generated successfully")
            except Exception as e:
                logger.error(f"❌ Error generating Rainbow comparison: {e}")
                self.results["Rainbow"]["comparison_generated"] = False
        
        # Step 4: Generate Metro comparison
        if self.results["Metro"]["products"] > 0:
            try:
                logger.info("\n🔄 Generating Metro price comparison...")
                metro_results = metro.generate_price_comparison(
                    csv_file_path=self.metro_csv_path, 
                    output_path=self.metro_comparison_path,
                    delay_seconds=3
                )
                self.results["Metro"]["comparison_generated"] = True
                results["Metro"] = metro_results
                logger.info("✅ Metro comparison CSV generated successfully")
            except Exception as e:
                logger.error(f"❌ Error generating Metro comparison: {e}")
                self.results["Metro"]["comparison_generated"] = False
        
        # Step 5: Generate Imtiaz comparison
        if self.results["Imtiaz"]["products"] > 0:
            try:
                logger.info("\n🔄 Generating Imtiaz price comparison...")
                imtiaz_results = imtiaz.generate_price_comparison(
                    csv_file_path=self.imtiaz_csv_path, 
                    output_path=self.imtiaz_comparison_path,
                    delay_seconds=3
                )
                self.results["Imtiaz"]["comparison_generated"] = True
                results["Imtiaz"] = imtiaz_results
                logger.info("✅ Imtiaz comparison CSV generated successfully")
            except Exception as e:
                logger.error(f"❌ Error generating Imtiaz comparison: {e}")
                self.results["Imtiaz"]["comparison_generated"] = False
        
        return results
    
    def update_from_comparisons(self) -> Dict:
        """Update local CSVs from the generated comparison CSVs"""
        results = {}
        
        # Step 1: Update Al-Fatah products
        if self.results["Al-Fatah"]["comparison_generated"]:
            try:
                logger.info("\n🔄 Applying Al-Fatah price updates...")
                alfatah_results = alfatah.update_local_from_reviewed_csv(
                    reviewed_csv_path=self.alfatah_comparison_path,
                    original_csv_path=self.alfatah_csv_path,
                    output_csv_path=self.alfatah_output_path
                )
                self.results["Al-Fatah"]["updates_applied"] = True
                results["Al-Fatah"] = alfatah_results
                logger.info("✅ Al-Fatah price updates applied successfully")
            except Exception as e:
                logger.error(f"❌ Error applying Al-Fatah updates: {e}")
                self.results["Al-Fatah"]["updates_applied"] = False
        
        # Step 2: Update Jalal Sons products
        if self.results["Jalal Sons"]["comparison_generated"]:
            try:
                logger.info("\n🔄 Applying Jalal Sons price updates...")
                jalalsons_results = jalalsons.update_local_from_reviewed_csv(
                    reviewed_csv_path=self.jalalsons_comparison_path,
                    original_csv_path=self.jalalsons_csv_path,
                    output_csv_path=self.jalalsons_output_path
                )
                self.results["Jalal Sons"]["updates_applied"] = True
                results["Jalal Sons"] = jalalsons_results
                logger.info("✅ Jalal Sons price updates applied successfully")
            except Exception as e:
                logger.error(f"❌ Error applying Jalal Sons updates: {e}")
                self.results["Jalal Sons"]["updates_applied"] = False
        
        # Step 3: Update Rainbow products
        if self.results["Rainbow"]["comparison_generated"]:
            try:
                logger.info("\n🔄 Applying Rainbow price updates...")
                rainbow_results = rainbow.update_local_from_reviewed_csv(
                    reviewed_csv_path=self.rainbow_comparison_path,
                    original_csv_path=self.rainbow_csv_path,
                    output_csv_path=self.rainbow_output_path
                )
                self.results["Rainbow"]["updates_applied"] = True
                results["Rainbow"] = rainbow_results
                logger.info("✅ Rainbow price updates applied successfully")
            except Exception as e:
                logger.error(f"❌ Error applying Rainbow updates: {e}")
                self.results["Rainbow"]["updates_applied"] = False
        
        # Step 4: Update Metro products
        if self.results["Metro"]["comparison_generated"]:
            try:
                logger.info("\n🔄 Applying Metro price updates...")
                metro_results = metro.update_local_from_reviewed_csv(
                    reviewed_csv_path=self.metro_comparison_path,
                    original_csv_path=self.metro_csv_path,
                    output_csv_path=self.metro_output_path
                )
                self.results["Metro"]["updates_applied"] = True
                results["Metro"] = metro_results
                logger.info("✅ Metro price updates applied successfully")
            except Exception as e:
                logger.error(f"❌ Error applying Metro updates: {e}")
                self.results["Metro"]["updates_applied"] = False
        
        # Step 5: Update Imtiaz products
        if self.results["Imtiaz"]["comparison_generated"]:
            try:
                logger.info("\n🔄 Applying Imtiaz price updates...")
                imtiaz_results = imtiaz.update_local_from_reviewed_csv(
                    reviewed_csv_path=self.imtiaz_comparison_path,
                    original_csv_path=self.imtiaz_csv_path,
                    output_csv_path=self.imtiaz_output_path
                )
                self.results["Imtiaz"]["updates_applied"] = True
                results["Imtiaz"] = imtiaz_results
                logger.info("✅ Imtiaz price updates applied successfully")
            except Exception as e:
                logger.error(f"❌ Error applying Imtiaz updates: {e}")
                self.results["Imtiaz"]["updates_applied"] = False
        
        return results
    
    def check_existing_comparison_files(self) -> None:
        """Check for existing comparison files and set appropriate flags for step2-only mode"""
        logger.info("🔍 Checking for existing comparison files...")
        
        # Check Al-Fatah comparison file
        if os.path.exists(self.alfatah_comparison_path):
            self.results["Al-Fatah"]["comparison_generated"] = True
            logger.info(f"✅ Found Al-Fatah comparison file: {self.alfatah_comparison_path}")
        
        # Check Jalal Sons comparison file
        if os.path.exists(self.jalalsons_comparison_path):
            self.results["Jalal Sons"]["comparison_generated"] = True
            logger.info(f"✅ Found Jalal Sons comparison file: {self.jalalsons_comparison_path}")
        
        # Check Rainbow comparison file
        if os.path.exists(self.rainbow_comparison_path):
            self.results["Rainbow"]["comparison_generated"] = True
            logger.info(f"✅ Found Rainbow comparison file: {self.rainbow_comparison_path}")
        
        # Check Metro comparison file
        if os.path.exists(self.metro_comparison_path):
            self.results["Metro"]["comparison_generated"] = True
            logger.info(f"✅ Found Metro comparison file: {self.metro_comparison_path}")
        
        # Check Imtiaz comparison file
        if os.path.exists(self.imtiaz_comparison_path):
            self.results["Imtiaz"]["comparison_generated"] = True
            logger.info(f"✅ Found Imtiaz comparison file: {self.imtiaz_comparison_path}")
    

    def merge_output_files(self) -> str:
        """Merge only products with price changes from all stores into a single consolidated file"""
        try:
            # Create consolidated output path in root directory
            consolidated_path = "consolidated.csv"
            
            # Collect DataFrames to concatenate (only products with price changes)
            dfs_to_merge = []
            total_products_with_changes = 0
            
            # Add Al-Fatah updates if available (only products with price changes)
            if self.results["Al-Fatah"]["updates_applied"] and os.path.exists(self.alfatah_output_path) and os.path.exists(self.alfatah_comparison_path):
                alfatah_df = pd.read_csv(self.alfatah_output_path)
                alfatah_comparison_df = pd.read_csv(self.alfatah_comparison_path)
                
                # Get product IDs that need price changes
                changed_product_ids = alfatah_comparison_df[alfatah_comparison_df['price_change_needed'] == 'YES']['product_id'].tolist()
                
                if changed_product_ids:
                    # Filter output to only include products with price changes
                    alfatah_filtered = alfatah_df[alfatah_df['product_id'].isin(changed_product_ids)]
                    if len(alfatah_filtered) > 0:
                        dfs_to_merge.append(alfatah_filtered)
                        total_products_with_changes += len(alfatah_filtered)
                        logger.info(f"📊 Al-Fatah: Added {len(alfatah_filtered)} products with price changes to consolidated")
            
            # Add Jalal Sons updates if available (only products with price changes)
            if self.results["Jalal Sons"]["updates_applied"] and os.path.exists(self.jalalsons_output_path) and os.path.exists(self.jalalsons_comparison_path):
                jalalsons_df = pd.read_csv(self.jalalsons_output_path)
                jalalsons_comparison_df = pd.read_csv(self.jalalsons_comparison_path)
                
                # Get product IDs that need price changes
                changed_product_ids = jalalsons_comparison_df[jalalsons_comparison_df['price_change_needed'] == 'YES']['product_id'].tolist()
                
                if changed_product_ids:
                    # Filter output to only include products with price changes
                    jalalsons_filtered = jalalsons_df[jalalsons_df['product_id'].isin(changed_product_ids)]
                    if len(jalalsons_filtered) > 0:
                        dfs_to_merge.append(jalalsons_filtered)
                        total_products_with_changes += len(jalalsons_filtered)
                        logger.info(f"📊 Jalal Sons: Added {len(jalalsons_filtered)} products with price changes to consolidated")
            
            # Add Rainbow updates if available (only products with price changes)
            if self.results["Rainbow"]["updates_applied"] and os.path.exists(self.rainbow_output_path) and os.path.exists(self.rainbow_comparison_path):
                rainbow_df = pd.read_csv(self.rainbow_output_path)
                rainbow_comparison_df = pd.read_csv(self.rainbow_comparison_path)
                
                # Get product IDs that need price changes
                changed_product_ids = rainbow_comparison_df[rainbow_comparison_df['price_change_needed'] == 'YES']['product_id'].tolist()
                
                if changed_product_ids:
                    # Filter output to only include products with price changes
                    rainbow_filtered = rainbow_df[rainbow_df['product_id'].isin(changed_product_ids)]
                    if len(rainbow_filtered) > 0:
                        dfs_to_merge.append(rainbow_filtered)
                        total_products_with_changes += len(rainbow_filtered)
                        logger.info(f"📊 Rainbow: Added {len(rainbow_filtered)} products with price changes to consolidated")
            
            # Add Metro updates if available (only products with price changes)
            if self.results["Metro"]["updates_applied"] and os.path.exists(self.metro_output_path) and os.path.exists(self.metro_comparison_path):
                metro_df = pd.read_csv(self.metro_output_path)
                metro_comparison_df = pd.read_csv(self.metro_comparison_path)
                
                # Get product IDs that need price changes
                changed_product_ids = metro_comparison_df[metro_comparison_df['price_change_needed'] == 'YES']['product_id'].tolist()
                
                if changed_product_ids:
                    # Filter output to only include products with price changes
                    metro_filtered = metro_df[metro_df['product_id'].isin(changed_product_ids)]
                    if len(metro_filtered) > 0:
                        dfs_to_merge.append(metro_filtered)
                        total_products_with_changes += len(metro_filtered)
                        logger.info(f"📊 Metro: Added {len(metro_filtered)} products with price changes to consolidated")
            
            # Add Imtiaz updates if available (only products with price changes)
            if self.results["Imtiaz"]["updates_applied"] and os.path.exists(self.imtiaz_output_path) and os.path.exists(self.imtiaz_comparison_path):
                imtiaz_df = pd.read_csv(self.imtiaz_output_path)
                imtiaz_comparison_df = pd.read_csv(self.imtiaz_comparison_path)
                
                # Get product IDs that need price changes
                changed_product_ids = imtiaz_comparison_df[imtiaz_comparison_df['price_change_needed'] == 'YES']['product_id'].tolist()
                
                if changed_product_ids:
                    # Filter output to only include products with price changes
                    imtiaz_filtered = imtiaz_df[imtiaz_df['product_id'].isin(changed_product_ids)]
                    if len(imtiaz_filtered) > 0:
                        dfs_to_merge.append(imtiaz_filtered)
                        total_products_with_changes += len(imtiaz_filtered)
                        logger.info(f"📊 Imtiaz: Added {len(imtiaz_filtered)} products with price changes to consolidated")
            
            # Merge if we have data from at least one store
            if dfs_to_merge:
                consolidated_df = pd.concat(dfs_to_merge, ignore_index=True)
                consolidated_df.to_csv(consolidated_path, index=False)
                logger.info(f"✅ Consolidated output saved to {consolidated_path}")
                logger.info(f"📊 Total products with price changes: {total_products_with_changes}")
                return consolidated_path
            else:
                logger.warning("⚠️  No products with price changes found to consolidate")
                return None
        
        except Exception as e:
            logger.error(f"❌ Error merging output files: {e}")
            return None
    
    def organize_reports(self) -> None:
        """Copy important files to the reports directory for better organization"""
        import shutil
        try:
            # Copy comparison files to reports directory
            comparison_files = [
                (self.alfatah_comparison_path, "Al-Fatah"),
                (self.jalalsons_comparison_path, "Jalal Sons"),
                (self.rainbow_comparison_path, "Rainbow"),
                (self.metro_comparison_path, "Metro"),
                (self.imtiaz_comparison_path, "Imtiaz")
            ]
            
            for file_path, store_name in comparison_files:
                if os.path.exists(file_path):
                    dest_path = os.path.join(self.reports_dir, os.path.basename(file_path))
                    shutil.copy2(file_path, dest_path)
                    logger.info(f"📋 Copied {store_name} comparison to reports: {dest_path}")
            
            # Copy updated files to reports directory  
            updated_files = [
                (self.alfatah_output_path, "Al-Fatah"),
                (self.jalalsons_output_path, "Jalal Sons"),
                (self.rainbow_output_path, "Rainbow"),
                (self.metro_output_path, "Metro"),
                (self.imtiaz_output_path, "Imtiaz")
            ]
            
            for file_path, store_name in updated_files:
                if os.path.exists(file_path):
                    dest_path = os.path.join(self.reports_dir, os.path.basename(file_path))
                    shutil.copy2(file_path, dest_path)
                    logger.info(f"📄 Copied {store_name} updated file to reports: {dest_path}")
                    
        except Exception as e:
            logger.error(f"❌ Error organizing reports: {e}")
    
    def generate_summary_report(self) -> None:
        """Generate a summary report of the price update process"""
        try:
            report_path = os.path.join(self.reports_dir, f"summary_report_{self.timestamp}.txt")
            
            # Create the report content
            report = f"""
🏪🏪 MULTI-STORE PRICE UPDATE REPORT 🏪🏪
=========================================
📅 Date: {self.timestamp}
📂 Input file: {self.input_csv_path}
📁 Output directory: {self.output_dir}

📊 PROCESS SUMMARY:
------------------
Al-Fatah Products Processed: {self.results["Al-Fatah"]["products"]}
Jalal Sons Products Processed: {self.results["Jalal Sons"]["products"]}
Rainbow Products Processed: {self.results["Rainbow"]["products"]}
Metro Products Processed: {self.results["Metro"]["products"]}
Imtiaz Products Processed: {self.results["Imtiaz"]["products"]}

🔍 COMPARISON GENERATION:
----------------------
Al-Fatah Comparison Generated: {"✅" if self.results["Al-Fatah"]["comparison_generated"] else "❌"}
Jalal Sons Comparison Generated: {"✅" if self.results["Jalal Sons"]["comparison_generated"] else "❌"}
Rainbow Comparison Generated: {"✅" if self.results["Rainbow"]["comparison_generated"] else "❌"}
Metro Comparison Generated: {"✅" if self.results["Metro"]["comparison_generated"] else "❌"}
Imtiaz Comparison Generated: {"✅" if self.results["Imtiaz"]["comparison_generated"] else "❌"}

🔄 CSV UPDATES APPLIED:
---------------------
Al-Fatah Updates Applied: {"✅" if self.results["Al-Fatah"]["updates_applied"] else "❌"}
Jalal Sons Updates Applied: {"✅" if self.results["Jalal Sons"]["updates_applied"] else "❌"}
Rainbow Updates Applied: {"✅" if self.results["Rainbow"]["updates_applied"] else "❌"}
Metro Updates Applied: {"✅" if self.results["Metro"]["updates_applied"] else "❌"}
Imtiaz Updates Applied: {"✅" if self.results["Imtiaz"]["updates_applied"] else "❌"}

📝 FILES GENERATED:
----------------
Al-Fatah Products: {os.path.basename(self.alfatah_csv_path) if self.results["Al-Fatah"]["products"] > 0 else "N/A"}
Al-Fatah Comparison: {os.path.basename(self.alfatah_comparison_path) if self.results["Al-Fatah"]["comparison_generated"] else "N/A"}
Al-Fatah Updated: {os.path.basename(self.alfatah_output_path) if self.results["Al-Fatah"]["updates_applied"] else "N/A"}

Jalal Sons Products: {os.path.basename(self.jalalsons_csv_path) if self.results["Jalal Sons"]["products"] > 0 else "N/A"}
Jalal Sons Comparison: {os.path.basename(self.jalalsons_comparison_path) if self.results["Jalal Sons"]["comparison_generated"] else "N/A"}
Jalal Sons Updated: {os.path.basename(self.jalalsons_output_path) if self.results["Jalal Sons"]["updates_applied"] else "N/A"}

Rainbow Products: {os.path.basename(self.rainbow_csv_path) if self.results["Rainbow"]["products"] > 0 else "N/A"}
Rainbow Comparison: {os.path.basename(self.rainbow_comparison_path) if self.results["Rainbow"]["comparison_generated"] else "N/A"}
Rainbow Updated: {os.path.basename(self.rainbow_output_path) if self.results["Rainbow"]["updates_applied"] else "N/A"}

Metro Products: {os.path.basename(self.metro_csv_path) if self.results["Metro"]["products"] > 0 else "N/A"}
Metro Comparison: {os.path.basename(self.metro_comparison_path) if self.results["Metro"]["comparison_generated"] else "N/A"}
Metro Updated: {os.path.basename(self.metro_output_path) if self.results["Metro"]["updates_applied"] else "N/A"}

Imtiaz Products: {os.path.basename(self.imtiaz_csv_path) if self.results["Imtiaz"]["products"] > 0 else "N/A"}
Imtiaz Comparison: {os.path.basename(self.imtiaz_comparison_path) if self.results["Imtiaz"]["comparison_generated"] else "N/A"}
Imtiaz Updated: {os.path.basename(self.imtiaz_output_path) if self.results["Imtiaz"]["updates_applied"] else "N/A"}

� CONSOLIDATED FILE NOTE:
-------------------------
The consolidated.csv file contains ONLY products where price_change_needed = 'YES'
Products with no price changes are excluded from the consolidated file.

�🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # Write to file
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            # Print to console
            logger.info("\n" + report)
            logger.info(f"📄 Summary report saved to: {report_path}")
            
        except Exception as e:
            logger.error(f"❌ Error generating summary report: {e}")


def run_price_update_workflow(input_csv_path: str, headless: bool = False, 
                              step1_only: bool = False, step2_only: bool = False) -> Dict:
    """
    Run the complete price update workflow for all supported stores: Al-Fatah, Jalal Sons, Rainbow, Metro, and Imtiaz.
    
    Args:
        input_csv_path (str): Path to the input CSV with products from multiple stores
        headless (bool): Run browsers in headless mode
        step1_only (bool): Only run Step 1 (comparison generation) 
        step2_only (bool): Only run Step 2 (apply CSV updates)
    
    Returns:
        Dict: Results of the workflow
    """
    try:
        logger.info(f"🚀 Starting multi-store price update workflow")
        updater = MultiStoreUpdater(input_csv_path, headless)
        
        # Step 0: Split input CSV by store
        if not step2_only:
            store_counts = updater.split_input_csv_by_store()
            logger.info(f"📊 Split input CSV by store: Al-Fatah ({store_counts['Al-Fatah']}), Jalal Sons ({store_counts['Jalal Sons']}), Rainbow ({store_counts['Rainbow']}), Metro ({store_counts['Metro']}), Imtiaz ({store_counts['Imtiaz']})")
        
        # Step 1: Generate price comparison CSVs
        if not step2_only:
            logger.info(f"🔍 Step 1: Generating price comparison CSVs")
            comparison_results = updater.generate_price_comparisons()
            
            if step1_only:
                logger.info("\n📝 Step 1 completed. Comparison CSVs generated.")
                if updater.results["Al-Fatah"]["comparison_generated"]:
                    logger.info(f"📁 Al-Fatah comparison CSV: {updater.alfatah_comparison_path}")
                if updater.results["Jalal Sons"]["comparison_generated"]:
                    logger.info(f"📁 Jalal Sons comparison CSV: {updater.jalalsons_comparison_path}")
                if updater.results["Rainbow"]["comparison_generated"]:
                    logger.info(f"📁 Rainbow comparison CSV: {updater.rainbow_comparison_path}")
                if updater.results["Metro"]["comparison_generated"]:
                    logger.info(f"📁 Metro comparison CSV: {updater.metro_comparison_path}")
                if updater.results["Imtiaz"]["comparison_generated"]:
                    logger.info(f"📁 Imtiaz comparison CSV: {updater.imtiaz_comparison_path}")
                logger.info("\n📋 NEXT STEPS:")
                logger.info(f"1. Review the comparison CSVs")
                logger.info(f"2. Run again with --step2-only flag to apply local CSV updates")
                updater.organize_reports()
                updater.generate_summary_report()
                return comparison_results
        
        # Step 2: Apply updates from comparison CSVs (local CSV updates)
        if not step1_only:
            logger.info(f"🔄 Step 2: Applying updates from comparison CSVs")
            
            # If running step2-only, check for existing comparison files and set flags
            if step2_only:
                updater.check_existing_comparison_files()
            
            update_results = updater.update_from_comparisons()
            
            # Merge output files
            consolidated_path = updater.merge_output_files()
            if consolidated_path:
                logger.info(f"📄 Consolidated output saved to: {consolidated_path}")
        

        # Organize reports and generate summary
        updater.organize_reports()
        updater.generate_summary_report()
        
        logger.info(f"✅ Multi-store price update workflow completed")
        return updater.results
        
    except Exception as e:
        logger.error(f"❌ Error in price update workflow: {e}")
        raise


if __name__ == "__main__":
    import argparse
    
    # Set up command-line arguments
    parser = argparse.ArgumentParser(description="Multi-store price updater for Al-Fatah, Jalal Sons, Rainbow, Metro, and Imtiaz")
    parser.add_argument("input_csv", help="Path to the input CSV with products from multiple stores")
    parser.add_argument("--headless", action="store_true", help="Run browsers in headless mode")
    parser.add_argument("--step1-only", action="store_true", help="Only run Step 1 (comparison generation)")
    parser.add_argument("--step2-only", action="store_true", help="Only run Step 2 (apply local CSV updates)")

    
    args = parser.parse_args()
    
    # Validate mutually exclusive options
    exclusive_flags = [args.step1_only, args.step2_only]
    if sum(exclusive_flags) > 1:
        logger.error("❌ Error: Cannot use multiple workflow flags (--step1-only, --step2-only) at the same time")
        exit(1)
    
    # Run the workflow
    run_price_update_workflow(
        input_csv_path=args.input_csv,
        headless=args.headless,
        step1_only=args.step1_only,
        step2_only=args.step2_only
    )
