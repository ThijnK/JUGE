package sbst.runtool;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.file.Paths;

public class Main {
    public static void main(String[] args) throws IOException {
        if (args.length != 2) {
            throw new IllegalArgumentException("Usage: Main <unpacked-maze-directory> <experiment.json>");
        }
        MazeTool tool = new MazeTool(Paths.get(args[0]), Paths.get(args[1]));
        new RunTool(tool, new InputStreamReader(System.in), new OutputStreamWriter(System.out)).run();
    }
}
