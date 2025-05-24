import csv
import os

def generate_latex_boxplot_body(stats_file, outliers_file, output_file):
    """
    Generate LaTeX boxplot code using numeric x-coordinates and pre-calculated whiskers and outliers.
    
    Args:
        stats_file: Path to the CSV file with box plot statistics including whiskers
        outliers_file: Path to the CSV file with pre-identified outliers
        output_file: Path to save the generated LaTeX code
    """
    # Define the specific tools in the required order
    ordered_tools = [
        'maze-DFS-SD', 
        'maze-BFS-SD', 
        'maze-SGS-SD', 
        'maze-RPS+COS-SD', 
        'maze-FOS-SD', 
        'maze-FOS+COS-SD', 
        'evosuite', 
        'randoop'
    ]
    
    # Create a mapping of tool names to numeric positions
    tool_positions = {tool: i+1 for i, tool in enumerate(ordered_tools)}
    
    # Read the statistics data with calculated whiskers
    stats_data = {}
    
    with open(stats_file, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            tool = row['Tool']
            if tool in ordered_tools:
                stats_data[tool] = {
                    'min': float(row['Min']),
                    'q1': float(row['Q1']),
                    'median': float(row['Median']),
                    'q3': float(row['Q3']),
                    'max': float(row['Max']),
                    'lower_whisker': float(row['LowerWhisker']),
                    'upper_whisker': float(row['UpperWhisker'])
                }
    
    # Read the outliers from the outlier file
    tool_outliers = {tool: [] for tool in ordered_tools}
    
    with open(outliers_file, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                tool = row['Tool']
                if tool in ordered_tools:
                    score = float(row['Score'])
                    tool_outliers[tool].append(score)
            except (ValueError, KeyError):
                continue
    
    # Generate LaTeX code - just the body part
    latex_code = []
    
    # Add each boxplot in specified order
    for tool in ordered_tools:
        if tool in stats_data:
            stats = stats_data[tool]
            position = tool_positions[tool]

            # Add outliers if any, using numeric position
            outlier_scores = tool_outliers.get(tool, [])
            
            if outlier_scores:
                latex_code.append(f"% Outliers for {tool}")
                latex_code.append(r"\addplot+[only marks, mark=*, forget plot]")
                latex_code.append(r"coordinates {")
                for score in outlier_scores:
                    latex_code.append(f"  ({position}, {score})")
                latex_code.append(r"};")
            
            # Box plot for each tool using numeric position
            latex_code.append(f"% Box plot for {tool}")
            latex_code.append(r"\addplot+[")
            latex_code.append(r"  boxplot prepared={")
            latex_code.append(f"    median={stats['median']},")
            latex_code.append(f"    upper quartile={stats['q3']},")
            latex_code.append(f"    lower quartile={stats['q1']},")
            latex_code.append(f"    upper whisker={stats['upper_whisker']},")
            latex_code.append(f"    lower whisker={stats['lower_whisker']}")
            latex_code.append(r"  },")
            latex_code.append(r"  mark=none,")
            latex_code.append(r"] coordinates {};")
    
    # Write LaTeX code to file
    with open(output_file, 'w') as f:
        f.write('\n'.join(latex_code))
    
    print(f"LaTeX boxplot body generated and written to {output_file}")
    print("\nUse with these axis settings:")
    print(r"xtick={1,2,3,4,5,6,7,8},")
    print(r"xticklabels={maze-DFS-SD, maze-BFS-SD, maze-SGS-SD, maze-RPS+COS-SD, maze-FOS-SD, maze-FOS+COS-SD, evosuite, randoop},")
    print(r"cycle list name=primarylistfill,")

if __name__ == "__main__":
    stats_file = "score_boxplot_stats.csv"
    outliers_file = "score_boxplot_outliers.csv"
    output_file = "boxplot_body.tex"
    generate_latex_boxplot_body(stats_file, outliers_file, output_file)