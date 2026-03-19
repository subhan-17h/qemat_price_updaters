// Upload CSV to Firebase - Matched Products Collection (UPDATE EXISTING ONLY)
// Expected CSV columns: product_id, name, category, price, store_id, image_url,
// original_url, created_at, last_updated, price_history, matched_products,
// matched_products_count, categoryNameVariations
//
// This script updates ONLY existing documents in Firebase with:
// - price
// - price_history array
// - last_updated (current timestamp)
//
// Documents that don't exist in Firebase are SKIPPED (not created)
import fs from 'fs';
import path from 'path';
import admin from 'firebase-admin';
import Papa from 'papaparse';
import { createRequire } from 'module';

// Create require function for ES modules
const require = createRequire(import.meta.url);

// Initialize Firebase Admin with error handling
try {
  admin.initializeApp({
      credential: admin.credential.cert(require("../serviceAccountKey.json")),
      storageBucket: "qemat-a2a2c.firebasestorage.app"
  });
  console.log('✅ Firebase Admin initialized successfully');
} catch (error) {
  console.error('❌ Failed to initialize Firebase Admin:', error.message);
  console.error('💡 Please check your serviceAccountKey.json file');
  process.exit(1);
}

const db = admin.firestore();

// Updated processCSVRow function with NaN handling
function processCSVRow(row, rowIndex, updateTimestamp = true) {
  const errors = [];
  
  try {
    // Validate required fields
    const requiredFields = ['product_id', 'name', 'category', 'price', 'store_id'];
    for (const field of requiredFields) {
      if (!row[field] || row[field].trim() === '') {
        errors.push(`Missing required field: ${field}`);
      }
    }
    
    if (errors.length > 0) {
      return { success: false, errors };
    }
    
    const currentTimestamp = new Date().toISOString();
    
    // Helper function to parse JSON arrays with NaN handling
    const parseJSONArray = (jsonString, fieldName) => {
      if (!jsonString || jsonString.trim() === '') {
        return [];
      }
      
      try {
        // First, clean up NaN values in the JSON string
        let cleanedJsonString = jsonString
          .replace(/:\s*NaN\s*([,\}])/g, ': null$1')  // Replace NaN with null
          .replace(/"\s*NaN\s*"/g, '""');             // Replace "NaN" strings with empty strings
        
        const parsedArray = JSON.parse(cleanedJsonString);
        
        // Validate that it's an array
        if (!Array.isArray(parsedArray)) {
          errors.push(`${fieldName} must be an array`);
          return null;
        }
        
        return parsedArray;
      } catch (parseError) {
        console.log(`❌ JSON Parse Error for ${fieldName} in row ${rowIndex}:`);
        console.log(`   Original: ${jsonString.substring(0, 200)}...`);
        errors.push(`Invalid JSON in ${fieldName}: ${parseError.message}`);
        return null;
      }
    };

    // Parse matched_products JSON string with NaN handling
    let matchedProducts = parseJSONArray(row.matched_products, 'matched_products');
    if (matchedProducts === null) {
      return { success: false, errors };
    }
    
    // Clean up any remaining malformed data in matched products and update timestamps
    if (matchedProducts.length > 0) {
      matchedProducts = matchedProducts.map(product => {
        // Fix the last_updated field if it's "[object Object]" or update if requested
        let lastUpdated = product.last_updated;
        if (product.last_updated === "[object Object]") {
          lastUpdated = product.created_at || currentTimestamp;
        }
        
        // Update timestamp if requested
        if (updateTimestamp) {
          lastUpdated = currentTimestamp;
        }
        
        // Helper function to clean NaN values
        const cleanValue = (value, fallback = '') => {
          if (value === null || value === undefined || 
              (typeof value === 'number' && isNaN(value)) ||
              value === 'NaN' || value === NaN) {
            return fallback;
          }
          return value;
        };
        
        // Helper function to clean numeric values
        const cleanNumericValue = (value, fallback = 0) => {
          const parsed = parseFloat(value);
          return isNaN(parsed) ? fallback : parsed;
        };
        
        return {
          document_id: cleanValue(product.document_id, ''),
          product_id: cleanValue(product.product_id, ''),
          name: cleanValue(product.name, ''),
          category: cleanValue(product.category, ''),
          price: cleanNumericValue(product.price, 0),
          store_id: cleanValue(product.store_id, ''),
          image_url: cleanValue(product.image_url, ''),
          original_url: cleanValue(product.original_url, ''),
          created_at: cleanValue(product.created_at, ''),
          last_updated: lastUpdated
        };
      });
    }
    
    // Parse price_history array
    let priceHistory = parseJSONArray(row.price_history, 'price_history');
    if (priceHistory === null) {
      return { success: false, errors };
    }
    
    // Parse categoryNameVariations array
    let categoryNameVariations = parseJSONArray(row.categoryNameVariations, 'categoryNameVariations');
    if (categoryNameVariations === null) {
      return { success: false, errors };
    }
    
    // Determine last_updated for main document
    let mainLastUpdated = row.last_updated ? row.last_updated.trim() : '';
    if (updateTimestamp) {
      mainLastUpdated = currentTimestamp;
    }
    
    // Helper function to clean main document values
    const cleanMainValue = (value, fallback = '') => {
      if (value === null || value === undefined || 
          (typeof value === 'number' && isNaN(value)) ||
          value === 'NaN' || value === NaN) {
        return fallback;
      }
      return typeof value === 'string' ? value.trim() : String(value);
    };
    
    // Create the document structure with cleaned values
    const document = {
      product_id: row.product_id.trim(),
      name: row.name.trim(),
      category: row.category.trim(),
      price: parseFloat(row.price) || 0,
      store_id: row.store_id.trim(),
      image_url: cleanMainValue(row.image_url, ''),
      original_url: cleanMainValue(row.original_url, ''),
      created_at: cleanMainValue(row.created_at, ''),
      last_updated: mainLastUpdated,
      price_history: priceHistory,
      matched_products_count: parseInt(row.matched_products_count) || matchedProducts.length,
      matched_products: matchedProducts,
      categoryNameVariations: categoryNameVariations
    };
    
    return { success: true, document };
    
  } catch (error) {
    console.log(`❌ Row processing error for row ${rowIndex}: ${error.message}`);
    return { success: false, errors: [`Row processing error: ${error.message}`] };
  }
}

