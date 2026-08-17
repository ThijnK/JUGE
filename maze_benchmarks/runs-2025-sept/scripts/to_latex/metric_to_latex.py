def parse_sum_metrics_to_latex(csv_file, metric_type, output_file):
    """
    Parse sum metrics CSV data and generate LaTeX addplot coordinates.
    
    Args:
        csv_file: Path to the CSV file
        metric_type: Either 'mutation' for mutation kill ratio or 'branch' for condition/branch coverage
        output_file: Output file for LaTeX code
    """
    # Dictionary to hold data for each tool
    tool_data = {}
    
    # Select the column index based on metric type
    if metric_type == 'mutation':
        metric_index = 4  # Sum_MutantsKillRatio is the 5th column (index 4)
        metric_name = "Mutation Kill Ratio"
    elif metric_type == 'branch':
        metric_index = 3  # Sum_ConditionsCoverageRatio is the 4th column (index 3)
        metric_name = "Branch Coverage"
    else:
        raise ValueError("metric_type must be either 'mutation' or 'branch'")
    
    # Read the CSV file
    with open(csv_file, 'r') as file:
        # Skip header
        header = next(file)
        
        for line in file:
            # Skip commented lines
            if line.strip().startswith('//'):
                continue
                
            # Split by comma
            parts = line.strip().split(',')
            
            # Ensure we have enough parts
            if len(parts) < 5:
                continue
                
            try:
                tool = parts[0]
                time_budget = parts[1]
                metric_value = float(parts[metric_index])
                num_benchmarks = float(parts[5])  # Number of benchmarks
                
                # Initialize tool entry if not exists
                if tool not in tool_data:
                    tool_data[tool] = {}
                
                # Store the metric divided by 100 to get range 0-10 
                # (since it's a sum of 10 benchmarks, each with range 0-100)
                tool_data[tool][time_budget] = metric_value / 100.0
                
            except (ValueError, IndexError):
                # Skip rows that can't be parsed properly
                continue
    
    # Define the custom tool order
    tool_order = [
        "maze-DFS-SD", "maze-DFS-CD",
        "maze-BFS-SD", "maze-BFS-CD",
        "maze-SGS-SD", "maze-SGS-CD",
        "maze-RPS+COS-SD", "maze-RPS+COS-CD",
        "maze-FOS-SD", "maze-FOS-CD",
        "maze-FOS+COS-SD", "maze-FOS+COS-CD",
        "evosuite",
        "randoop"
    ]
    
    # Generate LaTeX code
    latex_code = ""
    
    # Process tools in the specified order
    for tool_pattern in tool_order:
        # Find tools that match the pattern (to handle variants like -SD, -CD)
        matching_tools = [t for t in tool_data.keys() if t.startswith(tool_pattern)]
        
        for tool in matching_tools:
            # Check if we have data for all time budgets
            if all(tb in tool_data[tool] for tb in ["5", "10", "30", "60"]):
                latex_code += f"% {tool}\n\\addplot coordinates {{\n"
                
                # Add coordinates for each time budget (5, 10, 30, 60)
                coordinates = []
                for time_budget in ["5", "10", "30", "60"]:
                    ratio = tool_data[tool][time_budget]
                    coordinates.append(f" ({time_budget}, {ratio:.3f})")
                
                latex_code += " ".join(coordinates)
                latex_code += "\n};\n"
                latex_code += f"\\addlegendentry{{{tool}}}\n\n"
    
    # Write to output file
    with open(output_file, 'w') as file:
        file.write(latex_code)
    
    print(f"LaTeX code for summed {metric_name} written to {output_file}")

if __name__ == "__main__":
    input_file = "sum_metrics.csv"
    
    # Generate for both metric types
    parse_sum_metrics_to_latex(input_file, 'mutation', "sum_mutation_latex_plots.tex")
    parse_sum_metrics_to_latex(input_file, 'branch', "sum_branch_latex_plots.tex")