package sbst.runtool;

import java.io.*;
import java.util.ArrayList;
import java.util.List;

public class T3Tool implements ITestingTool {

    private String cutClassPath;
    private String cutSupportClassPaths ; // other jars used by CUT
    private File t3Jar = new File("lib", "t3-3.0.1-shaded.jar");
    
    boolean enabledEvoAlg ;
    String worklistType ; // standard/random/lowcovfirst
    
    // worklistty: standard/random/lowcovfirst
    // enableEvo: if true will enable evolutionary trace refinement
    public T3Tool(String worklistType, boolean enableEvo) {
    	enabledEvoAlg = enableEvo ;
    	this.worklistType = worklistType ;
    }

    public List<File> getExtraClassPath() {
        List<File> files = new ArrayList<>();
        if (!t3Jar.exists()) {
            System.err.println("Incorrect T3-jar setting, jar is not at: " + t3Jar.getAbsolutePath());
        } else {
            files.add(t3Jar);
        }
        return files;
    }

    public void initialize(File src, File bin, List<File> classPath) {
        this.cutClassPath = bin.getAbsolutePath() ;
    	StringBuilder sb = new StringBuilder();
        int k = 0 ;
    	for (File f : classPath) {
    		String path = f.getAbsolutePath() ;
    		if (path.equals(cutClassPath)) continue ;
    		if (k>0) sb.append(File.pathSeparator);
    		sb.append(path) ;
    		k++ ;
        }
        this.cutSupportClassPaths = sb.toString();
    }

    public void run(String cutName, long timeBudget) {
        List<String> command;
        ProcessBuilder pbuilder = new ProcessBuilder();
        try {
            command = new ArrayList<>();
            // command.add("java");
            // Explicitly use java >= 11
            command.add("/usr/lib/jvm/java-11-openjdk-amd64/bin/java");  
            command.add("-classpath");
            command.add(t3Jar.getAbsolutePath() + ":" + cutSupportClassPaths);
            command.add("Sequenic.T3.DerivativeSuiteGens.Gen2.G2_forSBST"); // we'll use the G2 engine
            command.add("generate") ;
            command.add(cutName) ; // CUT
            command.add(cutClassPath) ; // classes dir to find CUT (binary) 
            //command.add("./temp/testcases/") ; // where to put generated t3-traces 
            command.add("/home/t3/traces/") ; // where to put generated t3-traces 
            
            command.add("./temp/testcases/") ; // where to put generated test-classes
            // budget was in sec, covert to ms:
            command.add("" + timeBudget*1000) ;
            command.add(worklistType) ; // arg6 worklist-type:  standard/random/lowcovfirst
            command.add(enabledEvoAlg ? "evo" : "random") ;   // arg7 trace-refinement-heuristic: random/evo
            command.add("5") ;     // arg8 the maximum number of times each test-target will be refined
            command.add("true") ;  // arg9 whether or not to use code-coverage guidance
            command.add("false") ; // arg10 whether or not to use staticinfo.txt
            
            System.err.println("Running T3 with command: " + command);
            pbuilder.command(command);

            // redirect error stream to a file
            File errorFile = new File("error.txt");
            pbuilder.redirectError(errorFile);
            Process process = pbuilder.start();

            process.waitFor();

            if (process.exitValue() != 0) {
                System.err.println("Error running T3, see error.txt for details");
            }
        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        }

    }

}