// Function to read and parse CSV file
function parseCSVFile(csvFilePath) {
  try {
    console.log(`📖 Reading CSV file: ${csvFilePath}`);
    
    if (!fs.existsSync(csvFilePath)) {
      throw new Error(`CSV file not found: ${csvFilePath}`);
    }
    
    const csvContent = fs.readFileSync(csvFilePath, 'utf8');
    
    // Parse CSV with Papa Parse
    const parseResult = Papa.parse(csvContent, {
      header: true,
      skipEmptyLines: true,
      dynamicTyping: false, // Keep everything as strings initially
      transformHeader: (header) => header.trim() // Clean up headers
    });
    
    if (parseResult.errors && parseResult.errors.length > 0) {
      console.log('⚠️  CSV parsing warnings:');
      parseResult.errors.forEach(error => {
        console.log(`  • Row ${error.row}: ${error.message}`);
      });
    }
    
    console.log(`📊 Found ${parseResult.data.length} rows in CSV`);
    
    return parseResult.data;
    
  } catch (error) {
    console.error('❌ Error reading CSV file:', error);
    throw error;
  }
}

// Function to process CSV data into Firebase documents
function processCSVData(csvData, updateTimestamp = true) {
  const processedData = [];
  const errors = [];
  let successCount = 0;
  
  console.log('🔄 Processing CSV data...');
  console.log(`⏰ Update timestamps: ${updateTimestamp ? 'YES' : 'NO'}`);
  
  csvData.forEach((row, index) => {
    const result = processCSVRow(row, index + 1, updateTimestamp);
    
    if (result.success) {
      processedData.push({
        docId: result.document.product_id, // Use product_id as document ID
        data: result.document
      });
      successCount++;
    } else {
      errors.push({
        row: index + 1,
        product_id: row.product_id || 'Unknown',
        errors: result.errors
      });
    }
    
    // Progress indicator
    if ((index + 1) % 100 === 0) {
      console.log(`📊 Processed ${index + 1}/${csvData.length} rows`);
    }
  });
  
  console.log(`📊 Processing complete!`);
  console.log(`✅ Successfully processed: ${successCount} rows`);
  console.log(`❌ Errors: ${errors.length} rows`);
  
  if (errors.length > 0) {
    console.log('\n❌ Processing errors:');
    errors.slice(0, 10).forEach(error => {
      console.log(`  • Row ${error.row} (${error.product_id}): ${error.errors.join(', ')}`);
    });
    if (errors.length > 10) {
      console.log(`  ... and ${errors.length - 10} more errors`);
    }
  }
  
  return { processedData, errors, successCount };
}

