# Maze Benchmark Setup

This directory contains the synthetic benchmark subjects used to benchmark the MAZE tool and its search strategies.

## Subjects

The configuration file `benchmarks.list` lists all subjects. The file `orig-benchmarks.list` lists only the subjects from the original MAZE framework.

#### Subjects from the original MAZE benchmark

- `AckermannPeter`: Implementation of the Ackermann-Peter function.
- `BinarySearch`: Implementation of a binary search algorithm on an int array.
- `ConvergingPaths`: Class where control flow paths repeatedly diverge and converge.
- `ExprEvaluator`: Evaluates simple arithemetic expressions in a char array, using recursive descent parsing.
- `FloatStatistics`: Provides methods for statistics and functions of floating-point numbers (e.g., mean, sqrt, etc.).
- `MatrixAnalyzer`: Performs operations on a 2D int array.
- `NestedLoops`: Sorts an array with bubble sort while calculating a specific value.
- `QuickSort`: Implementation of the quicksort algorithm on an int array.
- `SinglyLinkedList`: Implements a singly linked list with various operations (e.g., add, delete, etc.).
- `TriangleClassifier`: Classifies a triangle based on its sides (e.g., equilateral, isosceles, etc.).
- `BinaryTree`: Provides a binary tree implementation and various traversal and utility methods (e.g., in-order, pre-order, post-order traversal, height calculation, finding certain values).
- `BitwiseManipulator`: Class that performs various bitwise operations on integers.
- `BracketBalancer`: Class that checks whether a string of brackets (represented as an array of characters) is balanced.
- `ConnectedComponents`: Calculates the number of connected components and detects components with cycles of a given length in a graph represented as an adjacency matrix.
- `Dijkstra`: Implements Dijkstra's algorithm to find the shortest path in a graph represented as an adjacency matrix, as well as a DFS traversal method to check whether a particular node is reachable from another node.
- `GraphTraversal`: Implements DFS and BFS graph traversal algorithms on a graph represented as an adjacency matrix. The DFS algorithm is used by the `ConnectedComponents` class.
- `HeapSort`: Implementation of the heap sort algorithm on an array of floating-point numbers.
- `IntUtils`: Class that provides various utility methods for integers, such as calculating the GCD, LCM, and factorial.
- `StringPatternMatcher`: Implements a simple string pattern matching algorithm based on regex-like syntax.
- `StringUtils`: Class that provides various utility methods for strings, such as reversing a string, checking for palindromes, and finding really specific substrings (e.g., alternating digits and letters).

#### Subjects ported from SVComp

- `BellmanFord_FunSat01`
- `RedBlackTree_MemSat01`
- `float_nonlinear_calculation.Bessel`
- `float_nonlinear_calculation.Conflict`
- `float_nonlinear_calculation.Euler`
- `float_nonlinear_calculation.Optimization`
- `MinePump.spec1_5_product1.Actions`
