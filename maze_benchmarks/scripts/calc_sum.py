import csv
from collections import defaultdict

def calculate_sums(input_file, output_file):
    """
    Calculate the sum of metrics across all benchmarks for each tool and time budget.
    
    Args:
        input_file: Path to the input CSV file (average_metrics.csv)
        output_file: Path to the output CSV file for sum metrics
    """
    # Dictionary to store sums for each tool and time budget
    sums = defaultdict(lambda: defaultdict(lambda: {
        'line_sum': 0.0,
        'conditions_sum': 0.0,
        'mutants_sum': 0.0,
        'benchmark_count': 0
    }))
    
    try:
        # Read the average metrics file
        with open(input_file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)  # Skip header row
            
            # Process each row in the CSV
            for row in reader:
                if len(row) < 6:  # Ensure the row has enough columns
                    continue
                
                tool = row[0]
                benchmark = row[1]
                time_budget = row[2]
                
                try:
                    # Extract metrics
                    avg_line = float(row[3])
                    avg_conditions = float(row[4])
                    avg_mutants = float(row[5])
                    
                    # Add to the sums for this tool and time budget
                    sums[tool][time_budget]['line_sum'] += avg_line
                    sums[tool][time_budget]['conditions_sum'] += avg_conditions
                    sums[tool][time_budget]['mutants_sum'] += avg_mutants
                    sums[tool][time_budget]['benchmark_count'] += 1
                except (ValueError, IndexError):
                    # Skip rows with invalid data
                    continue
        
        # Write the sums to output file
        with open(output_file, 'w', newline='') as sumfile:
            sum_writer = csv.writer(sumfile)
            
            # Write header for the sum file
            sum_writer.writerow(['Tool', 'TimeBudget', 'SumLineCoverageRatio', 
                              'SumConditionsCoverageRatio', 'SumMutantsKillRatio',
                              'NumBenchmarks'])
            
            # Write sums for each tool and time budget
            for tool in sorted(sums.keys()):
                for time_budget in sorted(sums[tool].keys()):
                    data = sums[tool][time_budget]
                    sum_writer.writerow([
                        tool,
                        time_budget,
                        data['line_sum'],
                        data['conditions_sum'],
                        data['mutants_sum'],
                        data['benchmark_count']
                    ])
        
        print(f"Sum metrics across benchmarks written to {output_file}")
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    input_file = "average_metrics.csv"
    output_file = "sum_metrics.csv"
    calculate_sums(input_file, output_file)