// Function to check which documents exist in Firebase
async function checkExistingDocuments(productIds, collectionName = 'matched_products') {
  const existingDocs = new Set();
  const newDocs = new Set();
  
  console.log(`🔍 Checking existence of ${productIds.length} products in Firebase...`);
  
  // Process in batches of 10 (Firestore 'in' query limit)
  const batchSize = 10;
  for (let i = 0; i < productIds.length; i += batchSize) {
    const batch = productIds.slice(i, i + batchSize);
    
    try {
      const query = db.collection(collectionName).where('product_id', 'in', batch);
      const snapshot = await query.get();
      
      snapshot.forEach(doc => {
        existingDocs.add(doc.data().product_id);
      });
      
      // Add remaining IDs to new docs set
      batch.forEach(id => {
        if (!existingDocs.has(id)) {
          newDocs.add(id);
        }
      });
      
      if ((i + batchSize) % 100 === 0 || i + batchSize >= productIds.length) {
        console.log(`📊 Checked ${Math.min(i + batchSize, productIds.length)}/${productIds.length} products`);
      }
      
    } catch (error) {
      console.error(`❌ Error checking batch ${i}-${i + batchSize}:`, error);
      // If query fails, assume all in this batch are new
      batch.forEach(id => newDocs.add(id));
    }
  }
  
  console.log(`📊 Found ${existingDocs.size} existing documents, ${newDocs.size} new documents`);
  
  return { existingDocs, newDocs };
}

// Function to update only specific fields in existing Firebase documents
async function updateExistingDocuments(processedData, collectionName = 'matched_products') {
  let batch = db.batch();
  let batchCount = 0;
  const batchLimit = 500; // Firestore batch limit
  let totalProcessed = 0;
  let updatedCount = 0;
  let skippedCount = 0;

  try {
    console.log(`🔄 Starting update of existing documents in '${collectionName}' collection...`);

    // Get list of all product IDs to check
    const productIds = processedData.map(item => item.docId);
    const { existingDocs, newDocs } = await checkExistingDocuments(productIds, collectionName);

    console.log('\n📝 UPDATE OPERATION SUMMARY:');
    console.log(`✅ Documents to UPDATE: ${existingDocs.size}`);
    console.log(`⏭️  Documents to SKIP (not found): ${newDocs.size}`);
    console.log(`📊 Total documents in CSV: ${processedData.length}\n`);

    for (const { docId, data } of processedData) {
      const docRef = db.collection(collectionName).doc(docId);

      if (existingDocs.has(docId)) {
        // Document exists - update only the 3 specified fields
        const updateData = {
          price: data.price,
          price_history: data.price_history,
          last_updated: data.last_updated
        };

        batch.update(docRef, updateData);
        updatedCount++;
        totalProcessed++;
      } else {
        // Document doesn't exist - skip it
        skippedCount++;
      }

      batchCount++;

      // Execute batch when limit is reached
      if (batchCount >= batchLimit) {
        await batch.commit();
        console.log(`📤 Processed batch: ${totalProcessed - batchCount + 1}-${totalProcessed} documents`);
        batchCount = 0;
        batch = db.batch();
      }
    }

    // Commit remaining documents
    if (batchCount > 0) {
      await batch.commit();
      console.log(`📤 Processed final batch: ${totalProcessed - batchCount + 1}-${totalProcessed} documents`);
    }

    console.log('\n✅ UPDATE COMPLETE!');
    console.log(`📊 Total in CSV: ${processedData.length} documents`);
    console.log(`🔄 Updated existing: ${updatedCount} documents`);
    console.log(`⏭️  Skipped (not found): ${skippedCount} documents`);
    console.log(`📚 Collection: '${collectionName}'`);
    console.log(`📝 Fields updated: price, price_history, last_updated`);

    return { totalProcessed, updatedCount, skippedCount };

  } catch (error) {
    console.error('❌ Error during update operation:', error);

    // Specific error handling
    if (error.code === 16 || error.reason === 'ACCESS_TOKEN_EXPIRED') {
      console.error('🔑 Authentication Error: Your Firebase credentials have expired.');
      console.error('💡 Solutions:');
      console.error('   1. Regenerate your serviceAccountKey.json from Firebase Console');
      console.error('   2. Check if the file exists and has proper permissions');
      console.error('   3. Verify the file path is correct');
    }

    throw error;
  }
}

