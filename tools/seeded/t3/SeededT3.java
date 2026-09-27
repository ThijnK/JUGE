import Sequenic.T3.T3Random;
import Sequenic.T3.DerivativeSuiteGens.Gen2.G2;
import Sequenic.T3.DerivativeSuiteGens.Gen2.G2Config;
import java.nio.file.Files;
import java.nio.file.Paths;

/** Calls the upstream SBST generator without its unconditional exit(-1). */
public final class SeededT3 {
    public static void main(String[] args) throws Exception {
        long seed = Long.parseLong(args[0]);
        long budgetMillis = Long.parseLong(args[1]);
        T3Random.getRnd().setSeed(seed);
        // Worklist also owns an RNG: the pinned compatibility patch reads this property.
        System.setProperty("juge.seed", Long.toString(seed));
        Files.createDirectories(Paths.get("trdir"));
        Files.createDirectories(Paths.get("temp/testcases"));
        G2Config config = new G2Config();
        config.CUTrootDir = args[3];
        config.dirOfStaticInfo = "trdir";
        config.dirToSaveSuites = "trdir";
        config.dirToSaveJunit = "temp/testcases";
        config.injectOracles = true;
        config.regressionMode = true;
        config.worklistType = "standard";
        config.refinementHeuristic = "random";
        config.generateJunitForEachSuite = true;
        config.maxNumberOfRefinements_ofEachTarget = 8;
        config.useCoverageGuidance = true;
        config.useStaticInfo = false;
        config.maxPrefixLength = 6;
        config.maxSuffixLength = 1;
        config.numberOfPrefixes = 10;
        config.includePrivateAndDefaultMembers = true;
        try {
            G2.generateSuites(args[2], config, budgetMillis);
        } catch (G2.TimeBudgetException expected) {
            System.err.println("T3 reached its generation budget");
        }
    }
}
