package sbst.runtool;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.evosuite.EvoSuite;

public class EvoSuiteTool implements ITestingTool {

    /**
     * The class under test classpath
     */
    private String cutClassPath;

    private EvoSuite evo;

    /**
     * List of additional class path entries required by a testing tool
     *
     * @return List of directories/jar files
     */
    @Override
    public List<File> getExtraClassPath() {
        List<File> files = new ArrayList<File>();
        File evo = new File("lib", "evosuite.jar");
        if (!evo.exists()) {
            System.err.println("Wrong EvoSuite jar setting, jar is not at: " + evo.getAbsolutePath());
        } else {
            files.add(evo);
        }
        return files;
    }

    /**
     * Initialize the testing tool, with details about the code to be tested (SUT)
     * Called only once.
     *
     * @param src       Directory containing source files of the SUT
     * @param bin       Directory containing class files of the SUT
     * @param classPath List of directories/jar files (dependencies of the SUT)
     */
    @Override
    public void initialize(File src, File bin, List<File> classPath) {
        StringBuilder sb = new StringBuilder();
        sb.append(bin.getAbsolutePath());
        for (File f : classPath) {
            sb.append(File.pathSeparator);
            sb.append(f.getAbsolutePath());
        }
        this.cutClassPath = sb.toString();
        this.evo = new EvoSuite();
    }

    /**
     * Run the test tool, and let it generate test cases for a given class
     *
     * @param cName      Name of the class for which unit tests should be generated
     * @param timeBudget How long the tool must run to test the class (in seconds
     */
    @Override
    public void run(String cName, long timeBudget) {
        // Assign 50% of time budget to search phase
        long halfTimeBudget = timeBudget / 2L;
        long searchBudget = halfTimeBudget;
        if (timeBudget % 2L != 0)
            searchBudget++; // If uneven time budget, favor search phase

        // The rest of the time budget is divided equally between assertion generation,
        // initialization, and compilation/flakiness checks
        // Minimization is turned off, so it does not get any time budget
        long initBudget = halfTimeBudget / 3L;
        long assertionBudget = halfTimeBudget / 3L;
        long checksBudget = halfTimeBudget / 3L;
        // Distribute the remainder, prioritizing assertion, then init
        long remainder = halfTimeBudget % 3L;
        if (remainder > 0)
            assertionBudget++;
        if (remainder > 1)
            initBudget++;

        System.err.println("Time Budget: " + timeBudget);
        System.err.println("  Search: " + searchBudget);
        System.err.println("  Initialization: " + initBudget);
        System.err.println("  Assertions: " + assertionBudget);
        System.err.println("  Checks: " + checksBudget);
        List<String> commands = new ArrayList<String>();
        commands.addAll(Arrays.asList(
                "-projectCP=" + this.cutClassPath,
                "-class", cName,
                "-Dshow_progress=false",
                "-Dstopping_condition=MAXTIME",
                "-Dassertion_strategy=all",
                "-Dtest_comments=false",
                "-Dminimize=false",
                "-Dinline=false",
                "-Dcoverage=false",
                "-Dvariable_pool=true",
                "-Dnew_statistics=false",
                "-Dstatistics_backend=NONE",
                "-Dsearch_budget=" + searchBudget,
                "-Dinitialization_timeout=" + initBudget,
                "-Dassertion_timeout=" + assertionBudget,
                "-Djunit_check_timeout=" + checksBudget,
                // Write timeout is the total time budget to adhere to external
                // time budget imposed by JUGE (but usually this is really fast,
                // so does not matter much)
                "-Dwrite_junit_timeout=" + timeBudget,
                "-Dtest_dir=temp/testcases",
                "-Dreuse_leftover_time=true"));
        String[] command = new String[commands.size()];
        commands.toArray(command);
        this.evo.parseCommandLine(command);
    }
}
