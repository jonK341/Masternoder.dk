# Advanced Calculator Data Population Guide

## Overview

The `populate_advanced_calculator_data.py` script generates massive amounts of constructive, realistic data for all Advanced Calculator database tables. This data is essential for testing API endpoints and demonstrating the system's capabilities.

## Features

- **Comprehensive Data Generation**: Populates all 7 Advanced Calculator tables
- **Realistic Data**: Generates data with proper relationships, timestamps, and JSON structures
- **Configurable Volume**: Choose how many records to generate for each table
- **Historical Data**: Generates data spanning 180 days for realistic historical context
- **Proper Relationships**: Maintains foreign key relationships between tables
- **Progress Tracking**: Shows progress during data generation

## Tables Populated

1. **calculation_history** - Calculation records with breakdowns and insights
2. **point_loss_detection** - Point loss detection records with various methods
3. **repair_log** - Repair operations linked to calculations and losses
4. **predictions** - Future point predictions with confidence intervals
5. **pattern_analysis** - Pattern analysis results with insights and recommendations
6. **anomaly_detection** - Anomaly records with different severities
7. **system_point_snapshots** - Historical point snapshots for systems

## Prerequisites

1. **Database Tables Must Exist**: Run the migration script first:
   ```bash
   python scripts/migrate_advanced_calculator.py
   ```

2. **Flask App Configuration**: Ensure your Flask app is properly configured with database connection

## Usage

### Basic Usage

```bash
cd /path/to/project
python scripts/populate_advanced_calculator_data.py
```

### Interactive Configuration

When you run the script, it will prompt you for the number of records to generate for each table:

```
Number of calculation_history records [1000]: 
Number of point_loss_detection records [300]: 
Number of repair_log records [400]: 
Number of predictions records [500]: 
Number of pattern_analysis records [400]: 
Number of anomaly_detection records [600]: 
Number of system_point_snapshots records [2000]: 
```

Press Enter to use the default values (shown in brackets), or enter custom numbers.

### Recommended Record Counts

For **testing/demonstration**:
- calculation_history: 1000-2000
- point_loss_detection: 300-500
- repair_log: 400-600
- predictions: 500-1000
- pattern_analysis: 400-600
- anomaly_detection: 600-1000
- system_point_snapshots: 2000-5000

For **comprehensive testing**:
- calculation_history: 5000-10000
- point_loss_detection: 1000-2000
- repair_log: 1500-3000
- predictions: 2000-5000
- pattern_analysis: 1500-3000
- anomaly_detection: 2000-5000
- system_point_snapshots: 10000-50000

## Data Characteristics

### Realistic Features

- **Time Distribution**: Data spread over 180 days for historical analysis
- **User Distribution**: Uses 200+ unique user IDs
- **System Integration**: Uses real system names from 178 point systems
- **Proper JSON**: All JSON fields contain realistic, structured data
- **Relationships**: Foreign keys properly maintained
- **Variety**: Different types, severities, and statuses for realistic testing

### Calculation History

- Multiple calculation types: intelligent, atomic, financial, point_calculator, comprehensive
- System breakdowns with 10-50 systems per calculation
- Multipliers and insights included
- Confidence scores and duration tracking

### Point Loss Detection

- Multiple detection methods: statistical, pattern, neural, threshold, comparative
- Some losses marked as resolved with resolution timestamps
- Breakdown of losses across multiple systems
- Detection confidence scores

### Repair Logs

- Linked to calculations and loss detections
- Various repair types and success rates
- Detailed repair information in JSON format
- Duration tracking

### Predictions

- Multiple prediction types: future_points, trend, correction, growth, decline
- Various time horizons: 7, 14, 30, 60, 90 days
- Confidence intervals and ranges
- System-level predictions

### Pattern Analysis

- Multiple analysis types: trend, anomaly, correlation, neural, pattern, seasonal
- Insights and recommendations included
- Analysis of 10-40 systems per record
- Duration tracking

### Anomaly Detection

- Multiple severity levels: low, medium, high, critical
- Some anomalies marked as fixed
- Detailed anomaly information and suggested fixes
- Linked to calculations

### System Point Snapshots

- Multiple snapshots per calculation (3-10)
- Covers various systems from the 178 system list
- Includes multipliers and calculated totals
- Historical tracking

## Example Output

```
================================================================================
ADVANCED CALCULATOR DATA POPULATION
Generating Massive Amounts of Constructive Data for API
================================================================================

[INFO] Using 200 user IDs

[1/7] Populating calculation_history (1000 records)...
  Created 100/1000 calculation records...
  Created 200/1000 calculation records...
  ...
  ✅ Created 1000 calculation_history records

[2/7] Populating point_loss_detection (300 records)...
  ...
  ✅ Created 300 point_loss_detection records

...

================================================================================
DATA POPULATION COMPLETE!
================================================================================

Summary:
  calculation_history:     1,000 records
  point_loss_detection:    300 records
  repair_log:              400 records
  predictions:             500 records
  pattern_analysis:        400 records
  anomaly_detection:       600 records
  system_point_snapshots:  2,000 records

  TOTAL RECORDS CREATED:   5,200
```

## Next Steps

After populating data:

1. **Test API Endpoints**: Verify data is accessible through API routes
2. **Check Statistics**: Test statistics endpoints to see aggregated data
3. **Test Predictions**: Try prediction endpoints with real data
4. **Verify Relationships**: Check that foreign keys work correctly
5. **Performance Testing**: Test query performance with larger datasets

## Troubleshooting

### Tables Don't Exist

```
[ERROR] Missing tables: calculation_history, ...
Please run migrate_advanced_calculator.py first
```

**Solution**: Run the migration script first:
```bash
python scripts/migrate_advanced_calculator.py
```

### Database Connection Errors

Make sure your Flask app configuration has the correct database URI set in `SQLALCHEMY_DATABASE_URI`.

### Memory Issues with Large Datasets

If generating very large datasets (50,000+ records), consider:
- Running in batches
- Increasing database connection pool size
- Using database-specific bulk insert methods

## API Endpoints to Test

After populating data, test these endpoints:

- `GET /vidgenerator/api/advanced-calculator/statistics/<user_id>` - Get statistics
- `GET /vidgenerator/api/advanced-calculator/predict/<user_id>` - Get predictions
- `GET /vidgenerator/api/advanced-calculator/analyze-patterns/<user_id>` - Analyze patterns
- `GET /vidgenerator/api/advanced-calculator/detect-loss/<user_id>` - Detect losses

## Notes

- The script generates data in batches to avoid memory issues
- All timestamps are in UTC
- Data spans 180 days from current date backwards
- User IDs are generated (user_001, user_002, etc.)
- All numeric values are rounded to 2 decimal places
- JSON fields contain structured, realistic data
