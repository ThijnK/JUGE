import csv
from collections import defaultdict

def calculate_avg_execution_time(input_file, output_file):
    """
    Calculate average execution time for each benchmark subject across all entries.
    
    Args:
        input_file: Path to the input CSV file
        output_file: Path to the output CSV file where results will be written
    """
    # Dictionary to store execution time data for each benchmark
    benchmark_data = defaultdict(lambda: {'total_time': 0.0, 'count': 0})
    
    # Read the input CSV file
    try:
        with open(input_file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            
            # Process each row in the CSV
            for row in reader:
                if len(row) < 8:  # Ensure the row has enough columns
                    continue
                
                if row[0].startswith('//'):  # Skip comment lines
                    continue
                    
                # Extract relevant information
                tool = row[0]  # Tool name (column 1, 0-indexed)
                if (not tool.startswith("maze-")):
                    continue
                benchmark = row[1]  # Benchmark name (column 2, 0-indexed)
                
                try:
                    # Extract execution time (converting to float)
                    execution_time = float(row[6])  # Column 7 (0-indexed)
                    
                    # Add to the total and increment the count
                    benchmark_data[benchmark]['total_time'] += execution_time
                    benchmark_data[benchmark]['count'] += 1
                except (ValueError, IndexError):
                    # Skip rows with invalid data
                    continue
        
        # Calculate averages and write to output file
        with open(output_file, 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            
            # Write header
            writer.writerow(['Benchmark', 'Average_Execution_Time'])
            
            # Calculate and write averages for each benchmark
            for benchmark in sorted(benchmark_data.keys()):
                total_time = benchmark_data[benchmark]['total_time']
                count = benchmark_data[benchmark]['count']
                
                # Calculate average if data exists
                if count > 0:
                    avg_time = total_time / count
                    writer.writerow([benchmark, avg_time])
        
        print(f"Average execution times calculated and written to {output_file}")
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    input_file = "results.tmp"
    output_file = "average_execution_times.csv"
    calculate_avg_execution_time(input_file, output_file)