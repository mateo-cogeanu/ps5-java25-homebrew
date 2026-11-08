/* SPDX-License-Identifier: GPL-3.0-or-later */
public final class HelloLts {
    private static native int nativeMultiply(int a, int b);

    public static int run() throws Exception {
        if (Runtime.version().feature() != 17) throw new AssertionError("Expected real Java17");
        if (nativeMultiply(6, 7) != 42) throw new AssertionError("JNI arguments/result");
        long value = 0;
        for (int i = 0; i < 10000; i++) value += i;
        if (value != 49995000L) throw new AssertionError("Java arithmetic");
        if (!"PS5 \u03c0 \ud83c\udfae".equals(new String("PS5 \u03c0 \ud83c\udfae".toCharArray())))
            throw new AssertionError("UTF16 string");
        if (StrictMath.sin(0) != 0 || StrictMath.cos(0) != 1 || StrictMath.sqrt(144) != 12)
            throw new AssertionError("Original StrictMath natives");
        try {
            Integer.parseInt("expected exception");
            throw new AssertionError("Exception missing");
        } catch (NumberFormatException expected) { }
        final int[] worker = {0};
        Thread thread = new Thread(() -> worker[0] = nativeMultiply(17, 3), "Java17 probe worker");
        thread.start();
        thread.join(5000);
        if (thread.isAlive() || worker[0] != 51) throw new AssertionError("Java thread/JNI");
        return 17;
    }

    private HelloLts() { }
}
