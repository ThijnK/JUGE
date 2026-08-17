def parse_csv_to_latex(csv_file, benchmark, output_file):
    """
    Parse CSV data and generate LaTeX addplot coordinates for mutation kill ratios.
    
    Args:
        csv_file: Path to the CSV file
        benchmark: Benchmark to filter (e.g., 'FLOAT', 'EXPR')
        output_file: Output file for LaTeX code
    """
    # Dictionary to hold data for each tool
    tool_data = {}
    
    # Read the CSV file
    with open(csv_file, 'r') as file:
        for line in file:
            # Skip commented lines and header
            if line.strip().startswith('//') or 'Tool,Benchmark' in line:
                continue
                
            # Split by comma
            parts = line.strip().split(',')
            
            # Ensure we have enough parts
            if len(parts) < 6:
                continue
                
            try:
                tool = parts[0]
                bench = parts[1]
                time_budget = parts[2]
                mutation_kill_ratio = float(parts[5])
                
                # Filter for the benchmark we're interested in
                if bench == benchmark:
                    # Initialize tool entry if not exists
                    if tool not in tool_data:
                        tool_data[tool] = {}
                    
                    # Store the mutation kill ratio for this time budget
                    tool_data[tool][time_budget] = mutation_kill_ratio / 100.0  # Convert percentage to decimal
            except (ValueError, IndexError):
                # Skip rows that can't be parsed properly
                continue
    
    # Define the custom tool order
    tool_order = [
        "maze-DFS-SD", # "maze-DFS-CD",
        "maze-BFS-SD", # "maze-BFS-CD",
        "maze-SGS-SD", # "maze-SGS-CD",
        "maze-RPS+COS-SD", # "maze-RPS+COS-CD",
        "maze-FOS-SD", # "maze-FOS-CD",
        "maze-FOS+COS-SD", # "maze-FOS+COS-CD",
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
    
    print(f"LaTeX code for benchmark {benchmark} written to {output_file}")

if __name__ == "__main__":
    input_file = "average_metrics.csv"
    benchmarks = ["FLOAT", "EXPR", "TRIANGLE"]
    for benchmark in benchmarks:
      output_file = f"{benchmark.lower()}_latex_plots.tex"
      parse_csv_to_latex(input_file, benchmark, output_file)