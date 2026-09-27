import java.util.Arrays;
import sbst.benchmark.pitest.PITWrapper;

/** Integration check on a generated fixture with more than 400 mutants. */
public final class MutationPolicyCheck {
    public static void main(String[] args) {
        System.clearProperty("sbst.benchmark.allMutants");
        int sampled = new PITWrapper(args[0], "ManyMutants", Arrays.asList("UnusedTest"))
            .getGeneratedMutants().getNumberOfMutations();
        System.setProperty("sbst.benchmark.allMutants", "true");
        int all = new PITWrapper(args[0], "ManyMutants", Arrays.asList("UnusedTest"))
            .getGeneratedMutants().getNumberOfMutations();
        if (all <= 400 || sampled >= all || sampled != all / 3) {
            throw new AssertionError("Unexpected mutation counts: sampled=" + sampled + ", all=" + all);
        }
        System.out.println("Mutation policy verified: sampled=" + sampled + ", all=" + all);
    }
}
