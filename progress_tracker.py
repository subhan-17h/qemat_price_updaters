"""
Progress tracking utility for handling connection failures and resuming from last processed product.
"""

import pandas as pd
import os
from datetime import datetime
from typing import List, Optional, Dict, Set
import logging

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Tracks progress of product processing to enable resuming after connection failures.
    Saves progress to a CSV file after each product is processed.
    """
    
    def __init__(self, progress_file_path: str, store_name: str):
        """
        Initialize the progress tracker.
        
        Args:
            progress_file_path (str): Path to the progress tracking CSV file
            store_name (str): Name of the store (for logging)
        """
        self.progress_file_path = progress_file_path
        self.store_name = store_name
        self.progress_df = None
        self.processed_ids: Set[str] = set()
        
        # Create progress directory if it doesn't exist
        progress_dir = os.path.dirname(progress_file_path)
        if progress_dir:
            os.makedirs(progress_dir, exist_ok=True)
        
        # Load existing progress if available
        self.load_progress()
    
    def load_progress(self) -> None:
        """Load existing progress from the CSV file."""
        if os.path.exists(self.progress_file_path):
            try:
                self.progress_df = pd.read_csv(self.progress_file_path)
                self.processed_ids = set(self.progress_df['product_id'].astype(str).tolist())
                logger.info(f"📂 {self.store_name}: Loaded {len(self.processed_ids)} previously processed products from {self.progress_file_path}")
            except Exception as e:
                logger.warning(f"⚠️  {self.store_name}: Could not load progress file: {e}")
                self.progress_df = None
                self.processed_ids = set()
        else:
            logger.info(f"📝 {self.store_name}: No existing progress file found. Starting fresh.")
            self.progress_df = None
            self.processed_ids = set()
    
    def save_progress(self, product_id: str, status: str, old_price: Optional[float] = None, 
                      new_price: Optional[float] = None, error_message: Optional[str] = None) -> None:
        """
        Save progress for a single product.
        
        Args:
            product_id (str): Product ID
            status (str): Status - 'SUCCESS', 'ERROR', 'SKIPPED', 'NO_CHANGE'
            old_price (float, optional): Old price from CSV
            new_price (float, optional): New price from website
            error_message (str, optional): Error message if status is ERROR
        """
        try:
            # Create progress record
            progress_record = {
                'product_id': product_id,
                'status': status,
                'old_price': old_price,
                'new_price': new_price,
                'error_message': error_message if error_message else '',
                'timestamp': datetime.now().isoformat()
            }
            
            # Add to progress dataframe
            if self.progress_df is None:
                self.progress_df = pd.DataFrame([progress_record])
            else:
                # If product already exists, update it; otherwise append
                if product_id in self.processed_ids:
                    # Update existing record
                    mask = self.progress_df['product_id'].astype(str) == str(product_id)
                    for key, value in progress_record.items():
                        self.progress_df.loc[mask, key] = value
                else:
                    # Append new record
                    new_row_df = pd.DataFrame([progress_record])
                    self.progress_df = pd.concat([self.progress_df, new_row_df], ignore_index=True)
            
            # Add to processed set
            self.processed_ids.add(str(product_id))
            
            # Save to CSV
            self.progress_df.to_csv(self.progress_file_path, index=False)
            
        except Exception as e:
            logger.error(f"❌ {self.store_name}: Error saving progress for product {product_id}: {e}")
    
    def get_processed_ids(self) -> Set[str]:
        """
        Get set of already processed product IDs.
        
        Returns:
            Set[str]: Set of processed product IDs
        """
        return self.processed_ids
    
    def is_processed(self, product_id: str) -> bool:
        """
        Check if a product has already been processed.
        
        Args:
            product_id (str): Product ID to check
            
        Returns:
            bool: True if product has been processed, False otherwise
        """
        return str(product_id) in self.processed_ids
    
    def get_status(self, product_id: str) -> Optional[str]:
        """
        Get the status of a processed product.
        
        Args:
            product_id (str): Product ID
            
        Returns:
            Optional[str]: Status ('SUCCESS', 'ERROR', 'SKIPPED', 'NO_CHANGE') or None if not found
        """
        if self.progress_df is None or not self.is_processed(product_id):
            return None
        
        try:
            mask = self.progress_df['product_id'].astype(str) == str(product_id)
            status_series = self.progress_df.loc[mask, 'status']
            if not status_series.empty:
                return status_series.values[0]
        except Exception as e:
            logger.error(f"❌ {self.store_name}: Error getting status for product {product_id}: {e}")
        
        return None
    
    def get_error_ids(self) -> List[str]:
        """
        Get list of product IDs that had errors during processing.
        These should be retried on the next run.
        
        Returns:
            List[str]: List of product IDs with ERROR status
        """
        if self.progress_df is None:
            return []
        
        try:
            error_mask = self.progress_df['status'] == 'ERROR'
            return self.progress_df.loc[error_mask, 'product_id'].astype(str).tolist()
        except Exception as e:
            logger.error(f"❌ {self.store_name}: Error getting error IDs: {e}")
            return []
    
    def get_success_count(self) -> int:
        """Get count of successfully processed products."""
        if self.progress_df is None:
            return 0
        return len(self.progress_df[self.progress_df['status'] == 'SUCCESS'])
    
    def get_error_count(self) -> int:
        """Get count of products with errors."""
        if self.progress_df is None:
            return 0
        return len(self.progress_df[self.progress_df['status'] == 'ERROR'])
    
    def reset(self) -> None:
        """Clear all progress and delete the progress file."""
        try:
            if os.path.exists(self.progress_file_path):
                os.remove(self.progress_file_path)
                logger.info(f"🗑️  {self.store_name}: Progress file deleted: {self.progress_file_path}")
            
            self.progress_df = None
            self.processed_ids = set()
            
        except Exception as e:
            logger.error(f"❌ {self.store_name}: Error resetting progress: {e}")
    
    def get_summary(self) -> Dict[str, int]:
        """
        Get summary statistics of progress.
        
        Returns:
            Dict with counts for each status
        """
        if self.progress_df is None:
            return {'total': 0, 'success': 0, 'error': 0, 'skipped': 0, 'no_change': 0}
        
        try:
            summary = {
                'total': len(self.progress_df),
                'success': len(self.progress_df[self.progress_df['status'] == 'SUCCESS']),
                'error': len(self.progress_df[self.progress_df['status'] == 'ERROR']),
                'skipped': len(self.progress_df[self.progress_df['status'] == 'SKIPPED']),
                'no_change': len(self.progress_df[self.progress_df['status'] == 'NO_CHANGE'])
            }
            return summary
        except Exception as e:
            logger.error(f"❌ {self.store_name}: Error getting summary: {e}")
            return {'total': 0, 'success': 0, 'error': 0, 'skipped': 0, 'no_change': 0}
