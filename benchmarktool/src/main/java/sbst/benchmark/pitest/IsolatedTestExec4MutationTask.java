package sbst.benchmark.pitest;

import org.junit.runner.Result;
import org.pitest.mutationtest.engine.MutationIdentifier;
import sbst.benchmark.Main;
import sbst.benchmark.junit.StoppingJUnitCore;

import java.io.*;
import java.nio.file.Files;
import java.net.URLClassLoader;
import java.util.*;
import java.util.concurrent.TimeUnit;

/** Isolate threads started by a mutant's test suite in a disposable JVM. */
public class IsolatedTestExec4MutationTask extends TestExec4MutationTask {
    public IsolatedTestExec4MutationTask(String cp, List<String> tests, Set<TestInfo> flaky,
                                        MutationIdentifier id) {
        super(cp, tests, flaky, id);
    }

    @Override
    public MutationResults call() throws IOException, ClassNotFoundException {
        File directory = new File(System.getProperty("sbst.benchmark.mutationEvidence", "mutation-isolation"));
        directory.mkdirs();
        File evidence = Files.createTempDirectory(directory.toPath(), "mutant-").toFile();
        File input = new File(evidence, "input.bin");
        File output = new File(evidence, "result.bin");
        try (PrintWriter id = new PrintWriter(new File(evidence, "mutation.txt"))) {
            id.println(results.getMutation_id());
        }
        try (DataOutputStream data = new DataOutputStream(new FileOutputStream(input))) {
            data.writeInt(testClasses.size());
            for (String test : testClasses) {
                data.writeUTF(test);
            }
            data.writeInt(flakyTests.size());
            for (TestInfo test : flakyTests) {
                data.writeUTF(test.testClass);
                data.writeUTF(test.testMethod);
            }
        }
        String java = Main.JAVA == null ? System.getProperty("java.home") + "/bin/java" : Main.JAVA;
        Process process = new ProcessBuilder(java, "-Xmx1500m", "-ea", "-cp",
                cp + File.pathSeparator + System.getProperty("java.class.path"),
                IsolatedTestExec4MutationTask.class.getName(), input.getAbsolutePath(), output.getAbsolutePath())
                .redirectErrorStream(true).redirectOutput(new File(evidence, "process.log")).start();
        try {
            long limit = Long.getLong("sbst.benchmark.mutantProcessTimeoutMs", 180000L);
            if (!process.waitFor(limit, TimeUnit.MILLISECONDS)) {
                throw new IOException("Isolated mutant exceeded " + limit + " ms: " + evidence);
            }
            if (process.exitValue() != 0 || !output.isFile()) {
                throw new IOException("Isolated mutant did not return a result: " + evidence);
            }
            Result result;
            // JUnit Failure contains the generated test's Class and may contain
            // a subject-specific exception. Neither is on the runner's classpath.
            try (URLClassLoader loader = URLClassLoader.newInstance(urls, getClass().getClassLoader());
                 ObjectInputStream data = new ObjectInputStream(new FileInputStream(output)) {
                     @Override protected Class<?> resolveClass(ObjectStreamClass descriptor)
                             throws IOException, ClassNotFoundException {
                         try {
                             return Class.forName(descriptor.getName(), false, loader);
                         } catch (ClassNotFoundException e) {
                             return super.resolveClass(descriptor);
                         }
                     }
                 }) {
                result = (Result) data.readObject();
            }
            if (result == null) {
                throw new IOException("Isolated mutant returned an interrupted JUnit result: " + evidence);
            }
            results.addJUnitResult(result);
            return processTestResults(result);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("Isolated mutant evaluation interrupted: " + evidence, e);
        } finally {
            process.destroyForcibly();
            try {
                process.waitFor(5, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
    }

    /** Child JVM exits after reporting, even if generated tests leave threads alive. */
    public static void main(String[] args) {
        Main.debugStr = System.out;
        Main.infoStr = System.out;
        try {
            List<Class> classes = new ArrayList<>();
            Set<TestInfo> flaky = new HashSet<>();
            try (DataInputStream data = new DataInputStream(new FileInputStream(args[0]))) {
                int count = data.readInt();
                for (int i = 0; i < count; i++) {
                    String test = data.readUTF();
                    if (test.contains("_scaffolding") || test.contains("ReflectionUtils") || test.contains("EqualityUtils")) {
                        continue;
                    }
                    if (test.startsWith("testcases.")) {
                        test = test.substring("testcases.".length());
                    }
                    classes.add(Class.forName(test, false, IsolatedTestExec4MutationTask.class.getClassLoader()));
                }
                count = data.readInt();
                for (int i = 0; i < count; i++) {
                    flaky.add(new TestInfo(data.readUTF(), data.readUTF()));
                }
            }
            Result result = new StoppingJUnitCore().run(classes, 5000, flaky);
            if (result != null) {
                for (org.junit.runner.notification.Failure failure : result.getFailures()) {
                    System.out.println(failure.getTestHeader());
                    System.out.println(failure.getTrace());
                }
            }
            try (ObjectOutputStream data = new ObjectOutputStream(new FileOutputStream(args[1]))) {
                data.writeObject(result);
            }
            System.exit(0);
        } catch (Throwable error) {
            error.printStackTrace();
            System.exit(2);
        }
    }
}
