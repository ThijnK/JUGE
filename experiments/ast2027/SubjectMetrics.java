import java.io.File;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Arrays;
import org.jacoco.core.analysis.Analyzer;
import org.jacoco.core.analysis.CoverageBuilder;
import org.jacoco.core.analysis.IClassCoverage;
import org.jacoco.core.data.ExecutionDataStore;

/** Static bytecode counters; includes constructors and private methods, excludes nested CUTs. */
public final class SubjectMetrics {
    public static void main(String[] args) throws Exception {
        CoverageBuilder coverage = new CoverageBuilder();
        new Analyzer(new ExecutionDataStore(), coverage).analyzeAll(new File(args[0]));
        System.out.println("subject,methods,branches,bytecode_lines,cyclomatic_complexity,physical_source_lines");
        IClassCoverage[] classes = coverage.getClasses().toArray(new IClassCoverage[0]);
        Arrays.sort(classes, (a, b) -> a.getName().compareTo(b.getName()));
        for (IClassCoverage item : classes) {
            if (item.getName().contains("$")) continue;
            String name = item.getName().substring(item.getName().lastIndexOf('/') + 1);
            long lines;
            try (java.util.stream.Stream<String> stream = Files.lines(Paths.get(args[1], name + ".java"))) {
                lines = stream.count();
            }
            System.out.printf("%s,%d,%d,%d,%d,%d%n", name, item.getMethodCounter().getTotalCount(),
                item.getBranchCounter().getTotalCount(), item.getLineCounter().getTotalCount(),
                item.getComplexityCounter().getTotalCount(), lines);
        }
    }
}
