import java.io.InputStream;
import java.lang.reflect.InvocationTargetException;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.jar.JarFile;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

public class ZipJar25 {
    public static void main(String[] args) throws Exception {
        String stage = "locate archive";
        try {
            if (Runtime.version().feature() != 25) throw new AssertionError("Need Java 25");
            String supplied = System.getProperty("ps5.probe.jar",
                    "/app0/assets/java25/jars/probe.jar");
            Path jar = Path.of(supplied);
            stage = "open ZIP";
            try (ZipFile zip = new ZipFile(jar.toFile())) {
                if (zip.size() != 5) throw new AssertionError("Wrong entry count: " + zip.size());
                stage = "stored ZIP entry";
                ZipEntry stored = zip.getEntry("fixtures/stored.txt");
                if (stored == null || stored.getMethod() != ZipEntry.STORED)
                    throw new AssertionError("Stored entry missing or wrong method");
                try (InputStream input = zip.getInputStream(stored)) {
                    if (!Arrays.equals(input.readAllBytes(), "ZIP_STORED_OK\n".getBytes(StandardCharsets.UTF_8)))
                        throw new AssertionError("Stored entry bytes changed");
                }
                stage = "deflated ZIP entry";
                ZipEntry compressed = zip.getEntry("fixtures/deflated.bin");
                if (compressed == null || compressed.getMethod() != ZipEntry.DEFLATED)
                    throw new AssertionError("Deflated entry missing or wrong method");
                try (InputStream input = zip.getInputStream(compressed)) {
                    byte[] actual = input.readAllBytes();
                    if (actual.length != 65536) throw new AssertionError("Wrong inflated length");
                    for (int i = 0; i < actual.length; i++)
                        if (actual[i] != (byte)(i * 31 + 7)) throw new AssertionError("Inflated bytes changed at " + i);
                }
            }
            stage = "JAR manifest";
            try (JarFile archive = new JarFile(jar.toFile())) {
                if (archive.getManifest() == null || !"PS5 Java 25 probe".equals(
                        archive.getManifest().getMainAttributes().getValue("Implementation-Title")))
                    throw new AssertionError("Manifest missing or incorrect");
            }
            stage = "JAR class loader";
            // The payload exists ONLY in the JAR. No JNI DefineClass is used for it.
            try (URLClassLoader loader = new URLClassLoader(new URL[]{jar.toUri().toURL()},
                    ClassLoader.getPlatformClassLoader())) {
                Class<?> payload = Class.forName("ps5probe.JarHello25", true, loader);
                if (payload.getClassLoader() != loader) throw new AssertionError("Wrong defining loader");
                stage = "JAR class execution and UTF-8 resource";
                Object result = payload.getMethod("run").invoke(null);
                if (!"JAR_CLASS_OK 49995000 café / 日本語 / 🎮\n".equals(result))
                    throw new AssertionError("Wrong JAR result: " + result);
            }
            System.out.println("JAVA_ZIP_JAR_OK");
        } catch (Throwable error) {
            Throwable detail = error instanceof InvocationTargetException && error.getCause() != null
                    ? error.getCause() : error;
            throw new Exception("ZIP/JAR stage " + stage + ": " + detail, detail);
        }
    }
}
