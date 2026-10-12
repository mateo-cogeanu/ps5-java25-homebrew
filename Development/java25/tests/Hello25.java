public class Hello25 {
    public static void main(String[] args) throws Exception {
        if (Runtime.version().feature() != 25) throw new AssertionError("Need Java 25");
        long sum = 0;
        for (int i = 0; i < 10000; i++) sum += i;
        if (sum != 49995000L) throw new AssertionError("Arithmetic failed");
        Thread worker = new Thread(() -> System.out.println("THREAD_OK"));
        worker.start();
        worker.join();
        System.out.println("HELLO_JAVA_25 " + sum);
    }
}
