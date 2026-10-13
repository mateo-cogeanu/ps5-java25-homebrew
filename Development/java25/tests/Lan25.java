import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Properties;

public class Lan25 {
    private static native void checkpoint(String stage);
    private static void trace(String stage) {
        if (Boolean.getBoolean("ps5.probe.networkTrace")) checkpoint("LAN: " + stage);
    }
    public static void main(String[] args) throws Exception {
        String stage = "read endpoint configuration";
        try {
            trace(stage);
            if (Runtime.version().feature()!=25) throw new AssertionError("Need Java 25");
            Properties config = new Properties();
            try (var input=Files.newInputStream(Path.of(System.getProperty("ps5.probe.config",
                    "/app0/assets/java25/probe.properties")))) {config.load(input);}
            String[] parts=config.getProperty("lan.host", "").split("\\.");
            if(parts.length!=4) throw new IOException("Expected numeric IPv4 LAN host");
            byte[] address=new byte[4];
            for(int i=0;i<4;i++) {int value=Integer.parseInt(parts[i]);if(value<0||value>255)throw new IOException("Invalid IPv4 host");address[i]=(byte)value;}
            InetAddress peer=InetAddress.getByAddress(address);
            if(peer.isAnyLocalAddress() || peer.isMulticastAddress() ||
               (peer.isLoopbackAddress()&&!Boolean.getBoolean("ps5.probe.allowLoopbackTest")))
                throw new IOException("LAN test needs another device's address");
            int port=Integer.parseInt(config.getProperty("lan.port"));
            if(port<1024||port>65535) throw new IOException("Invalid LAN port");
            byte[] payload="PS5 Java LAN: café / 日本語 / 🎮\n".getBytes(StandardCharsets.UTF_8);
            stage="TCP connect to configured Mac";trace(stage);
            try(Socket socket=new Socket()) {
                socket.connect(new InetSocketAddress(peer,port),4000);socket.setSoTimeout(4000);
                stage="TCP framed UTF-8 echo";trace(stage);
                DataOutputStream output=new DataOutputStream(socket.getOutputStream());
                output.writeInt(payload.length);output.write(payload);output.flush();
                DataInputStream input=new DataInputStream(socket.getInputStream());
                if(input.readInt()!=payload.length)throw new AssertionError("LAN TCP length");
                byte[] actual=new byte[payload.length];input.readFully(actual);
                if(!Arrays.equals(actual,payload))throw new AssertionError("LAN TCP bytes");
            }
            stage="UDP echo from configured Mac";trace(stage);
            try(DatagramSocket socket=new DatagramSocket()) {
                socket.setSoTimeout(4000);socket.connect(peer,port);
                socket.send(new DatagramPacket(payload,payload.length));
                byte[] bytes=new byte[payload.length+1];DatagramPacket reply=new DatagramPacket(bytes,bytes.length);
                socket.receive(reply);
                if(reply.getPort()!=port || !reply.getAddress().equals(peer) || reply.getLength()!=payload.length ||
                   !Arrays.equals(Arrays.copyOfRange(bytes,reply.getOffset(),reply.getOffset()+reply.getLength()),payload))
                    throw new AssertionError("LAN UDP source/bytes");
            }
            System.out.println("JAVA_LAN_OK TCP UDP");
        } catch(Throwable error) {
            throw new Exception("LAN stage "+stage+": "+error,error);
        }
    }
}
