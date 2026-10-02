package sbst.benchmark.junit;

import org.junit.runner.notification.Failure;
import org.junit.runners.model.TestTimedOutException;

/** Evidenced execution limits/signals, rather than assertions about a mutant. */
public final class NonKillingFailure {
    private NonKillingFailure() {}

    public static boolean isNonKilling(Failure failure) {
        Throwable error = failure.getException();
        return error instanceof InterruptedException || error instanceof TestTimedOutException
                || failure.getTrace().contains("java.lang.Exception: test timed out after");
    }
}
