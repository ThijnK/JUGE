import csv
import os
from collections import defaultdict

def calculate_averages(input_file, output_file):
    """
    Calculate average metrics for each tool, benchmark, and time budget combination.
    
    Args:
        input_file: Path to the input CSV file
        output_file: Path to the output CSV file where results will be written
    """
    # Dictionary to store data for each tool, benchmark, and time budget
    results = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
        'line_coverage': [], 
        'conditions_coverage': [], 
        'mutants_kill': []
    })))
    
    # Read the input CSV file
    try:
        with open(input_file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            
            # Process each row in the CSV
            for row in reader:
                if len(row) < 23:  # Ensure the row has enough columns
                    continue
                
                if row[0].startswith('//'):  # Skip comment lines
                    continue
                    
                # Extract relevant information
                tool = row[0]  # Tool name
                benchmark = row[1]  # Benchmark name
                time_budget = row[23]  # Time budget (column 24, 0-indexed)
                
                try:
                    # Extract metrics (converting to float)
                    line_coverage = float(row[13])  # Column 14 (0-indexed)
                    conditions_coverage = float(row[16])  # Column 17 (0-indexed)
                    mutants_kill = float(row[21])  # Column 22 (0-indexed)
                    
                    # Store the values
                    results[tool][benchmark][time_budget]['line_coverage'].append(line_coverage)
                    results[tool][benchmark][time_budget]['conditions_coverage'].append(conditions_coverage)
                    results[tool][benchmark][time_budget]['mutants_kill'].append(mutants_kill)
                except (ValueError, IndexError):
                    # Skip rows with invalid data
                    continue
        
        # Calculate averages and write to output file
        with open(output_file, 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            
            # Write header with time budget column
            writer.writerow(['Tool', 'Benchmark', 'TimeBudget', 'AvgLineCoverageRatio', 
                            'AvgConditionsCoverageRatio', 'AvgMutantsKillRatio'])
            
            # Calculate and write averages for each tool-benchmark-timebudget combination
            for tool in sorted(results.keys()):
                for benchmark in sorted(results[tool].keys()):
                    for time_budget in sorted(results[tool][benchmark].keys()):
                        line_data = results[tool][benchmark][time_budget]['line_coverage']
                        conditions_data = results[tool][benchmark][time_budget]['conditions_coverage']
                        mutants_data = results[tool][benchmark][time_budget]['mutants_kill']
                        
                        # Calculate averages if data exists
                        if line_data and conditions_data and mutants_data:
                            avg_line = sum(line_data) / len(line_data)
                            avg_conditions = sum(conditions_data) / len(conditions_data)
                            avg_mutants = sum(mutants_data) / len(mutants_data)
                            
                            writer.writerow([tool, benchmark, time_budget, 
                                            avg_line, avg_conditions, avg_mutants])
        
        print(f"Average metrics calculated and written to {output_file}")
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    input_file = "results.tmp"
    output_file = "average_metrics.csv"
    calculate_averages(input_file, output_file)