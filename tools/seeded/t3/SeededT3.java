import Sequenic.T3.T3Random;
import Sequenic.T3.DerivativeSuiteGens.Gen2.G2_forSBST;
import java.util.Arrays;

/** Seed the public T3 RNG, then delegate configuration and deadlines upstream. */
public final class SeededT3 {
    public static void main(String[] args) throws Throwable {
        T3Random.getRnd().setSeed(Long.parseLong(args[0]));
        G2_forSBST.main(Arrays.copyOfRange(args, 1, args.length));
    }
}
