import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Arrays;

public class FileIO25 {
    public static void main(String[] args) throws Exception {
        if (Runtime.version().feature() != 25) throw new AssertionError("Need Java 25");
        // Exercise the explicit user.dir resolution used by the PS5 sandbox.
        Path relative = Path.of("java25-relative-check").toAbsolutePath();
        Path resolved = Path.of(System.getProperty("user.dir"), "java25-relative-check");
        if (!relative.equals(resolved)) throw new AssertionError("Wrong relative path resolution");
        Path directory = Path.of(System.getProperty("java.io.tmpdir"));
        Path file = directory.resolve("java25-file-probe-" + System.nanoTime() + ".txt");
        byte[] expected = "Java 25 on PS5: café / 日本語 / 🎮\n".getBytes(StandardCharsets.UTF_8);
        System.out.println("FILE_IO: creating unique probe file");
        Files.write(file, expected, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
        try {
            System.out.println("FILE_IO: reading and checking UTF-8 bytes");
            if (!Arrays.equals(expected, Files.readAllBytes(file))) {
                throw new AssertionError("File bytes changed");
            }
            if (Files.size(file) != expected.length) throw new AssertionError("Wrong file size");
        } finally {
            Files.delete(file);
        }
        if (Files.exists(file)) throw new AssertionError("Probe file still exists");
        System.out.println("JAVA_FILE_IO_OK");
    }
}
