package sbst.runtool;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.DeserializationFeature;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Set;

/** One named MAZE invocation configuration; search JSON remains opaque to JUGE. */
final class MazeExperiment {
    static final ObjectMapper JSON = new ObjectMapper()
            .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    private static final Set<String> MANAGED = new HashSet<>(Arrays.asList(
            "--classpath", "--class-name", "--output-path", "--time-budget", "--junit-version",
            "--concrete-driven", "--export-summary", "--help", "--version"));
    final Path directory;
    final JsonNode definition;
    final String name;
    final String mode;
    final List<String> arguments = new ArrayList<>();

    MazeExperiment(Path file) throws IOException {
        directory = file.toAbsolutePath().getParent();
        definition = JSON.readTree(file.toFile());
        if (definition == null || !definition.isObject()) {
            throw new IllegalArgumentException("Experiment must be a JSON object");
        }
        Iterator<String> fields = definition.fieldNames();
        while (fields.hasNext()) {
            String field = fields.next();
            if (!Arrays.asList("name", "mode", "arguments").contains(field)) {
                throw new IllegalArgumentException("Unknown experiment field: " + field);
            }
        }
        name = text("name");
        if (!name.matches("[A-Za-z0-9][A-Za-z0-9._-]*")) {
            throw new IllegalArgumentException("Experiment name must contain only letters, digits, '.', '_' or '-'");
        }
        mode = text("mode");
        if (!mode.equals("symbolic") && !mode.equals("concrete")) {
            throw new IllegalArgumentException("Experiment mode must be symbolic or concrete");
        }
        JsonNode values = definition.path("arguments");
        if (!values.isArray()) throw new IllegalArgumentException("Experiment arguments must be an array");
        for (JsonNode value : values) {
            if (!value.isTextual()) throw new IllegalArgumentException("Each argument must be a string");
            String argument = value.textValue();
            String option = argument.split("=", 2)[0];
            // Prevent response files and aliases from overriding the benchmark's owned settings.
            if (argument.startsWith("@") || MANAGED.contains(option)
                    || argument.matches("-[cnobjChV].*")) {
                throw new IllegalArgumentException("JUGE supplies this setting; remove it from arguments: " + argument);
            }
            arguments.add(argument);
        }
    }

    private String text(String field) {
        JsonNode value = definition.path(field);
        if (!value.isTextual() || value.textValue().isEmpty()) {
            throw new IllegalArgumentException("Experiment requires a nonempty '" + field + "'");
        }
        return value.textValue();
    }
}
