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
