package sbst.runtool;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;

public class Main {
    public static void main(String[] args) throws IOException {
        String strategy = "DFS";
        //String concreteDriven = "false";
        String minimalisticSuite = "false" ;
        String pathLengthToCover = "0" ;
        String pathAging = "-1" ;
        if (args.length >= 4) {
        	pathAging = args[3];
        }
        if (args.length >= 3) {
        	pathLengthToCover = args[2];
        }
        if (args.length >= 2) {
        	minimalisticSuite = args[1];
        }
        if (args.length >= 1) {
        	strategy = args[0];
        }
 
        MazeTool tool = new MazeTool(strategy, minimalisticSuite, pathLengthToCover, pathAging);
        RunTool runtool = new RunTool(tool, new InputStreamReader(System.in),
                new OutputStreamWriter(System.out));
        runtool.run();
    }
}
