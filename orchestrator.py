#!/usr/bin/env python3
"""
Main Orchestrator for Price Update and Firebase Sync
This script orchestrates the complete workflow:
1. Run main.py to update prices from stores
2. Run update_firebase.py to sync updated data to Firebase
"""

import subprocess
import sys
import logging
import os
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PriceUpdateOrchestrator:
    def __init__(self, input_csv: str = "test_with_matched.csv"):
        """
        Initialize the orchestrator
        
        Args:
            input_csv: Path to the input CSV file
        """
        self.input_csv = input_csv
        self.consolidated_csv = "consolidated.csv"
        
    def run_main_price_update(self) -> bool:
        """
        Run main.py to generate price updates
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("=" * 60)
            logger.info("STEP 1: Running Price Update Workflow")
            logger.info("=" * 60)
            
            # Run main.py with the input CSV
            cmd = [sys.executable, "main.py", self.input_csv]
            logger.info(f"Executing: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Print the output
            if result.stdout:
                print(result.stdout)
            
            logger.info("✅ Price update workflow completed successfully")
            
            # Check if consolidated.csv was generated
            if os.path.exists(self.consolidated_csv):
                logger.info(f"✅ Consolidated file found: {self.consolidated_csv}")
                return True
            else:
                logger.warning(f"⚠️  Warning: {self.consolidated_csv} not found")
                logger.warning("This may mean no price changes were detected")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error running price update workflow:")
            logger.error(f"Exit code: {e.returncode}")
            if e.stdout:
                logger.error(f"Output: {e.stdout}")
            if e.stderr:
                logger.error(f"Error: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False
    
    def run_firebase_update(self) -> bool:
        """
        Run update_firebase.py to sync data to Firebase
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("\n" + "=" * 60)
            logger.info("STEP 2: Syncing to Firebase")
            logger.info("=" * 60)
            
            # Check if consolidated.csv exists
            if not os.path.exists(self.consolidated_csv):
                logger.error(f"❌ {self.consolidated_csv} not found")
                logger.error("Cannot proceed with Firebase update")
                return False
            
            # Run update_firebase.py
            cmd = [sys.executable, "update_firebase.py"]
            logger.info(f"Executing: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Print the output
            if result.stdout:
                print(result.stdout)
            
            logger.info("✅ Firebase update completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error running Firebase update:")
            logger.error(f"Exit code: {e.returncode}")
            if e.stdout:
                logger.error(f"Output: {e.stdout}")
            if e.stderr:
                logger.error(f"Error: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False
    
    def run_complete_workflow(self) -> bool:
        """
        Run the complete orchestrated workflow
        
        Returns:
            bool: True if both steps successful, False otherwise
        """
        start_time = datetime.now()
        
        logger.info("\n" + "🚀" * 30)
        logger.info("PRICE UPDATE & FIREBASE SYNC ORCHESTRATOR")
        logger.info("🚀" * 30)
        logger.info(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Input CSV: {self.input_csv}\n")
        
        # Step 1: Run price update
        step1_success = self.run_main_price_update()
        
        if not step1_success:
            logger.error("\n❌ Workflow failed at Step 1: Price Update")
            logger.error("Firebase sync will not be performed")
            return False
        
        # Step 2: Run Firebase update
        step2_success = self.run_firebase_update()
        
        # Final summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("\n" + "=" * 60)
        logger.info("WORKFLOW SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Step 1 (Price Update): {'✅ SUCCESS' if step1_success else '❌ FAILED'}")
        logger.info(f"Step 2 (Firebase Sync): {'✅ SUCCESS' if step2_success else '❌ FAILED'}")
        logger.info(f"Total Duration: {duration:.2f} seconds")
        logger.info(f"Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        return step1_success and step2_success


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Orchestrate price updates and Firebase sync"
    )
    parser.add_argument(
        "input_csv",
        nargs="?",
        default="test_with_matched.csv",
        help="Path to input CSV file (default: test_with_matched.csv)"
    )
    parser.add_argument(
        "--step1-only",
        action="store_true",
        help="Only run Step 1 (price update)"
    )
    parser.add_argument(
        "--step2-only",
        action="store_true",
        help="Only run Step 2 (Firebase sync)"
    )
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = PriceUpdateOrchestrator(input_csv=args.input_csv)
    
    # Run workflow based on flags
    if args.step1_only:
        success = orchestrator.run_main_price_update()
    elif args.step2_only:
        success = orchestrator.run_firebase_update()
    else:
        success = orchestrator.run_complete_workflow()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
