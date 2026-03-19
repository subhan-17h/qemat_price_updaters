#type: ignore
import pandas as pd
import time
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Import progress tracker
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from progress_tracker import ProgressTracker

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImtiazPriceUpdater:
    def __init__(self, headless: bool = False):
        """
        Initialize the Imtiaz price updater (Local CSV only version)
        
        Args:
            headless (bool): Run browser in headless mode
        """
        self.base_url = "https://shop.imtiaz.com.pk"
        self.store_id = "Imtiaz"
        self.headless = headless
        self.driver = None
        self.location_selected = False
        
        # Statistics tracking
        self.stats = {
            'total': 0,
            'processed': 0,
            'price_changes': 0,
            'errors': 0,
            'unchanged': 0,
            'results': []
        }
        
    def _setup_driver(self):
        """Setup Chrome WebDriver with options"""
        try:
            chrome_options = Options()
            
            # Ubuntu-specific Chrome options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            
            if self.headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("✅ Chrome driver initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Chrome driver: {e}")
            return False
    
    def _test_website_connection(self) -> bool:
        """Send a test request to the base URL to ensure the website is responsive"""
        try:
            logger.info(f"🔍 Testing website connection to {self.base_url}...")
            self.driver.set_page_load_timeout(30)
            
            try:
                self.driver.get(self.base_url)
                time.sleep(2)  # Wait for page to load
                
                # Check if page loaded successfully (basic check)
                if "imtiaz" in self.driver.title.lower() or "imtiaz" in self.driver.current_url.lower():
                    logger.info("✅ Website connection test successful")
                    return True
                else:
                    logger.warning(f"⚠️  Website connection test completed but page may not have loaded correctly")
                    logger.info(f"   Page title: {self.driver.title}")
                    return True  # Still return True as we got some response
                    
            except Exception as e:
                logger.warning(f"⚠️  Website connection test failed: {e}")
                logger.info("   Will continue with product scraping anyway...")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️  Error during website connection test: {e}")
            return False
    
    def _select_dropdown_option(self, dropdown_input, option_text: str, dropdown_name: str) -> bool:
        """Select an option from a MUI autocomplete with readonly-safe fallbacks."""
        try:
            wait = WebDriverWait(self.driver, 12)

            # Open dropdown from input first.
            try:
                dropdown_input.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", dropdown_input)
            time.sleep(0.6)

            # For non-readonly inputs, typing helps filter options.
            readonly = (dropdown_input.get_attribute("readonly") or "").lower()
            if readonly not in ("", "false"):
                logger.info(f"   ℹ️ {dropdown_name} is readonly; selecting from list options directly")
            else:
                try:
                    dropdown_input.clear()
                    dropdown_input.send_keys(option_text)
                    logger.info(f"   📝 Typed '{option_text}' in {dropdown_name}")
                    time.sleep(0.8)
                except Exception as e:
                    logger.debug(f"   ⚠️ Could not type in {dropdown_name}: {e}")

            # Ensure listbox is visible (MUI popper).
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, "//ul[@role='listbox']")))
            except Exception:
                pass

            # Preferred exact/contains text options.
            option_selectors = [
                f"//li[@role='option'][.//span[normalize-space()='{option_text}'] or normalize-space()='{option_text}']",
                f"//li[@role='option'][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{option_text.lower()}')]",
                "//li[@role='option']",
            ]

            for selector in option_selectors:
                try:
                    options = self.driver.find_elements(By.XPATH, selector)
                    for option in options:
                        if not option.is_displayed():
                            continue

                        option_value = option.text.strip()
                        if selector.endswith("//li[@role='option']") or option_text.lower() in option_value.lower():
                            logger.info(f"   🎯 Found option candidate: '{option_value}'")
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'nearest'});", option)
                            time.sleep(0.2)
                            try:
                                option.click()
                            except Exception:
                                self.driver.execute_script("arguments[0].click();", option)
                            logger.info(f"   ✅ Selected '{option_value}' in {dropdown_name}")
                            time.sleep(0.8)
                            return True
                except Exception as e:
                    logger.debug(f"   ⚠️ Selector '{selector}' failed: {e}")

            # Keyboard fallback.
            from selenium.webdriver.common.keys import Keys
            dropdown_input.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.3)
            dropdown_input.send_keys(Keys.ENTER)
            logger.info(f"   ✅ Used keyboard fallback for {dropdown_name}")
            time.sleep(0.8)
            return True

        except Exception as e:
            logger.warning(f"   ⚠️ Error selecting option in {dropdown_name}: {e}")
            return False
    
    def _handle_location_selection(self):
        """Handle Imtiaz location modal robustly for cloud/headless runs."""
        try:
            if self.location_selected:
                return True

            logger.info("   🏪 Handling Imtiaz location selection...")
            wait = WebDriverWait(self.driver, 15)

            # If modal prompt isn't visible, assume location is already set.
            modal_markers = self.driver.find_elements(
                By.XPATH,
                "//*[contains(normalize-space(.), 'Please select your location') or contains(normalize-space(.), 'Select your order type')]",
            )
            if not any(m.is_displayed() for m in modal_markers):
                logger.info("   ℹ️ Location modal not visible; proceeding")
                self.location_selected = True
                return True

            # Prefer EXPRESS tab if available.
            try:
                express_tab = self.driver.find_element(
                    By.XPATH,
                    "//button[@role='tab' and contains(translate(normalize-space(.), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'EXPRESS')]",
                )
                if express_tab.get_attribute("aria-selected") != "true":
                    try:
                        express_tab.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", express_tab)
                    logger.info("   ✅ Selected EXPRESS order type")
            except Exception as e:
                logger.debug(f"   ℹ️ EXPRESS tab not adjusted: {e}")

            # Step 1: City selector
            logger.info("   📍 Step 1: Ensuring city selection...")
            city_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Select City / Region']"))
            )
            city_value = (city_input.get_attribute("value") or "").strip()
            if city_value:
                logger.info(f"   ✅ City pre-selected: {city_value}")
            else:
                if not self._select_dropdown_option(city_input, "Karachi", "City dropdown"):
                    logger.warning("   ⚠️ Could not reliably select city; continuing with fallback flow")

            # Step 2: Area selector
            logger.info("   📍 Step 2: Selecting area...")
            area_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Select Area / Sub Region']"))
            )
            area_value = (area_input.get_attribute("value") or "").strip()

            if not area_value:
                # Open area dropdown via popup indicator button.
                try:
                    popup_btn = self.driver.find_element(
                        By.XPATH,
                        "//input[@placeholder='Select Area / Sub Region']/ancestor::div[contains(@class, 'MuiAutocomplete-inputRoot')][1]//button[contains(@class, 'MuiAutocomplete-popupIndicator')]",
                    )
                    try:
                        popup_btn.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", popup_btn)
                    time.sleep(0.5)
                except Exception as e:
                    logger.debug(f"   ⚠️ Area popup button click failed: {e}")

                selected_area = self._select_dropdown_option(area_input, "Askari 1", "Area dropdown")
                if not selected_area:
                    selected_area = self._select_dropdown_option(area_input, "Askari", "Area dropdown")
                if not selected_area:
                    logger.warning("   ⚠️ Could not select preferred area from dropdown")

            # Step 3: click enabled Select button
            logger.info("   📍 Step 3: Submitting location...")
            select_btn = None
            try:
                select_btn = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Select' and not(@disabled)]"))
                )
            except Exception:
                # Fallback: any enabled button named Select.
                candidate_buttons = self.driver.find_elements(By.XPATH, "//button[contains(normalize-space(.), 'Select')]")
                for button in candidate_buttons:
                    if button.is_displayed() and button.is_enabled():
                        select_btn = button
                        break

            if select_btn is not None:
                try:
                    select_btn.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", select_btn)
                logger.info("   ✅ Clicked location Select button")
                time.sleep(2)
            else:
                logger.warning("   ⚠️ Select button not clickable; proceeding anyway")

            # Confirm modal is gone or at least not blocking.
            try:
                WebDriverWait(self.driver, 6).until_not(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(normalize-space(.), 'Please select your location')]"))
                )
                logger.info("   ✅ Location modal dismissed")
            except Exception:
                logger.info("   ℹ️ Location prompt still detectable, but continuing (may be non-blocking)")

            self.location_selected = True
            logger.info("   ✅ Location selection flow completed")
            return True

        except Exception as e:
            logger.error(f"   ❌ Error handling location selection: {e}")
            return False

    def _parse_price_value(self, text: str) -> Optional[float]:
        """Extract a numeric price from text with strict currency-aware parsing first."""
        if not text:
            return None

        normalized = text.replace("\n", " ").strip()
        currency_match = re.search(r"(?:Rs\.?|PKR|₨)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", normalized, flags=re.IGNORECASE)
        if currency_match:
            try:
                return float(currency_match.group(1).replace(",", ""))
            except ValueError:
                return None

        # Fallback for bare numbers in known price nodes.
        number_match = re.search(r"\b([0-9][0-9,]*(?:\.[0-9]{1,2})?)\b", normalized)
        if number_match:
            try:
                value = float(number_match.group(1).replace(",", ""))
                if value > 0:
                    return value
            except ValueError:
                return None

        return None
        
    def extract_price_from_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract current price from Imtiaz website"""
        try:
            logger.info(f"   🌐 Visiting: {url}")

            # Set page load timeout to 30 seconds
            self.driver.set_page_load_timeout(30)

            try:
                self.driver.get(url)
            except Exception as timeout_error:
                logger.error(f"   ⏱️ Page load timeout after 30 seconds: {url}")
                return None
            
            # Handle location selection if needed (only on first visit)
            if not self.location_selected:
                if not self._handle_location_selection():
                    logger.warning("   ⚠️ Could not handle location selection, continuing anyway...")
                    time.sleep(2)  # Wait a bit and continue
            
            # Wait for page to load
            time.sleep(3)

            # If modal still appears, do one more recovery attempt.
            modal_still_present = self.driver.find_elements(
                By.XPATH, "//*[contains(normalize-space(.), 'Please select your location')]"
            )
            if any(m.is_displayed() for m in modal_still_present):
                logger.info("   🔁 Location modal still present; retrying selection once")
                if not self._handle_location_selection():
                    logger.warning("   ⚠️ Location recovery retry failed")
                time.sleep(1.5)

            priority_selectors = [
                ".MuiBox-root.blink-style-1igmii2 .MuiBox-root span",
                ".MuiBox-root[class*='blink-style'] span",
                ".MuiTypography-root[class*='price']",
                ".price, .product-price, .current-price, .selling-price, .final-price, .amount",
                "[class*='price'] span, span[class*='price'], div[class*='price']",
            ]

            # Pass 1: currency-marked text only (most reliable).
            for selector in priority_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if not element.is_displayed():
                            continue

                        text = (
                            element.get_attribute("value")
                            if element.tag_name.lower() == "input"
                            else element.text.strip()
                        )
                        if not text:
                            continue

                        if not re.search(r"(?:Rs\.?|PKR|₨)", text, flags=re.IGNORECASE):
                            continue

                        price_value = self._parse_price_value(text)
                        if price_value and price_value > 0:
                            logger.info(f"   💰 Found price: Rs. {price_value} (selector: {selector})")
                            return {
                                'current_price': price_value,
                                'original_price': None,
                                'source_info': {
                                    'selector': selector,
                                    'original_text': text,
                                    'cleaned_text': str(price_value),
                                },
                                'is_sale': False,
                            }
                except Exception as e:
                    logger.debug(f"Error with selector '{selector}': {e}")

            # Pass 2: find any visible element containing currency text.
            try:
                currency_nodes = self.driver.find_elements(
                    By.XPATH,
                    "//*[self::span or self::div or self::p][contains(., 'Rs') or contains(., 'PKR') or contains(., '₨')]",
                )
                for node in currency_nodes:
                    if not node.is_displayed():
                        continue

                    text = node.text.strip()
                    price_value = self._parse_price_value(text)
                    if price_value and price_value > 0:
                        logger.info(f"   💰 Found price: Rs. {price_value} (currency-node fallback)")
                        return {
                            'current_price': price_value,
                            'original_price': None,
                            'source_info': {
                                'selector': 'currency-node-fallback',
                                'original_text': text,
                                'cleaned_text': str(price_value),
                            },
                            'is_sale': False,
                        }
            except Exception as e:
                logger.debug(f"Error in currency-node fallback: {e}")

            logger.warning(f"   ❌ No price found on page")
            return None
                
        except Exception as e:
            logger.error(f"   ❌ Error extracting price from {url}: {e}")
            return None
    
    def parse_price_history(self, price_history_data) -> List[Dict]:
        """Parse price history from CSV data"""
        try:
            if pd.isna(price_history_data) or price_history_data == '':
                return []
            
            # Handle different possible formats
            if isinstance(price_history_data, str):
                # Try to parse as JSON if it looks like JSON
                if price_history_data.startswith('[') or price_history_data.startswith('{'):
                    return json.loads(price_history_data)
            elif isinstance(price_history_data, list):
                return price_history_data
            
            return []
        except Exception as e:
            logger.warning(f"   ⚠️  Could not parse price history: {e}")
            return []
    
    def create_price_history_entry(self, price: float, is_current: bool = False) -> Dict:
        """Create new price history entry"""
        return {
            'price': price,
            'is_current': is_current,
            'timestamp': datetime.now().isoformat()
        }
    
    def update_price_history(self, current_history: List[Dict], new_price: float) -> List[Dict]:
        """Update price history array"""
        # Set all existing entries to is_current: false
        updated_history = []
        for entry in current_history:
            updated_entry = entry.copy()
            updated_entry['is_current'] = False
            updated_history.append(updated_entry)
        
        # Add new entry as current
        updated_history.append(self.create_price_history_entry(new_price, True))
        
        return updated_history
    
    def generate_comparison_csv(self, input_csv_path: str, output_csv_path: str = None, delay_seconds: int = 3, progress_tracker: Optional[ProgressTracker] = None) -> Dict:
        """Generate comparison CSV for manual review"""
        try:
            if not output_csv_path:
                timestamp = datetime.now().strftime('%Y-%m-%d')
                output_csv_path = f'imtiaz_price_comparison_{timestamp}.csv'
            
            # Initialize browser
            if not self._setup_driver():
                raise Exception("Failed to initialize browser")
            
            logger.info(f"📄 Reading CSV file: {input_csv_path}")
            df = pd.read_csv(input_csv_path)
            
            self.stats['total'] = len(df)
            logger.info(f"📊 Found {self.stats['total']} products to check\n")
            
            # Test website connection before processing products
            self._test_website_connection()
            
            comparison_data = []
            
            for index, product in df.iterrows():
                progress = f"[{index + 1}/{self.stats['total']}]"
                product_name = product.get('name', 'Unknown Product')
                
                logger.info(f"{progress} 🔍 Checking: {product_name}")
                
                # Create base comparison row
                comparison_row = {
                    'product_id': product.get('product_id'),
                    'old_price': product.get('price'),
                    'new_price': None,
                    'price_change_needed': 'NO'
                }
                
                # Parse current price history
                current_price_history = self.parse_price_history(product.get('price_history'))
                
                # Skip if no URL
                if pd.isna(product.get('original_url')) or not product.get('original_url'):
                    logger.warning(f"{progress} ⏭️  Skipping - No original_url provided")
                    comparison_row['price_change_needed'] = 'ERROR - No URL'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                    continue
                
                csv_price = product.get('price')
                if pd.isna(csv_price) or csv_price <= 0:
                    logger.warning(f"{progress} ⏭️  Skipping - Invalid CSV price: {csv_price}")
                    comparison_row['price_change_needed'] = 'ERROR - Invalid Price'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                    continue
                
                logger.info(f"   📋 CSV Price: Rs. {csv_price}")
                logger.info(f"   📚 Price History: {len(current_price_history)} entries")
                
                # Get current price from website
                website_data = self.extract_price_from_page(product['original_url'])
                
                if not website_data:
                    logger.warning(f"{progress} ❌ Could not fetch website price (possible timeout)")
                    comparison_row['price_change_needed'] = 'ERROR - Page timeout or failed to load'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                elif not website_data.get('current_price'):
                    logger.warning(f"{progress} ❌ Could not extract price from page")
                    comparison_row['price_change_needed'] = 'ERROR - Price not found on page'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                else:
                    website_price = website_data['current_price']
                    price_difference = website_price - csv_price
                    
                    # Update comparison row with website data
                    comparison_row['new_price'] = website_price
                    
                    # Determine if price change is needed
                    if abs(price_difference) < 0.01:
                        logger.info(f"{progress} ✅ Prices match - No update needed")
                        comparison_row['price_change_needed'] = 'NO'
                        self.stats['unchanged'] += 1
                    else:
                        logger.info(f"{progress} 🔄 Price difference: Rs. {price_difference:.2f}")
                        logger.info(f"   📋 CSV: Rs. {csv_price}")
                        logger.info(f"   🌐 Website: Rs. {website_price}")
                        comparison_row['price_change_needed'] = 'YES'
                        self.stats['price_changes'] += 1
                    
                    comparison_data.append(comparison_row)
                    self.stats['processed'] += 1
                
                logger.info('')
                
                # Rate limiting (longer delay for Jalal Sons)
                if index < len(df) - 1:
                    logger.info(f"   ⏳ Waiting {delay_seconds}s before next request...")
                    time.sleep(delay_seconds)
            
            # Save comparison CSV
            comparison_df = pd.DataFrame(comparison_data)
            comparison_df.to_csv(output_csv_path, index=False)
            
            logger.info(f"\n✅ Comparison CSV generated: {output_csv_path}")
            logger.info(f"📊 Summary: {self.stats['processed']} checked, {self.stats['price_changes']} need updates, {self.stats['unchanged']} unchanged, {self.stats['errors']} errors")
            
            logger.info(f"\n📝 NEXT STEPS:")
            logger.info(f"1. Open {output_csv_path}")
            logger.info(f"2. Review products where 'price_change_needed' = 'YES'")
            logger.info(f"3. Run update_local_from_reviewed_csv('{output_csv_path}', 'your_original.csv') to apply changes")
            
            return {
                'output_file': output_csv_path,
                'stats': self.stats,
                'comparison_data': comparison_data
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating comparison CSV: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
                logger.info('🔚 Browser closed')
    
    def update_local_from_reviewed_csv(self, reviewed_csv_path: str, original_csv_path: str, output_csv_path: str = None) -> Dict:
        """Update local CSV from comparison CSV
        
        Args:
            reviewed_csv_path (str): Path to the comparison CSV with 4 columns
            original_csv_path (str): Path to the original products CSV to update
            output_csv_path (str): Output path for updated CSV (defaults to overwriting original)
        """
        try:
            logger.info(f"📄 Reading comparison CSV: {reviewed_csv_path}")
            comparison_df = pd.read_csv(reviewed_csv_path)
            
            # Verify required columns exist
            required_columns = ['product_id', 'old_price', 'new_price', 'price_change_needed']
            if not all(col in comparison_df.columns for col in required_columns):
                raise ValueError(f"Comparison CSV must contain these columns: {required_columns}")
            
            # Read the original products CSV
            logger.info(f"📄 Reading original products CSV: {original_csv_path}")
            original_df = pd.read_csv(original_csv_path)
            
            # Create output path if not provided (default to overwriting the original)
            if not output_csv_path:
                output_csv_path = original_csv_path
                # Create a backup of the original file
                backup_path = f"{original_csv_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                logger.info(f"📑 Creating backup of original file: {backup_path}")
                original_df.to_csv(backup_path, index=False)
            
            # Filter for entries that need price changes (YES only)
            changes_needed_df = comparison_df[comparison_df['price_change_needed'] == 'YES']
            
            logger.info(f"📊 Found {len(changes_needed_df)} products that need price updates\n")
            
            if len(changes_needed_df) == 0:
                logger.warning('⚠️  No price changes needed. Exiting.')
                return {'updated': 0, 'errors': 0, 'updates': []}
            
            update_results = {
                'updated': 0,
                'errors': 0,
                'updates': []
            }
            
            # Create a copy of the original dataframe to update
            updated_df = original_df.copy()
            
            for index, product in changes_needed_df.iterrows():
                progress = f"[{index + 1}/{len(changes_needed_df)}]"
                
                product_id = product['product_id']
                old_price = float(product['old_price'])
                new_price = float(product['new_price'])
                
                logger.info(f"{progress} 🔄 Updating product: {product_id}")
                logger.info(f"   💰 {old_price} → {new_price}")
                
                try:
                    # Find the matching row in the original dataframe
                    mask = updated_df['product_id'] == product_id
                    if mask.any():
                        # Update the price
                        updated_df.loc[mask, 'price'] = new_price
                        
                        # Update price_history if it exists
                        if 'price_history' in updated_df.columns:
                            # Parse current price history
                            current_price_history = self.parse_price_history(updated_df.loc[mask, 'price_history'].values[0])
                            # Update price history
                            updated_price_history = self.update_price_history(current_price_history, new_price)
                            updated_df.loc[mask, 'price_history'] = json.dumps(updated_price_history)
                        
                        # Update last_updated if it exists
                        if 'last_updated' in updated_df.columns:
                            updated_df.loc[mask, 'last_updated'] = datetime.now().isoformat()
                        
                        # Get product name if available
                        product_name = updated_df.loc[mask, 'name'].values[0] if 'name' in updated_df.columns else f"Product {product_id}"
                        
                        logger.info(f"{progress} ✅ Successfully updated: {product_name}")
                        update_results['updated'] += 1
                        update_results['updates'].append({
                            'name': product_name,
                            'product_id': product_id,
                            'old_price': old_price,
                            'new_price': new_price,
                            'price_history_entries': len(current_price_history) + 1 if 'price_history' in updated_df.columns else 1
                        })
                    else:
                        logger.error(f"{progress} ❌ Could not find product with ID {product_id} in original CSV")
                        update_results['errors'] += 1
                except Exception as e:
                    logger.error(f"{progress} ❌ Error updating data for product {product_id}: {e}")
                    update_results['errors'] += 1
                
                logger.info('')
            
            # Save the updated dataframe
            updated_df.to_csv(output_csv_path, index=False)
            logger.info(f"📄 Updated CSV saved to: {output_csv_path}")
            
            self._generate_update_report(update_results)
            return update_results
            
        except Exception as e:
            logger.error(f"❌ Error updating local CSV: {e}")
            raise
    
    def _generate_update_report(self, results: Dict):
        """Generate update report"""
        report = f"""