// Function to save processing report (updated for field-specific updates)
function saveProcessingReport(csvFilePath, processResult, updateResult, outputFolder = './output', updateTimestamp = true) {
  try {
    // Create output folder if it doesn't exist
    if (!fs.existsSync(outputFolder)) {
      fs.mkdirSync(outputFolder, { recursive: true });
      console.log(`📁 Created output folder: ${outputFolder}`);
    }

    const csvFileName = path.basename(csvFilePath, '.csv');
    const reportFile = path.join(outputFolder, `matched_products_update_report_${csvFileName}.txt`);

    const report = `
MATCHED PRODUCTS UPDATE REPORT
==============================
Input CSV file: ${csvFilePath}
Collection: matched_products
Operation: UPDATE existing documents only (NO creation)
Fields updated: price, price_history, last_updated
Update timestamps: ${updateTimestamp ? 'YES' : 'NO'}

CSV PROCESSING RESULTS:
Total rows in CSV: ${processResult.processedData.length + processResult.errors.length}
Successfully processed: ${processResult.successCount}
Processing errors: ${processResult.errors.length}

FIREBASE UPDATE RESULTS:
${updateResult ? `
Total documents in CSV: ${processResult.processedData.length}
Existing documents updated: ${updateResult.updatedCount}
Documents skipped (not found in Firebase): ${updateResult.skippedCount}
` : 'Update operation not completed'}

${processResult.errors.length > 0 ? `PROCESSING ERRORS:\n${processResult.errors.map(e =>
  `Row ${e.row} (${e.product_id}): ${e.errors.join(', ')}`
).join('\n')}` : 'No processing errors encountered'}

Generated at: ${new Date().toISOString()}
    `;

    fs.writeFileSync(reportFile, report);
    console.log(`📋 Processing report saved to: ${reportFile}`);

    return reportFile;

  } catch (error) {
    console.error('❌ Error saving report:', error);
  }
}

// Main function to process CSV and update existing Firebase documents
async function updateExistingFromCSV(csvFilePath, collectionName = 'matched_products', updateTimestamp = true) {
  try {
    console.log('🚀 Starting CSV to Firebase UPDATE process...\n');
    console.log(`⏰ Timestamp update mode: ${updateTimestamp ? 'ENABLED' : 'DISABLED'}`);
    console.log(`🔄 Operation mode: UPDATE existing documents only (NO creation)`);
    console.log(`📝 Fields to update: price, price_history, last_updated`);

    // Step 1: Parse CSV file
    const csvData = parseCSVFile(csvFilePath);

    if (csvData.length === 0) {
      console.log('📭 No data found in CSV file.');
      return;
    }

    // Step 2: Process CSV data
    const processResult = processCSVData(csvData, updateTimestamp);

    if (processResult.processedData.length === 0) {
      console.log('📭 No valid data to upload after processing.');
      return;
    }

    // Step 3: Update existing Firebase documents
    console.log('\n' + '='.repeat(60));
    console.log('📤 UPDATING EXISTING FIREBASE DOCUMENTS');
    console.log('='.repeat(60));
    console.log(`⚠️  This will process ${processResult.processedData.length} documents from '${collectionName}' collection!`);
    console.log('✅ Only EXISTING documents will be UPDATED');
    console.log('⏭️  Non-existing documents will be SKIPPED');
    console.log('📝 Only updating: price, price_history, last_updated fields');
    if (updateTimestamp) {
      console.log('⏰ last_updated will be set to current timestamp');
    }
    console.log('🔄 Starting update process...\n');

    const updateResult = await updateExistingDocuments(processResult.processedData, collectionName);

    // Step 4: Save processing report
    const reportFile = saveProcessingReport(csvFilePath, processResult, updateResult, './output', updateTimestamp);

    console.log('\n🎉 CSV update process completed successfully!');
    console.log(`📋 Check the report file for details: ${reportFile}`);

    return updateResult;

  } catch (error) {
    console.error('❌ CSV update process failed:', error);
    throw error;
  }
}

