package sbst.runtool;

import java.io.*;
import java.util.ArrayList;
import java.util.List;

public class MazeTool implements ITestingTool {

    private String classPath;
    private File mazeJar = new File("lib", "maze.jar");

    private String strategies; // comma-separated list of strategies
    private String concreteDriven; // "true" or "false"  --> not used in this BM
    private String minimalisticSuite; // "true" or "false"
    private String pathLengthToCover; // -1,0, or >0
    private String pathAging; // -1,0, or >0

    public MazeTool(String strategies, String minimalisticSuite, String pathLengthToCover, String pathAging) {
        this.strategies = strategies;
        //this.concreteDriven = concreteDriven;
        this.minimalisticSuite = minimalisticSuite ;
        this.pathLengthToCover = pathLengthToCover ;
        this.pathAging = pathAging ;
    }

    public List<File> getExtraClassPath() {
        List<File> files = new ArrayList<>();
        if (!mazeJar.exists()) {
            System.err.println("Incorrect Maze JAR setting, JAR is not at: " + mazeJar.getAbsolutePath());
        } else {
            files.add(mazeJar);
        }
        return files;
    }

    public void initialize(File src, File bin, List<File> classPath) {
        StringBuilder sb = new StringBuilder();
        sb.append(bin.getAbsolutePath());
        for (File f : classPath) {
            sb.append(File.pathSeparator);
            sb.append(f.getAbsolutePath());
        }
        this.classPath = sb.toString();
    }

    public void run(String className, long timeBudget) {
        List<String> command;
        ProcessBuilder pbuilder = new ProcessBuilder();
        try {
            command = new ArrayList<>();
            // Explicitly use java 21 executable
            command.add("/usr/lib/jvm/java-21-openjdk-amd64/bin/java");
            // If an sbst_logback.xml file is present, use it for logging
            File logbackFile = new File("sbst_logback.xml");
            if (logbackFile.exists()) {
                command.add("-Dlogback.configurationFile=" + logbackFile.getAbsolutePath());
            }
            command.add("-jar");
            command.add(mazeJar.getAbsolutePath());
            command.add("--classpath=" + classPath);
            command.add("--classname=" + className);
            command.add("--output-path=./temp/testcases/");
            command.add("--log-level=INFO");
            // params which are configurable in this BM:
            command.add("--strategy=" + strategies);
            //command.add("--concrete-driven=" + concreteDriven);
            command.add("--minimalistic-suite=" + this.minimalisticSuite) ;
            command.add("--path-length-cov=" + this.pathLengthToCover) ;
            command.add("--target-path-aging=" + this.pathAging) ;
            // other params which are fixed:
            command.add("--max-depth=400");      
            command.add("--max-array-size=10") ;  
            command.add("--time-budget=" + timeBudget);
            command.add("--junit-version=JUnit4");
            // reporting params:
            command.add("--export-summary=true") ; 	
            
            System.err.println("Running Maze with command: " + command);
            pbuilder.command(command);

            // redirect error stream to a file
            File errorFile = new File("error.txt");
            pbuilder.redirectError(errorFile);
            Process process = pbuilder.start();

            process.waitFor();

            if (process.exitValue() != 0) {
                System.err.println("Error running Maze, see error.txt for details");
            }
        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        }
    }
}