🏪 JALAL SONS PRICE UPDATE REPORT
=================================
✅ Successfully Updated: {results['updated']}
❌ Errors/Skipped: {results['errors']}

📝 PRICE UPDATES MADE:
"""
        
        if results['updates']:
            for update in results['updates']:
                report += f"""• {update['name']}
  Price: Rs. {update['old_price']} → Rs. {update['new_price']}
  Product ID: {update['product_id']}
  Price History Entries: {update['price_history_entries']}
"""
        else:
            report += "(No updates were made)\n"
        
        report += f"\n🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        logger.info('\n' + report)
        
        # Save report to file in reports folder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        reports_dir = 'reports'
        os.makedirs(reports_dir, exist_ok=True)  # Create reports directory if it doesn't exist
        report_filename = f'imtiaz_update_report_{timestamp}.txt'
        report_path = os.path.join(reports_dir, report_filename)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"📄 Report saved to: {report_path}")


# MAIN EXECUTION FUNCTIONS

def generate_price_comparison(
    csv_file_path: str,
    output_path: str = None,
    delay_seconds: int = 3,
    progress_tracker: Optional[ProgressTracker] = None,
    headless: bool = False,
) -> Dict:
    """Generate comparison CSV for manual review"""
    updater = ImtiazPriceUpdater(headless=headless)
    
    try:
        results = updater.generate_comparison_csv(csv_file_path, output_path, delay_seconds, progress_tracker)
        logger.info(f"\n🎉 Price comparison completed!")
        return results
    except Exception as e:
        logger.error(f"💥 Error generating comparison: {e}")
        raise

def update_local_from_reviewed_csv(reviewed_csv_path: str, original_csv_path: str, output_csv_path: str = None) -> Dict:
    """Update local CSV from comparison CSV"""
    updater = ImtiazPriceUpdater(headless=False)
    
    try:
        results = updater.update_local_from_reviewed_csv(reviewed_csv_path, original_csv_path, output_csv_path)
        logger.info(f"\n🎉 Local CSV update completed!")
        logger.info(f"📊 Summary: {results['updated']} updated, {results['errors']} errors")
        return results
    except Exception as e:
        logger.error(f"💥 Error updating local CSV: {e}")
        raise

# USAGE EXAMPLES:
if __name__ == "__main__":
    # Step 1: Generate comparison CSV
    # This will create a CSV with columns: product_id, old_price, new_price, price_change_needed
    generate_price_comparison('2.csv')
    
    # # Step 2: Update local CSV with changes
    # # This will update only products where price_change_needed = 'YES'
    # update_local_from_reviewed_csv(
    #     reviewed_csv_path='imtiaz_price_comparison_2025-09-26.csv',
    #     original_csv_path='2.csv',
    #     output_csv_path='updated_imtiaz_products.csv'  # Optional: defaults to overwriting original
    # )
