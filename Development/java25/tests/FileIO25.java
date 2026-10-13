import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.Arrays;

public class FileIO25 {
    private static IOException failure(String stage, IOException error) {
        return new IOException("File I/O stage " + stage + ": " + error, error);
    }

    public static void main(String[] args) throws Exception {
        if (Runtime.version().feature() != 25) throw new AssertionError("Need Java 25");
        Path relative = Path.of("java25-relative-check").toAbsolutePath();
        Path resolved = Path.of(System.getProperty("user.dir"), "java25-relative-check");
        if (!relative.equals(resolved)) throw new AssertionError("Wrong relative path resolution");
        Path directory = Path.of(System.getProperty("java.io.tmpdir"));
        Path file = directory.resolve("java25-file-probe-" + System.nanoTime() + ".txt");
        byte[] expected = "Java 25 on PS5: café / 日本語 / 🎮\n".getBytes(StandardCharsets.UTF_8);
        try {
            // Match the private-file mode used by the passing native probe.
            // createFile retains exclusive creation; existing files are never reused.
            Files.createFile(file, PosixFilePermissions.asFileAttribute(
                    PosixFilePermissions.fromString("rw-------")));
        } catch (IOException error) {
            throw failure("create (0600)", error);
        }
        String stage = "write";
        try {
            Files.write(file, expected, StandardOpenOption.WRITE);
            stage = "read";
            if (!Arrays.equals(expected, Files.readAllBytes(file))) {
                throw new AssertionError("File bytes changed");
            }
            stage = "size";
            if (Files.size(file) != expected.length) throw new AssertionError("Wrong file size");
        } catch (IOException error) {
            throw failure(stage, error);
        } finally {
            try {
                Files.delete(file);
            } catch (IOException error) {
                throw failure("delete", error);
            }
        }
        if (Files.exists(file)) throw new AssertionError("Probe file still exists");
        System.out.println("JAVA_FILE_IO_OK");
    }
}
