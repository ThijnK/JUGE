import csv
import os
from collections import defaultdict
import statistics

def calculate_aggregate_boxplot_stats(input_file, output_file, outlier_file):
    """
    Calculate aggregate statistics needed for box plots from score data,
    and identify outlier data points.
    
    Args:
        input_file: Path to the input CSV file with detailed scores
        output_file: Path to the output CSV file where statistics results will be written
        outlier_file: Path to the output CSV file where outlier data points will be written
    """
    # Dictionary to store score data for each tool (across all benchmarks and time budgets)
    tool_scores = defaultdict(list)
    
    # Dictionary to store detailed data for potential outliers
    # We'll store the full row information for each score
    all_data = []
    
    # Read the input CSV file
    try:
        with open(input_file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)  # Store header row
            
            # Process each row in the CSV
            for row in reader:
                if len(row) < 8 or row[0].startswith('//'):  # Skip comment or incomplete lines
                    continue
                
                try:
                    # Extract information
                    benchmark = row[1]
                    class_name = row[2]
                    run = row[3]
                    time_budget = row[4]
                    config = row[5]
                    tool = row[6]
                    score = float(row[7])
                    
                    # Add the score to the appropriate tool
                    tool_scores[tool].append(score)
                    
                    # Store full record for potential outlier identification later
                    all_data.append({
                        'row': row,
                        'benchmark': benchmark,
                        'class': class_name,
                        'run': run,
                        'timeBudget': time_budget,
                        'config': config,
                        'tool': tool,
                        'score': score
                    })
                    
                except (ValueError, IndexError):
                    # Skip rows with invalid data
                    continue
        
        # Calculate statistics and identify outliers
        outliers = []
        tool_stats = {}
        
        # Calculate statistics for each tool
        for tool in sorted(tool_scores.keys()):
            score_data = tool_scores[tool]
            
            if score_data:
                # Filter out zeros for some calculations
                non_zero_scores = [s for s in score_data if s > 0]
                non_zero_count = len(non_zero_scores)
                
                # Sort data for percentile calculations
                sorted_scores = sorted(score_data)
                count = len(sorted_scores)
                
                if count > 0:
                    min_val = min(sorted_scores)
                    max_val = max(sorted_scores)
                    median = statistics.median(sorted_scores)
                    mean = statistics.mean(sorted_scores)
                    
                    # Calculate standard deviation
                    std_dev = statistics.stdev(sorted_scores) if count > 1 else 0
                    
                    # Calculate quartiles
                    if count >= 4:
                        q1_pos = (count - 1) // 4
                        q3_pos = (count - 1) * 3 // 4
                        q1 = sorted_scores[q1_pos]
                        q3 = sorted_scores[q3_pos]
                    else:
                        q1 = min_val
                        q3 = max_val
                    
                    # Calculate IQR and outlier thresholds using Tukey's method
                    iqr = q3 - q1
                    lower_threshold = q1 - 1.5 * iqr
                    upper_threshold = q3 + 1.5 * iqr
                    
                    # Find the most extreme non-outlier values for whiskers
                    non_outlier_scores = [s for s in sorted_scores if lower_threshold <= s <= upper_threshold]
                    
                    if non_outlier_scores:
                        lower_whisker = min(non_outlier_scores)
                        upper_whisker = max(non_outlier_scores)
                    else:
                        # If no non-outlier values, use the quartiles as whiskers
                        lower_whisker = q1
                        upper_whisker = q3
                    
                    # Store these stats for this tool
                    tool_stats[tool] = {
                        'min': min_val,
                        'q1': q1,
                        'median': median,
                        'q3': q3,
                        'max': max_val,
                        'mean': mean,
                        'std_dev': std_dev,
                        'count': count,
                        'non_zero_count': non_zero_count,
                        'lower_threshold': lower_threshold,
                        'upper_threshold': upper_threshold,
                        'lower_whisker': lower_whisker,
                        'upper_whisker': upper_whisker
                    }
        
        # Find outliers based on Tukey's method thresholds
        for data in all_data:
            tool = data['tool']
            score = data['score']
            if tool in tool_stats:
                stats = tool_stats[tool]
                # Check if this score is an outlier (outside the whiskers)
                if score < stats['lower_whisker'] or score > stats['upper_whisker']:
                    data['outlier_type'] = 'low' if score < stats['lower_whisker'] else 'high'
                    outliers.append(data)
        
        # Write summary statistics to output file
        with open(output_file, 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            
            # Write header - now including whisker thresholds
            writer.writerow(['Tool', 'Min', 'Q1', 'Median', 'Q3', 'Max', 'Mean', 
                             'StdDev', 'Count', 'NonZeroCount', 
                             'LowerThreshold', 'UpperThreshold', 
                             'LowerWhisker', 'UpperWhisker'])
            
            # Write statistics for each tool
            for tool in sorted(tool_stats.keys()):
                stats = tool_stats[tool]
                writer.writerow([
                    tool, 
                    stats['min'], 
                    stats['q1'], 
                    stats['median'], 
                    stats['q3'], 
                    stats['max'], 
                    stats['mean'], 
                    stats['std_dev'], 
                    stats['count'], 
                    stats['non_zero_count'],
                    stats['lower_threshold'],
                    stats['upper_threshold'],
                    stats['lower_whisker'],
                    stats['upper_whisker']
                ])
        
        # Write outliers to separate file
        with open(outlier_file, 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            
            # Write header
            writer.writerow(['Tool', 'Benchmark', 'Class', 'Run', 'TimeBudget', 
                            'Score', 'OutlierType'])
            
            # Write each outlier
            for outlier in outliers:
                writer.writerow([
                    outlier['tool'],
                    outlier['benchmark'],
                    outlier['class'],
                    outlier['run'],
                    outlier['timeBudget'],
                    outlier['score'],
                    outlier['outlier_type']
                ])
        
        print(f"Aggregate box plot statistics calculated and written to {output_file}")
        print(f"Outlier data points written to {outlier_file}")
        print(f"Found {len(outliers)} outliers out of {len(all_data)} data points")
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    input_file = "detailed_score.csv"
    output_file = "score_boxplot_stats.csv"
    outlier_file = "score_boxplot_outliers.csv"
    calculate_aggregate_boxplot_stats(input_file, output_file, outlier_file)