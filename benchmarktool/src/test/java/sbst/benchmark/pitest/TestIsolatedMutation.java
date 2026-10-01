package sbst.benchmark.pitest;

import org.junit.Test;
import org.junit.Before;
import org.junit.After;
import sbst.benchmark.Main;
import java.util.Collections;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;
import javax.tools.ToolProvider;
import static org.junit.Assert.*;

public class TestIsolatedMutation {
    public static class Passing {
        @Test public void passes() {
            assertTrue(true);
        }
    }
    public static class Failing {
        @Test public void fails() {
            fail("expected failure");
        }
    }
    public static class Leaking {
        @Test public void leavesThreadBehind() {
            new Thread(() -> {
                while (true) {
                    Thread.yield();
                }
            }).start();
        }
    }
    public static class Stuck {
        @org.junit.BeforeClass public static void blocks() throws InterruptedException {
            Thread.sleep(60000);
        }
        @Test public void neverRuns() {
            fail();
        }
    }

    @Before public void setup() {
        Main.debugStr = System.out;
        Main.infoStr = System.out;
        System.setProperty("sbst.benchmark.mutationEvidence", "target/mutation-isolation-tests");
    }

    @After public void cleanup() {
        System.clearProperty("sbst.benchmark.mutationEvidence");
    }

    private MutationResults run(Class<?> test) throws Exception {
        return new IsolatedTestExec4MutationTask(System.getProperty("java.class.path"),
                Collections.singletonList(test.getName()), Collections.<TestInfo>emptySet(), null).call();
    }

    @Test public void passingAndFailingResultsSurviveTransport() throws Exception {
        assertEquals(MutationResults.State.SURVIVED, run(Passing.class).getState());
        assertEquals(MutationResults.State.KILLED, run(Failing.class).getState());
    }

    @Test public void generatedTestMayBeAbsentFromParentClasspath() throws Exception {
        Path dir = Files.createTempDirectory(new java.io.File("target").toPath(), "generated-test-");
        Path source = dir.resolve("GeneratedFailure.java");
        Files.write(source, ("public class GeneratedFailure { "
                + "public static class Problem extends RuntimeException {} "
                + "@org.junit.Test public void fails() { throw new Problem(); } }")
                .getBytes(StandardCharsets.UTF_8));
        String cp = System.getProperty("java.class.path");
        assertEquals(0, ToolProvider.getSystemJavaCompiler().run(null, null, null,
                "-cp", cp, "-d", dir.toString(), source.toString()));
        MutationResults result = new IsolatedTestExec4MutationTask(dir + java.io.File.pathSeparator + cp,
                Collections.singletonList("GeneratedFailure"), Collections.<TestInfo>emptySet(), null).call();
        assertEquals(MutationResults.State.KILLED, result.getState());
    }

    @Test public void mutantPrecedesAnOriginalSubjectInAToolDependency() throws Exception {
        Path dir = Files.createTempDirectory(new java.io.File("target").toPath(), "duplicate-subject-");
        Path original = Files.createDirectory(dir.resolve("original"));
        Path mutant = Files.createDirectory(dir.resolve("mutant"));
        Path copied = Files.createDirectory(dir.resolve("copied"));
        Path tests = Files.createDirectory(dir.resolve("tests"));
        String cp = System.getProperty("java.class.path");
        for (Path destination : new Path[] { original, mutant }) {
            Path source = destination.resolve("DuplicateSubject.java");
            Files.write(source, ("public class DuplicateSubject { public static int value() { return "
                    + (destination.equals(original) ? "1" : "2") + "; } }").getBytes(StandardCharsets.UTF_8));
            assertEquals(0, ToolProvider.getSystemJavaCompiler().run(null, null, null,
                    "-d", destination.toString(), source.toString()));
        }
        Path test = tests.resolve("DuplicateSubjectTest.java");
        Files.write(test, ("public class DuplicateSubjectTest { @org.junit.Test public void value() { "
                + "org.junit.Assert.assertEquals(1, DuplicateSubject.value()); } }").getBytes(StandardCharsets.UTF_8));
        assertEquals(0, ToolProvider.getSystemJavaCompiler().run(null, null, null,
                "-cp", original + java.io.File.pathSeparator + cp, "-d", tests.toString(), test.toString()));
        String measurement = tests + java.io.File.pathSeparator + original + java.io.File.pathSeparator + cp;
        String mutated = MutationsEvaluator.mutationClassPath(measurement, copied.toString(), copied.toString(), mutant.toString());
        assertEquals(MutationResults.State.KILLED, new IsolatedTestExec4MutationTask(mutated,
                Collections.singletonList("DuplicateSubjectTest"), Collections.<TestInfo>emptySet(), null).call().getState());
    }

    @Test(timeout = 15000) public void leakedThreadDoesNotPreventChildExit() throws Exception {
        assertEquals(MutationResults.State.SURVIVED, run(Leaking.class).getState());
    }

    @Test(timeout = 15000) public void processDeadlineProducesNoScore() throws Exception {
        System.setProperty("sbst.benchmark.mutantProcessTimeoutMs", "2000");
        try {
            run(Stuck.class);
            fail("Missing child result must fail measurement");
        } catch (IOException expected) {
            assertTrue(expected.getMessage().contains("exceeded"));
        } finally {
            System.clearProperty("sbst.benchmark.mutantProcessTimeoutMs");
        }
    }
}
