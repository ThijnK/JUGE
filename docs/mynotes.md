Start the docker-app (from desktop) first, else some docker commands may hang. Login too into the docker-app, just to make sure.

Creating fresh docker image with (from the home of juge-maze)   ... note the dot at the end:

    docker build -f Dockerfile -t junitcontest/infrastructure:latest .

Next we run a container from that image:

   docker run -v $(pwd)/tools/maze:/home/maze --name=JUGE -it --cpus=2 --memory=4g junitcontest/infrastructure:latest

NOTE: that will mount local tools/maze from juge-maze proj onto the container.

From there you are in the container shell.

The CUTs are in
   /var/benchmarks

Configure which CUTs in /var/benchmarks/conf , you can check to just run the triangle

To run the tools from contests scripts, first check the scripts in juge-maze project in infrastructure/benchmarks_maze/scripts

    from a tool's home, e.g. /home/maze
    > contest_generate_tests.sh maze 1 1 10
    > contest_compute_metrics <result-folder>
----

When you need to update maze, make a jar and put it in local juge-maze in tools/maze . This dir is mounted onto the container.


------

===
 TRIANGLE
 Evo-10
    Conditions total: 66
    Conditions coverage ratio (%): 100.0
    Mutants total: 75
    Mutants killed ratio (%): 0.0
Evo-60
    Conditions coverage ratio (%): 100.0
    Mutants killed ratio (%): 86.66
Evo-120  
    Mutants killed ratio (%): 86.66
Maze k=1, 10
    Conditions coverage ratio (%): 46.9
    Mutants killed ratio (%): 58.6
Maze k=1, 60  
    Conditions coverage ratio (%): 93.93
    Mutants killed ratio (%): 98.66
Maze k=3, 10
    Conditions coverage ratio (%): 54.545456
    Mutants killed ratio (%): 65.33333   
Maze k=3, 60
    Conditions coverage ratio (%): 93.93
    Mutants killed ratio (%): 98.66
======  

FLOATSTAT
Evo-10
    Conditions total: 10
  	Conditions coverage ratio (%): 100.0
  	Mutants total: 29
  	Mutants killed ratio (%): 37.931034
Evo-60
    Conditions coverage ratio (%): 100.0
    Mutants killed ratio (%): 72.41
Evo-120
    Mutants killed ratio (%): 75.86
Maze k=1, 10
    Conditions coverage ratio (%): 70.0
    Mutants killed ratio (%): 62.068962
Maze k=1, 60
    Conditions coverage ratio (%): 80.0
  	Mutants killed ratio (%): 72.41379
Maze k=3, 10
    Conditions coverage ratio (%): 70.0
  	Mutants killed ratio (%): 62.068962
Maze k=3, 60
    Conditions coverage ratio (%): 70.0
    Mutants killed ratio (%): 62.068962

======

BESSEL
Evo-10
    Conditions total: 24
  	Conditions coverage ratio (%): 95.83333
  	Mutants total: 26
  	Mutants killed ratio (%): 50.0
Evo-60
    Conditions coverage ratio (%): 95.83333
  	Mutants killed ratio (%): 92.30769
Maze k=1, 10
    Conditions coverage ratio (%): 54.166668
    Mutants killed ratio (%): 73.07692
Maze k=1, 60
    Conditions coverage ratio (%): 95.83333
  	Mutants killed ratio (%): 100.0
Maze k=3, 10
    Conditions coverage ratio (%): 58.333332
    Mutants killed ratio (%): 100.0
Maze k=3, 60
    Conditions coverage ratio (%): 95.83333
    Mutants killed ratio (%): 100.0

======
CONFLICT
Evo-10
    Conditions total: 36
    Conditions coverage ratio (%): 97.22222
    Mutants total: 68
    Mutants killed ratio (%): 27.941175
Evo-60
    Conditions coverage ratio (%): 97.22222
  	Mutants killed ratio (%): 52.941177
Evo-120
    Conditions coverage ratio (%): 97.22222
    Mutants killed ratio (%): 76.47059
Maze k=1, 10
    Conditions coverage ratio (%): 30.555555
  	Mutants killed ratio (%): 17.647058
Maze k=1, 60
    Conditions coverage ratio (%): 58.333332
  	Mutants killed ratio (%): 32.352943
Maze k=3, 10
    Conditions coverage ratio (%): 30.555555
    Mutants killed ratio (%): 17.647058
Maze k=3, 60
    Conditions coverage ratio (%): 52.77778
    Mutants killed ratio (%): 29.411766
Maze k=3, 120
    Conditions coverage ratio (%): 69.44444
    Mutants killed ratio (%): 38.235294

====

EULER
Evo-10
    Conditions total: 4
  	Conditions coverage ratio (%): 100.0
  	Mutants total: 12
  	Mutants killed ratio (%): 58.333332
Evo-60
    Mutants killed ratio (%): 91.66
Evo-120
    Mutants killed ratio (%): 83.33
Maze k=1, 10
    Conditions coverage ratio (%): 75.0
  	Mutants killed ratio (%): 100.0
Maze k=1, 60
    Conditions coverage ratio (%): 75.0
    Mutants killed ratio (%): 100.0
Maze k=3, 10 same
Maze k=3, 60 same
Maze k=3, 120 same

==========

OPTIMIZATION
Evo-10
    Conditions total: 32
    Conditions coverage ratio (%): 81.25
    Mutants total: 81
    Mutants killed ratio (%): 11.111112
Evo-60
    Conditions coverage ratio (%): 81.25
    Mutants killed ratio (%): 32
Evo-120
    Conditions coverage ratio (%): 87.5
    Mutants killed ratio (%): 33.3
Maze k=1, 10
    Conditions coverage ratio (%): 3.1
    Mutants killed ratio (%): 6.1
Maze k=1, 60 --> ZERO
Maze k=3, 10  same as k1 10
Maze k=3, 60 ZERO`
Maze k=3, 120 same as k1 10
Maze BFS k=3, 60
    Conditions coverage ratio (%): 6.25
    Mutants killed ratio (%): 12.3

========
RBT
Evo-10
    Conditions total: 170
  	Conditions coverage ratio (%): 52.35294
  	Mutants total: 176
  	Mutants killed ratio (%): 62.5
Evo-60
    Conditions coverage ratio (%): 59.4
    Mutants killed ratio (%): 53
Evo-120
    Conditions coverage ratio (%): 66.4
    Mutants killed ratio (%): 72.27
Maze k=1, 10
    Conditions coverage ratio (%): 48.8
    Mutants killed ratio (%): 58.5
Maze k=1, 60
    Conditions coverage ratio (%): 49.4
    Mutants killed ratio (%): 60.79
Maze k=3, 10
    Conditions coverage ratio (%): 51.76
    Mutants killed ratio (%): 64.7
Maze k=3, 60
    Conditions coverage ratio (%): 52.94
    Mutants killed ratio (%): 64.77
Maze k=3, 120
    same as 60
