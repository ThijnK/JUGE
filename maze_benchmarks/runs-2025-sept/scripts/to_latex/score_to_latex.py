def parse_score_to_latex(csv_file, output_file):
    """
    Parse average score CSV data and generate LaTeX addplot coordinates.
    
    Args:
        csv_file: Path to the CSV file
        output_file: Output file for LaTeX code
    """
    # Dictionary to hold data for each tool
    tool_data = {}
    
    # Read the CSV file
    with open(csv_file, 'r') as file:
        # Skip header
        header = next(file)
        
        for line in file:
            # Skip commented lines
            if line.strip().startswith('//'):
                continue
                
            # Split by comma and clean up quotes
            parts = [part.strip().strip('"') for part in line.strip().split(',')]
            
            # Ensure we have enough parts
            if len(parts) < 4:
                continue
                
            try:
                # Format: "index", timeBudget, tool, score
                time_budget = parts[1]
                tool = parts[2]
                score = float(parts[3])
                
                # Initialize tool entry if not exists
                if tool not in tool_data:
                    tool_data[tool] = {}
                
                # Store the score value
                tool_data[tool][time_budget] = score
                
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
        # Find tools that match the pattern
        matching_tools = [t for t in tool_data.keys() if t.startswith(tool_pattern)]
        
        for tool in matching_tools:
            # Check if we have data for all time budgets
            if all(tb in tool_data[tool] for tb in ["5", "10", "30", "60"]):
                latex_code += f"% {tool}\n\\addplot coordinates {{\n"
                
                # Add coordinates for each time budget (5, 10, 30, 60)
                coordinates = []
                for time_budget in ["5", "10", "30", "60"]:
                    score = tool_data[tool][time_budget]
                    coordinates.append(f" ({time_budget}, {score:.3f})")
                
                latex_code += " ".join(coordinates)
                latex_code += "\n};\n"
                latex_code += f"\\addlegendentry{{{tool}}}\n\n"
    
    # Write to output file
    with open(output_file, 'w') as file:
        file.write(latex_code)
    
    print(f"LaTeX code for average scores written to {output_file}")

if __name__ == "__main__":
    input_file = "./score/average_score.csv"
    output_file = "average_score_latex_plots.tex"
    parse_score_to_latex(input_file, output_file)