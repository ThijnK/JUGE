package sbst.runtool;

import java.io.*;
import java.util.ArrayList;
import java.util.List;

public class KexTool implements ITestingTool {


    private static final String KEX_HOME = new File("lib", "kex-0.0.11").getAbsolutePath();
    private String classPath;
    private File kexJar = java.nio.file.Paths.get(KEX_HOME, "kex-runner", "target", "kex-runner-0.0.11-jar-with-dependencies.jar").toFile();
    private File kexPolicy = new File(KEX_HOME, "kex.policy");

    public List<File> getExtraClassPath() {
        // Kex does not require extra classpath jars
        return new ArrayList<>();
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
        List<String> command = new ArrayList<>();
        ProcessBuilder pbuilder = new ProcessBuilder();
        try {
            pbuilder.environment().put("KEX_HOME", KEX_HOME);

            command.add("java");
            command.add("-Xmx8g");
            command.add("-Djava.security.manager");
            command.add("-Djava.security.policy==" + kexPolicy.getAbsolutePath());
            command.add("-Dlogback.statusListenerClass=ch.qos.logback.core.status.NopStatusListener");
            command.add("-jar");
            command.add(kexJar.getAbsolutePath());
            command.add("--classpath");
            command.add(classPath);
            command.add("--target");
            command.add(className);
            command.add("--output");
            command.add("./temp/testcases/");
            command.add("--mode");
            command.add("concolic");
            // Optionally, add time budget if Kex supports it (not in kex.py, so omitted)

            System.err.println("Running Kex with command: " + command);
            pbuilder.command(command);

            // redirect error stream to a file
            File errorFile = new File("error.txt");
            pbuilder.redirectError(errorFile);
            Process process = pbuilder.start();

            process.waitFor();

            if (process.exitValue() != 0) {
                System.err.println("Error running Kex, see error.txt for details");
            }
        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        }
    }
}
