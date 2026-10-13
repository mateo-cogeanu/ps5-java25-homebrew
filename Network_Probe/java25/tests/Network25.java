import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.channels.SelectionKey;
import java.nio.channels.Selector;
import java.nio.channels.ServerSocketChannel;
import java.nio.channels.SocketChannel;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.security.Security;
import java.util.concurrent.atomic.AtomicReference;

public class Network25 {
    private static final int TIMEOUT = 4000;
    private static final byte[] PAYLOAD = "Java 25 network: café / 日本語 / 🎮\n".getBytes(StandardCharsets.UTF_8);

    private static native void checkpoint(String stage);

    private static void trace(String stage) {
        if (Boolean.getBoolean("ps5.probe.networkTrace")) checkpoint("Network: " + stage);
    }

    private static void check(boolean valid, String message) {
        if (!valid) throw new AssertionError(message);
    }

    private static void tcp(InetAddress loopback) throws Exception {
        AtomicReference<Throwable> workerFailure = new AtomicReference<>();
        AtomicReference<Throwable> firstFailure = new AtomicReference<>();
        try (ServerSocket server = new ServerSocket()) {
            server.bind(new InetSocketAddress(loopback, 0), 1);
            server.setSoTimeout(TIMEOUT);
            Thread worker = new Thread(() -> {
                String workerStage = "accept/configure accepted socket";
                try (Socket peer = server.accept()) {
                    peer.setSoTimeout(TIMEOUT);
                    DataInputStream input = new DataInputStream(peer.getInputStream());
                    workerStage = "read request header";
                    check(input.readInt() == PAYLOAD.length, "TCP server length");
                    byte[] actual = new byte[PAYLOAD.length];
                    workerStage = "read request bytes";
                    input.readFully(actual);
                    check(Arrays.equals(actual, PAYLOAD), "TCP server bytes");
                    workerStage = "write response";
                    DataOutputStream output = new DataOutputStream(peer.getOutputStream());
                    output.writeInt(actual.length);
                    output.write(actual);
                    output.flush();
                } catch (Throwable error) {
                    IOException tagged = new IOException("TCP server " + workerStage + ": " + error, error);
                    workerFailure.set(tagged);
                    firstFailure.compareAndSet(null, tagged);
                }
            }, "Java25-TCP-echo");
            worker.setDaemon(true);
            worker.start();
            Throwable clientFailure = null;
            try (Socket client = new Socket()) {
                client.connect(new InetSocketAddress(loopback, server.getLocalPort()), TIMEOUT);
                client.setSoTimeout(TIMEOUT);
                DataOutputStream output = new DataOutputStream(client.getOutputStream());
                output.writeInt(PAYLOAD.length);
                output.write(PAYLOAD);
                output.flush();
                DataInputStream input = new DataInputStream(client.getInputStream());
                check(input.readInt() == PAYLOAD.length, "TCP client length");
                byte[] actual = new byte[PAYLOAD.length];
                input.readFully(actual);
                check(Arrays.equals(actual, PAYLOAD), "TCP client bytes");
            } catch (Throwable error) {
                clientFailure = new IOException("TCP client: " + error, error);
                firstFailure.compareAndSet(null, clientFailure);
            } finally {
                server.close(); // Release accept on every client failure.
                worker.join(TIMEOUT + 1000L);
            }
            check(!worker.isAlive(), "TCP worker did not stop");
            Throwable first = firstFailure.get();
            if (first != null) {
                if (workerFailure.get() != null && workerFailure.get() != first)
                    first.addSuppressed(workerFailure.get());
                if (clientFailure != null && clientFailure != first)
                    first.addSuppressed(clientFailure);
                throw new IOException("TCP first failure: " + describe(first), first);
            }
        }
    }

    private static void udp(InetAddress loopback) throws Exception {
        try (DatagramSocket receiver = new DatagramSocket(new InetSocketAddress(loopback, 0));
             DatagramSocket sender = new DatagramSocket(new InetSocketAddress(loopback, 0))) {
            receiver.setSoTimeout(TIMEOUT);
            sender.setSoTimeout(TIMEOUT);
            sender.send(new DatagramPacket(PAYLOAD, PAYLOAD.length, loopback, receiver.getLocalPort()));
            byte[] bytes = new byte[PAYLOAD.length + 1];
            DatagramPacket request = new DatagramPacket(bytes, bytes.length);
            receiver.receive(request);
            check(request.getPort() == sender.getLocalPort(), "UDP source port");
            check(request.getLength() == PAYLOAD.length && Arrays.equals(
                    Arrays.copyOfRange(bytes, request.getOffset(), request.getOffset() + request.getLength()), PAYLOAD),
                    "UDP receiver bytes");
            receiver.send(new DatagramPacket(PAYLOAD, PAYLOAD.length, request.getSocketAddress()));
            DatagramPacket reply = new DatagramPacket(bytes, bytes.length);
            sender.receive(reply);
            check(reply.getPort() == receiver.getLocalPort(), "UDP reply port");
            check(reply.getLength() == PAYLOAD.length && Arrays.equals(
                    Arrays.copyOfRange(bytes, reply.getOffset(), reply.getOffset() + reply.getLength()), PAYLOAD),
                    "UDP sender bytes");
        }
    }

