package sbst.runtool;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;

public class Main {
    public static void main(String[] args) throws IOException {
        String strategy = "DFS";
        String concreteDriven = "false";
        if (args.length > 1) {
            strategy = args[0];
            concreteDriven = args[1];
        } else if (args.length > 0) {
            strategy = args[0];
        }

        MazeTool tool = new MazeTool(strategy, concreteDriven);
        RunTool runtool = new RunTool(tool, new InputStreamReader(System.in),
                new OutputStreamWriter(System.out));
        runtool.run();
    }
}
