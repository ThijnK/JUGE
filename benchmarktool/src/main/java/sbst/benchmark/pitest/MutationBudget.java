package sbst.benchmark.pitest;

import org.junit.Test;
import java.lang.reflect.Method;
import java.util.List;

/** Common suite-size allowance; never changes a generated test's own timeout. */
public final class MutationBudget {
    public static final long DEFAULT_TEST_TIMEOUT_MS = 5000L;
    private MutationBudget() { }

    static final class Plan {
        final int classes;
        final int tests;
        final long testTimeoutsMs;
        final long limitMs;
        Plan(int classes, int tests, long testTimeoutsMs, long limitMs) {
            this.classes = classes;
            this.tests = tests;
            this.testTimeoutsMs = testTimeoutsMs;
            this.limitMs = limitMs;
        }
    }

    static long allowance(long testTimeoutsMs, int classes, long startupMs,
                          long fixtureMs, long minimumMs, long maximumMs) {
        if (classes < 0 || testTimeoutsMs < 0 || startupMs < 0 || fixtureMs < 0
                || minimumMs <= 0 || maximumMs <= 0) {
            throw new IllegalArgumentException("Invalid mutant measurement allowance");
        }
        // Saturate before arithmetic overflow; the total budget always bounds us.
        long value = Math.min(startupMs, maximumMs);
        long room = maximumMs - value;
        long fixtures = classes == 0 ? 0 : Math.min(fixtureMs, room / classes) * classes;
        if (classes != 0 && fixtureMs > room / classes) {
            return maximumMs;
        }
        value += fixtures;
        value += Math.min(testTimeoutsMs, maximumMs - value);
        return Math.min(maximumMs, Math.max(minimumMs, value));
    }

    static Plan inspect(List<Class<?>> classes, long startupMs, long fixtureMs,
                        long minimumMs, long maximumMs) {
        int count = 0;
        long timeouts = 0;
        for (Class<?> type : classes) {
            for (Method method : type.getMethods()) {
                Test test = method.getAnnotation(Test.class);
                if (test != null) {
                    count++;
                    long timeout = test.timeout() == 0 ? DEFAULT_TEST_TIMEOUT_MS : test.timeout();
                    timeouts += Math.min(timeout, Long.MAX_VALUE - timeouts);
                }
            }
        }
        return new Plan(classes.size(), count, timeouts,
                allowance(timeouts, classes.size(), startupMs, fixtureMs, minimumMs, maximumMs));
    }
}
