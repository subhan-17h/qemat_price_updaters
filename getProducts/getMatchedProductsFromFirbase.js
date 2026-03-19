import admin from "firebase-admin";
import fs from "fs";
import path from "path";
import XLSX from "xlsx";
import { createRequire } from "module";
import { fileURLToPath } from "url";

const require = createRequire(import.meta.url);
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Initialize Firebase Admin
admin.initializeApp({
  credential: admin.credential.cert(require("../serviceAccountKey.json")),
  storageBucket: "qemat-a2a2c.firebasestorage.app"
});

const db = admin.firestore();

// Enhanced CSV escape function
function escapeCSV(value) {
  if (value === null || value === undefined) {
    return '';
  }
  
  const stringValue = String(value);
  if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }
  return stringValue;
}

// Function to export matched products to both CSV and Excel in original format
async function exportMatchedProductsToFiles() {
  try {
    console.log("📊 Starting export from Firestore matched_products collection...");
    
    const matchedProductsCollection = db.collection('matched_products');
    const snapshot = await matchedProductsCollection.get();
    
    if (snapshot.empty) {
      console.log("❌ No matched products found in database");
      return;
    }
    
    console.log(`📦 Found ${snapshot.size} matched product documents to export`);
    
    // Define headers for the updated structure
    const headers = [
      'document_id',
      'category',
      'categoryNameVariations',
      'created_at',
      'image_url',
      'last_updated',
      'matched_products_count',
      'name',
      'original_url',
      'price',
      'price_history',
      'timestamp',
      'product_id',
      'store_id',
      'matched_products'
    ];
    
    // Prepare data arrays
    const excelData = [];
    let csvContent = headers.join(',') + '\n';
    
    let exportedCount = 0;
    let errors = 0;
    
    // Process each document
    snapshot.forEach((doc) => {
      try {
        const data = doc.data();
        const docId = doc.id;
        
        // Create row data with all fields (new structure)
        const rowData = {
          document_id: docId,
          category: data.category || '',
          categoryNameVariations: Array.isArray(data.categoryNameVariations) ? JSON.stringify(data.categoryNameVariations) : '',
          created_at: data.created_at || '',
          image_url: data.image_url || '',
          last_updated: data.last_updated || '',
          matched_products_count: data.matched_products_count || 0,
          name: data.name || '',
          original_url: data.original_url || '',
          price: data.price !== undefined ? data.price : '',
          price_history: Array.isArray(data.price_history) ? JSON.stringify(data.price_history) : '',
          timestamp: data.timestamp || '',
          product_id: data.product_id || '',
          store_id: data.store_id || '',
          matched_products: Array.isArray(data.matched_products) ? JSON.stringify(data.matched_products) : ''
        };
        
        // Add to Excel data
        excelData.push(rowData);
        
        // Add to CSV
        const csvRow = [
          escapeCSV(rowData.document_id),
          escapeCSV(rowData.category),
          escapeCSV(rowData.categoryNameVariations),
          escapeCSV(rowData.created_at),
          escapeCSV(rowData.image_url),
          escapeCSV(rowData.last_updated),
          escapeCSV(rowData.matched_products_count),
          escapeCSV(rowData.name),
          escapeCSV(rowData.original_url),
          escapeCSV(rowData.price),
          escapeCSV(rowData.price_history),
          escapeCSV(rowData.timestamp),
          escapeCSV(rowData.product_id),
          escapeCSV(rowData.store_id),
          escapeCSV(rowData.matched_products)
        ];
        
        csvContent += csvRow.join(',') + '\n';
        exportedCount++;
        
        if (exportedCount % 1000 === 0) {
          console.log(`📝 Processed ${exportedCount} documents...`);
        }
        
      } catch (error) {
        console.error(`❌ Error processing document ${doc.id}:`, error.message);
        errors++;
      }
    });
    
    // Create timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    
    // Save timestamped CSV file (audit copy)
    const csvFilename = `matched_products_export_${timestamp}.csv`;
    const csvFilepath = path.join(__dirname, csvFilename);
    fs.writeFileSync(csvFilepath, csvContent, 'utf8');

    // Save canonical products.csv in repository root for pipeline step 2
    const rootProductsPath = path.resolve(__dirname, "../products.csv");
    fs.writeFileSync(rootProductsPath, csvContent, 'utf8');
    
    // Save Excel file
    const excelFilename = `matched_products_export_${timestamp}.xlsx`;
    const excelFilepath = path.join(__dirname, excelFilename);
    const workbook = XLSX.utils.book_new();
    const worksheet = XLSX.utils.json_to_sheet(excelData);
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Matched Products');
    XLSX.writeFile(workbook, excelFilepath);
    
    console.log(`\n✅ Export completed successfully!`);
    console.log(`📁 CSV file saved: ${csvFilename}`);
    console.log(`📁 Canonical products CSV updated: ${rootProductsPath}`);
    console.log(`📁 Excel file saved: ${excelFilename}`);
    console.log(`📊 Statistics:`);
    console.log(`   Total documents exported: ${exportedCount}`);
    console.log(`   Errors: ${errors}`);
    console.log(`   CSV file size: ${(fs.statSync(csvFilepath).size / 1024 / 1024).toFixed(2)} MB`);
    console.log(`   Excel file size: ${(fs.statSync(excelFilepath).size / 1024 / 1024).toFixed(2)} MB`);
    
    return { csvFilepath, excelFilepath, rootProductsPath, exportedCount, errors };
    
  } catch (error) {
    console.error("❌ Export failed:", error.message);
    throw error;
  }
}

// Main execution
async function main() {
  try {
    await exportMatchedProductsToFiles();
  } catch (error) {
    console.error("❌ Process failed:", error);
    process.exit(1);
  }
}

// Run if called directly
if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  main();
}

export {
  exportMatchedProductsToFiles,
};
