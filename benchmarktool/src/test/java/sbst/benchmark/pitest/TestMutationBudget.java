package sbst.benchmark.pitest;

import org.junit.Test;
import java.util.Arrays;
import static org.junit.Assert.*;

public class TestMutationBudget {
    public static class MixedTimeouts {
        @Test public void defaultTimeout() { }
        @Test(timeout = 12000) public void explicitTimeout() { }
    }

    @Test public void countsMethodsAndPreservesExplicitTimeouts() {
        MutationBudget.Plan plan = MutationBudget.inspect(Arrays.<Class<?>>asList(MixedTimeouts.class),
                30000, 10000, 1, 3600000);
        assertEquals(2, plan.tests);
        assertEquals(17000, plan.testTimeoutsMs);
        assertEquals(57000, plan.limitMs);
        try {
            assertEquals(12000, MixedTimeouts.class.getMethod("explicitTimeout").getAnnotation(Test.class).timeout());
            assertEquals(0, MixedTimeouts.class.getMethod("defaultTimeout").getAnnotation(Test.class).timeout());
        } catch (NoSuchMethodException impossible) {
            throw new AssertionError(impossible);
        }
    }

    @Test public void largeSuiteFitsSequentialTimeoutsWithinTotalCap() {
        assertEquals(1620000, MutationBudget.allowance(106 * 5000L, 106, 30000, 10000, 180000, 3600000));
        assertEquals(180000, MutationBudget.allowance(5000, 1, 30000, 10000, 180000, 3600000));
        assertEquals(3600000, MutationBudget.allowance(Long.MAX_VALUE, Integer.MAX_VALUE, 30000, Long.MAX_VALUE, 180000, 3600000));
        assertEquals(3600000, MutationBudget.allowance(Long.MAX_VALUE, 1, 30000, 10000, 180000, 3600000));
    }
}