// Function to update existing Firebase documents with new timestamps only
async function updateTimestampsOnly(collectionName = 'matched_products') {
  try {
    console.log('🔄 Starting timestamp update process...\n');
    console.log(`⏰ Updating all last_updated fields in '${collectionName}' collection...`);
    
    const currentTimestamp = new Date().toISOString();
    let batch = db.batch();
    let batchCount = 0;
    const batchLimit = 500;
    let totalUpdated = 0;
    
    // Get all documents from the collection
    const snapshot = await db.collection(collectionName).get();
    
    if (snapshot.empty) {
      console.log('📭 No documents found in collection.');
      return;
    }
    
    console.log(`📊 Found ${snapshot.size} documents to update`);
    
    snapshot.forEach(doc => {
      const data = doc.data();
      
      // Update main document last_updated
      const updatedData = {
        ...data,
        last_updated: currentTimestamp
      };
      
      // Update last_updated in matched_products array
      if (data.matched_products && Array.isArray(data.matched_products)) {
        updatedData.matched_products = data.matched_products.map(product => ({
          ...product,
          last_updated: currentTimestamp
        }));
      }
      
      // Ensure new fields exist with default values if not present
      if (!data.hasOwnProperty('price_history')) {
        updatedData.price_history = [];
      }
      if (!data.hasOwnProperty('categoryNameVariations')) {
        updatedData.categoryNameVariations = [];
      }
      
      const docRef = db.collection(collectionName).doc(doc.id);
      batch.update(docRef, updatedData);
      
      batchCount++;
      totalUpdated++;
      
      // Execute batch when limit is reached
      if (batchCount >= batchLimit) {
        batch.commit();
        console.log(`📤 Updated batch: ${totalUpdated - batchCount + 1}-${totalUpdated} documents`);
        batchCount = 0;
        batch = db.batch();
      }
    });
    
    // Commit remaining documents
    if (batchCount > 0) {
      await batch.commit();
      console.log(`📤 Updated final batch: ${totalUpdated - batchCount + 1}-${totalUpdated} documents`);
    }
    
    console.log(`✅ Timestamp update complete! Updated ${totalUpdated} documents.`);
    console.log(`⏰ All documents now have last_updated: ${currentTimestamp}`);
    
  } catch (error) {
    console.error('❌ Error updating timestamps:', error);
    throw error;
  }
}

// Export functions for individual use
export {
  parseCSVFile,
  processCSVData,
  updateExistingDocuments,
  updateExistingFromCSV,
  updateTimestampsOnly,
  processCSVRow,
  saveProcessingReport,
  checkExistingDocuments
};

// Usage examples:

// 1. UPDATE existing CSV records with timestamp updates (RECOMMENDED - default behavior)
const csvFilePath = './consolidated.csv'; // Change this to your CSV file path
// updateExistingFromCSV(csvFilePath, 'matched_products', true);

// 2. UPDATE existing CSV records without updating timestamps (preserve original timestamps)
// updateExistingFromCSV(csvFilePath, 'matched_products', false);

// 3. Only update timestamps for existing documents (no data upload)
// updateTimestampsOnly('matched_products');

// Run the UPDATE process with timestamp updates enabled
updateExistingFromCSV(csvFilePath, 'matched_products', true)
  .then((result) => {
    if (result) {
      console.log(`\n📈 FINAL SUMMARY:`);
      console.log(`   Updated: ${result.updatedCount} existing documents`);
      console.log(`   Skipped: ${result.skippedCount} documents (not found in Firebase)`);
      console.log(`   Total in CSV: ${result.totalProcessed} documents`);
    }
  })
  .catch((error) => {
    console.error('❌ Process failed:', error);
    process.exit(1);
  });