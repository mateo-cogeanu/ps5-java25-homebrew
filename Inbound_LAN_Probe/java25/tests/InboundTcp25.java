import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public class InboundTcp25 {
    private static native void checkpoint(String stage);
    private static void trace(String stage) {
        if(Boolean.getBoolean("ps5.probe.networkTrace"))checkpoint("Inbound TCP: "+stage);
    }
    public static void main(String[] args) throws Exception {
        String stage="prepare listener";
        try {
            trace(stage);
            if(Runtime.version().feature()!=25)throw new AssertionError("Need Java 25");
            int port=Integer.getInteger("ps5.probe.inboundTcpPort",38026);
            if(port<1024||port>65535)throw new IOException("Invalid TCP port");
            byte[] expected="Mac -> PS5 Java inbound: café / 日本語 / 🎮\n".getBytes(StandardCharsets.UTF_8);
            byte[] response=("PS5_TCP_ACK "+new String(expected,StandardCharsets.UTF_8)).getBytes(StandardCharsets.UTF_8);
            stage="bind/listen on all IPv4 interfaces";trace(stage);
            try(ServerSocket server=new ServerSocket()) {
                server.setReuseAddress(true);
                server.bind(new InetSocketAddress(port),1);
                server.setSoTimeout(25000);
                stage="accept LAN client";trace(stage);
                try(Socket peer=server.accept()) {
                    peer.setSoTimeout(5000);
                    stage="read framed UTF-8 request";trace(stage);
                    DataInputStream input=new DataInputStream(peer.getInputStream());
                    if(input.readInt()!=expected.length)throw new AssertionError("Inbound TCP frame length");
                    byte[] actual=new byte[expected.length];input.readFully(actual);
                    if(!Arrays.equals(actual,expected))throw new AssertionError("Inbound TCP bytes");
                    stage="write acknowledgement";trace(stage);
                    DataOutputStream output=new DataOutputStream(peer.getOutputStream());
                    output.writeInt(response.length);output.write(response);output.flush();
                    // Require the Mac to confirm it received and verified the full response.
                    stage="receive client verification";trace(stage);
                    if(input.readInt()!=0x25ACCE55)throw new AssertionError("Missing TCP client confirmation");
                }
            }
            System.out.println("JAVA_INBOUND_TCP_OK");
        } catch(Throwable error){throw new Exception("Inbound TCP stage "+stage+": "+error,error);}
    }
}
