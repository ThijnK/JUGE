import csv
import os
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def create_violin_plot_from_csv(input_file="detailed_score.csv"):
    """
    Extract scores from CSV and create a violin plot matching LaTeX style specifications.
    
    Args:
        input_file: Path to the input CSV file (detailed_score.csv)
    """
    # Define the color scheme matching the bar plot
    colors = [
        (0, 0, 1),           # full blue
        (0, 128/255, 128/255),  # teal RGB(0,128,128)
        (1, 128/255, 0),      # orange (255,128,0)
        (191/255, 128/255, 64/255),  # brown (191,128,64)
        (0, 174/255, 239/255),  # cyan (0,174,239)
        (128/255, 0, 128/255),  # violet (128, 0, 128)
        (230/255, 190/255, 65/255),  # golden yellow (230, 190, 65)
        (1, 0, 0),           # full red
        (0, 0, 0),           # black
        (1, 94/255, 110/255),  # bright coral pink (255, 94, 110)
        (76/255, 145/255, 65/255)  # muted green (76,145, 65)
    ]
    
    # Define expected tool order and their display names
    tool_order = ['DFS', 'BFS', 'SGS', 'RPS+COS', 'FOS', 'FOS+COS', 'evosuite', 'randoop', 'kex']
    maze_tools = {'DFS', 'BFS', 'SGS', 'RPS+COS', 'FOS', 'FOS+COS'}
    
    # Extract scores from CSV
    tool_scores = defaultdict(list)
    
    try:
        with open(input_file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header
            
            for row in reader:
                if len(row) < 8:
                    continue
                
                try:
                    tool = row[6].strip()
                    score = float(row[7])
                    tool_scores[tool].append(score)
                except (ValueError, IndexError):
                    continue
        
        if not tool_scores:
            print(f"Error: No valid data found in '{input_file}'")
            return
        
        # Map actual tool names to expected names
        tool_mapping = _create_tool_mapping(tool_scores.keys())
        
        # Prepare data for plotting
        plot_data, plot_labels, plot_colors = _prepare_plot_data(
            tool_scores, tool_mapping, tool_order, colors
        )
        
        if not plot_data:
            print("Error: No matching tools found for plotting")
            return
        
        # Log data summary
        _log_data_summary(plot_labels, plot_data)
        
        # Create and save the violin plot
        _create_and_save_plot(plot_data, plot_labels, plot_colors, maze_tools)
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def _create_tool_mapping(actual_tools):
    """Create mapping from actual tool names to expected names."""
    tool_mapping = {}
    
    for tool in actual_tools:
        tool_lower = tool.lower()
        if 'evosuite' in tool_lower:
            tool_mapping[tool] = 'evosuite'
        elif 'randoop' in tool_lower:
            tool_mapping[tool] = 'randoop'
        elif 'kex' in tool_lower:
            tool_mapping[tool] = 'kex'
        elif 'dfs' in tool_lower:
            tool_mapping[tool] = 'DFS'
        elif 'bfs' in tool_lower:
            tool_mapping[tool] = 'BFS'
        elif 'sgs' in tool_lower:
            tool_mapping[tool] = 'SGS'
        elif 'rps+cos' in tool_lower or 'rps_cos' in tool_lower:
            tool_mapping[tool] = 'RPS+COS'
        elif 'fos+cos' in tool_lower or 'fos_cos' in tool_lower:
            tool_mapping[tool] = 'FOS+COS'
        elif 'fos' in tool_lower:
            tool_mapping[tool] = 'FOS'
    
    return tool_mapping

def _prepare_plot_data(tool_scores, tool_mapping, tool_order, colors):
    """Prepare data arrays for plotting in the correct order."""
    plot_data = []
    plot_labels = []
    plot_colors = []
    
    for i, expected_tool in enumerate(tool_order):
        # Find matching tool in actual data
        matching_tool = None
        for actual_tool, mapped_name in tool_mapping.items():
            if mapped_name == expected_tool:
                matching_tool = actual_tool
                break
        
        if matching_tool and matching_tool in tool_scores:
            plot_data.append(tool_scores[matching_tool])
            plot_labels.append(expected_tool)
            plot_colors.append(colors[i % len(colors)])
    
    return plot_data, plot_labels, plot_colors

def _log_data_summary(plot_labels, plot_data):
    """Log summary of data found for each tool."""
    print("Data summary:")
    for label, data in zip(plot_labels, plot_data):
        print(f"  {label}: {len(data)} data points (mean: {np.mean(data):.2f}, std: {np.std(data):.2f})")

def _create_and_save_plot(plot_data, plot_labels, plot_colors, maze_tools):
    """Create, style, and save the violin plot."""
    # Set LaTeX-compatible font (Computer Modern for LNCS)
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Computer Modern Roman'],
        'text.usetex': True,  # Set to True if you have LaTeX installed
        'font.size': 20,
        'axes.labelsize': 20,
        'axes.titlesize': 20,
        'xtick.labelsize': 20,
        'ytick.labelsize': 20
    })
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create violin plot with wider violins
    parts = ax.violinplot(plot_data, positions=range(len(plot_data)), 
                         showmeans=True, showmedians=True, widths=0.7)
    
    # Style violin bodies with colors and borders like bar plot
    for i, pc in enumerate(parts['bodies']):
        color = plot_colors[i]
        # Set fill color with 50% opacity
        pc.set_facecolor((*color, 0.5))
        # Set border color at full opacity
        pc.set_edgecolor(color)
        pc.set_linewidth(1.5)
    
    # Style statistical elements
    for element in ['cmeans', 'cmedians', 'cbars', 'cmaxes', 'cmins']:
        if element in parts:
            parts[element].set_color('red' if element == 'cmedians' else 'black')
            parts[element].set_linewidth(1.2)
    
    # Format labels with proper LaTeX small caps and styling
    formatted_labels = []
    for label in plot_labels:
        if label in maze_tools:
            # Bold small caps for MAZE strategies
            formatted_labels.append(f"\\textsc{{{label.lower()}}}")
        else:
            # Italic small caps for external tools
            formatted_labels.append(f"\\textsc{{{label.lower()}}}")
    
    # Configure axes
    ax.set_xticks(range(len(plot_labels)))
    ax.set_xticklabels(formatted_labels, rotation=45, ha='right')
    ax.tick_params(axis='x')
    ax.xaxis.set_tick_params(direction='out', length=10)
    
    ax.set_ylabel('Score', fontsize=24, labelpad=10)
    ax.set_title('Score Distribution for Each Strategy and Tool', fontsize=24, pad=16)
    ax.set_ylim(0, 7)
    ax.set_xlim(-0.5, len(plot_data) - 0.5)
    
    # Add grid and styling
    ax.grid(True, alpha=0.6, axis='y', linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(True)
    ax.yaxis.set_ticks_position('both')      # Show ticks on both left and right
    ax.yaxis.set_tick_params(direction='in', color=('black', 0.7), length=10) # Ticks go into the plot
    
    plt.tight_layout()
    
    # Save plots
    output_files = ['violin_plot_scores.pdf', 'violin_plot_scores.png']
    for filename in output_files:
        plt.savefig(filename, dpi=300, bbox_inches='tight')
    
    print(f"Violin plot saved as {' and '.join(output_files)}")

if __name__ == "__main__":
    create_violin_plot_from_csv()