package sbst.runtool;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/** Launches a packaged MAZE and publishes tests only after confirmed completion. */
public class MazeTool implements ITestingTool {
    private final Path home;
    private final MazeExperiment experiment;
    private final Path temp = Paths.get("temp").toAbsolutePath();
    private final ObjectNode batch = MazeExperiment.JSON.createObjectNode();
    private final ArrayNode invocations = batch.putArray("invocations");
    private String classPath;

    public MazeTool(Path home, Path configuration) throws IOException {
        this.home = home.toAbsolutePath();
        this.experiment = new MazeExperiment(configuration);
        if (!Files.isExecutable(this.home.resolve("maze")) || !Files.isRegularFile(this.home.resolve("maze.jar"))) {
            throw new IllegalArgumentException("MAZE_HOME must be an unpacked MAZE Linux package: " + home);
        }
        String batchId = System.getenv("JUGE_MAZE_BATCH_ID");
        batch.put("batchId", batchId == null ? UUID.randomUUID().toString() : batchId);
        batch.set("experiment", experiment.definition);
        batch.put("mazeJarSha256", sha256(this.home.resolve("maze.jar")));
    }

    public List<File> getExtraClassPath() {
        // JUGE already supplies JUnit; generated suites have no dependency on MAZE.
        return Collections.emptyList();
    }

    public void initialize(File src, File bin, List<File> dependencies) {
        List<String> paths = new ArrayList<>();
        paths.add(bin.getAbsolutePath());
        for (File dependency : dependencies) paths.add(dependency.getAbsolutePath());
        classPath = String.join(File.pathSeparator, paths);
        try {
            writeBatch("running");
        } catch (IOException e) {
            throw new IllegalStateException("Cannot initialize MAZE completion record", e);
        }
    }

    public void run(String className, long timeBudget) {
        Process process = null;
        try {
            Path invocation = Files.createTempDirectory(temp, "maze-run-");
            Path tests = Files.createDirectory(invocation.resolve("tests"));
            List<String> command = new ArrayList<>();
            command.add(home.resolve("maze").toString());
            command.add("--classpath=" + classPath);
            command.add("--class-name=" + className);
            command.add("--output-path=" + tests);
            command.add("--time-budget=" + timeBudget);
            command.add("--concrete-driven=" + experiment.mode.equals("concrete"));
            command.add("--junit-version=JUnit4");
            command.add("--export-summary=true");
            command.addAll(experiment.arguments);
            process = new ProcessBuilder(command).directory(experiment.directory.toFile())
                    .redirectErrorStream(true).redirectOutput(invocation.resolve("maze.log").toFile()).start();
            int exit = process.waitFor();
            if (exit != 0) throw new IOException("MAZE exited " + exit + "; see " + invocation.resolve("maze.log"));
            Path statusPath = tests.resolve(className + "-run-status.json");
            JsonNode status = MazeExperiment.JSON.readTree(statusPath.toFile());
            if (!"completed".equals(status.path("outcome").asText())
                    || !className.equals(status.path("target").asText())
                    || !experiment.mode.equals(status.path("mode").asText())
                    || status.path("invocationId").asText().isEmpty()) {
                throw new IOException("MAZE did not produce a matching completion record: " + statusPath);
            }
            ObjectNode evidence = invocations.addObject();
            evidence.put("target", className);
            evidence.put("timeBudget", timeBudget);
            evidence.put("invocationId", status.path("invocationId").asText());
            evidence.put("status", temp.relativize(statusPath).toString());
            evidence.put("sha256", sha256(statusPath));
            // Only validated Java sources enter the directory consumed by JUGE.
            Path destination = Files.createDirectories(temp.resolve("testcases"));
            try (Stream<Path> sources = Files.walk(tests)) {
                for (Path source : sources.filter(p -> p.toString().endsWith(".java")).collect(Collectors.toList())) {
                    Path target = destination.resolve(tests.relativize(source));
                    Files.createDirectories(target.getParent());
                    Files.copy(source, target, StandardCopyOption.REPLACE_EXISTING);
                }
            }
            writeBatch("running");
        } catch (IOException | InterruptedException e) {
            if (process != null && process.isAlive()) process.destroyForcibly();
            if (e instanceof InterruptedException) Thread.currentThread().interrupt();
            try { writeBatch("failed"); } catch (IOException failure) { e.addSuppressed(failure); }
            throw new IllegalStateException("MAZE generation failed for " + className, e);
        }
    }

    public void finish() {
        try {
            writeBatch("completed");
        } catch (IOException e) {
            throw new IllegalStateException("Cannot record completed MAZE batch", e);
        }
    }

    private void writeBatch(String outcome) throws IOException {
        Files.createDirectories(temp);
        batch.put("outcome", outcome);
        Path staging = Files.createTempFile(temp, ".maze-batch-", ".json");
        try {
            MazeExperiment.JSON.writerWithDefaultPrettyPrinter().writeValue(staging.toFile(), batch);
            Files.move(staging, temp.resolve("maze-batch.json"), StandardCopyOption.REPLACE_EXISTING,
                    StandardCopyOption.ATOMIC_MOVE);
        } finally {
            Files.deleteIfExists(staging);
        }
    }

    private static String sha256(Path file) throws IOException {
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(file));
            StringBuilder text = new StringBuilder();
            for (byte b : hash) text.append(String.format("%02x", b & 0xff));
            return text.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new AssertionError(e);
        }
    }
}
