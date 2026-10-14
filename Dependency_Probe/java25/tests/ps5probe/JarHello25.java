package ps5probe;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;

public class JarHello25 {
    public static String run() throws Exception {
        if (Runtime.version().feature() != 25) throw new AssertionError("Need Java 25");
        long sum = 0;
        for (int i = 0; i < 10000; i++) sum += i;
        try (InputStream input = JarHello25.class.getResourceAsStream("message.txt")) {
            if (input == null) throw new AssertionError("JAR resource missing");
            String message = new String(input.readAllBytes(), StandardCharsets.UTF_8);
            return "JAR_CLASS_OK " + sum + " " + message;
        }
    }
}