    private static void waitBefore(long deadline, String operation) throws Exception {
        if (System.nanoTime() >= deadline) throw new IOException("NIO deadline: " + operation);
        Thread.sleep(2);
    }

    private static void nio(InetAddress loopback) throws Exception {
        long deadline = System.nanoTime() + TIMEOUT * 1_000_000L;
        try (Selector selector = Selector.open(); ServerSocketChannel listener = ServerSocketChannel.open();
             SocketChannel client = SocketChannel.open()) {
            listener.configureBlocking(false);
            listener.bind(new InetSocketAddress(loopback, 0));
            client.configureBlocking(false);
            boolean connected = client.connect(listener.getLocalAddress());
            if (!connected) {
                client.register(selector, SelectionKey.OP_CONNECT);
                while (!client.finishConnect()) {
                    selector.select(25);
                    selector.selectedKeys().clear();
                    waitBefore(deadline, "connect");
                }
            }
            client.register(selector, SelectionKey.OP_READ);
            SocketChannel accepted;
            while ((accepted = listener.accept()) == null) waitBefore(deadline, "accept");
            try (SocketChannel peer = accepted) {
                peer.configureBlocking(false);
                ByteBuffer outgoing = ByteBuffer.wrap(PAYLOAD);
                while (outgoing.hasRemaining()) {
                    client.write(outgoing);
                    if (outgoing.hasRemaining()) waitBefore(deadline, "write request");
                }
                ByteBuffer incoming = ByteBuffer.allocate(PAYLOAD.length);
                while (incoming.hasRemaining()) {
                    if (peer.read(incoming) < 0) throw new IOException("NIO server EOF");
                    if (incoming.hasRemaining()) waitBefore(deadline, "read request");
                }
                check(Arrays.equals(incoming.array(), PAYLOAD), "NIO server bytes");
                incoming.flip();
                while (incoming.hasRemaining()) {
                    peer.write(incoming);
                    if (incoming.hasRemaining()) waitBefore(deadline, "write response");
                }
                ByteBuffer response = ByteBuffer.allocate(PAYLOAD.length);
                boolean readable = false;
                while (response.hasRemaining()) {
                    selector.select(25);
                    for (SelectionKey key : selector.selectedKeys()) {
                        if (key.isValid() && key.isReadable() && key.channel() == client) {
                            readable = true;
                            if (client.read(response) < 0) throw new IOException("NIO client EOF");
                        }
                    }
                    selector.selectedKeys().clear();
                    if (response.hasRemaining()) waitBefore(deadline, "selector read");
                }
                check(readable && Arrays.equals(response.array(), PAYLOAD), "NIO selected response bytes");
            }
        }
    }

    private static String describe(Throwable error) {
        StringBuilder text = new StringBuilder(error.toString());
        for (Throwable secondary : error.getSuppressed())
            text.append(" | secondary: ").append(secondary);
        Throwable cause = error.getCause();
        for (int depth = 0; cause != null && cause != error && depth < 3; depth++) {
            text.append(" | caused by: ").append(cause);
            cause = cause.getCause();
        }
        return text.toString();
    }

    public static void main(String[] args) throws Exception {
        String stage = "security configuration";
        try {
            trace(stage);
            check(Runtime.version().feature() == 25, "Need Java 25");
            check(Security.getProperty("security.provider.1") != null, "Missing security provider configuration");
            stage = "numeric IPv4 loopback";
            trace(stage);
            InetAddress loopback = InetAddress.getByAddress(new byte[]{127, 0, 0, 1});
            stage = "TCP client/server echo";
            trace(stage);
            tcp(loopback);
            stage = "UDP two-way datagrams";
            trace(stage);
            udp(loopback);
            stage = "NIO channels and selector";
            trace(stage);
            nio(loopback);
            System.out.println("JAVA_NETWORK_OK TCP UDP NIO");
        } catch (Throwable error) {
            throw new Exception("Network stage " + stage + ": " + describe(error), error);
        }
    }
}
