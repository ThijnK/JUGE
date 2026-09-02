package sbst.runtool;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;

public class Main {
    public static void main(String[] args) throws IOException {
    	String worklistType = "random" ;
    	boolean enabledEvoAlg = true ;
    	if (args.length >= 1) worklistType = args[0] ;
    	if (args.length >= 2) enabledEvoAlg = Boolean.parseBoolean(args[1]) ;
        RunTool runtool = new RunTool(new T3Tool(worklistType,enabledEvoAlg), new InputStreamReader(System.in),
                new OutputStreamWriter(System.out));
        runtool.run();
    }
}
