package sbst.benchmark.pitest;

import org.junit.Test;
import org.junit.runner.Result;
import java.util.Collections;
import static org.junit.Assert.*;

public class TestInterruptedMutation {
    public static class MixedTimeout {
        @Test public void passes() {}
        @Test public void timesOut() throws Exception {
            throw new Exception("test timed out after 5000 milliseconds");
        }
    }
    @Test public void timeoutWithoutKillingFailureIsIgnoredEvenWhenOtherTestsPass() {
        sbst.benchmark.Main.debugStr = System.out;
        sbst.benchmark.Main.infoStr = System.out;
        TestExec4MutationTask task = new TestExec4MutationTask("",
                Collections.<String>emptyList(), Collections.<TestInfo>emptySet(), new org.pitest.mutationtest.engine.MutationIdentifier(
                        new org.pitest.mutationtest.engine.Location(org.pitest.classinfo.ClassName.fromString("Fixture"),
                            org.pitest.mutationtest.engine.MethodName.fromString("method"), "()V"), 0, "fixture"));
        Result result = org.junit.runner.JUnitCore.runClasses(MixedTimeout.class);
        assertEquals(MutationResults.State.IGNORED, task.processTestResults(result).getState());
    }

    @Test
    public void missingResultIsNotASurvivingMutant() {
        TestExec4MutationTask task = new TestExec4MutationTask("",
                Collections.<String>emptyList(), Collections.<TestInfo>emptySet(), null);
        assertEquals(MutationResults.State.IGNORED, task.processTestResults(null).getState());
        assertTrue(task.getExecutionResults().isEmpty());
        assertEquals(0, task.countFailingTests());
    }

    @Test
    public void completedPassingResultStillSurvives() {
        TestExec4MutationTask task = new TestExec4MutationTask("",
                Collections.<String>emptyList(), Collections.<TestInfo>emptySet(), null);
        assertEquals(MutationResults.State.SURVIVED, task.processTestResults(new Result()).getState());
    }
}
