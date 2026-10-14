import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public class InboundUdp25 {
    private static native void checkpoint(String stage);
    private static void trace(String stage) {
        if(Boolean.getBoolean("ps5.probe.networkTrace"))checkpoint("Inbound UDP: "+stage);
    }
    public static void main(String[] args) throws Exception {
        String stage="prepare listener";
        try {
            trace(stage);
            if(Runtime.version().feature()!=25)throw new AssertionError("Need Java 25");
            int port=Integer.getInteger("ps5.probe.inboundUdpPort",38027);
            if(port<1024||port>65535)throw new IOException("Invalid UDP port");
            byte[] expected="Mac -> PS5 Java inbound: café / 日本語 / 🎮\n".getBytes(StandardCharsets.UTF_8);
            byte[] response=("PS5_UDP_ACK "+new String(expected,StandardCharsets.UTF_8)).getBytes(StandardCharsets.UTF_8);
            byte[] confirmation="MAC_UDP_VERIFIED".getBytes(StandardCharsets.US_ASCII);
            stage="bind on all IPv4 interfaces";trace(stage);
            try(DatagramSocket server=new DatagramSocket(new InetSocketAddress(port))) {
                server.setSoTimeout(25000);
                stage="receive Mac request";trace(stage);
                byte[] buffer=new byte[4096];DatagramPacket request=new DatagramPacket(buffer,buffer.length);
                server.receive(request);
                if(!Arrays.equals(expected,
                        Arrays.copyOfRange(buffer,request.getOffset(),request.getOffset()+request.getLength())))
                    throw new AssertionError("Inbound UDP source/bytes");
                stage="send acknowledgement and receive verification";trace(stage);
                server.setSoTimeout(5000);
                server.send(new DatagramPacket(response,response.length,request.getSocketAddress()));
                DatagramPacket verified=new DatagramPacket(new byte[128],128);server.receive(verified);
                if(!verified.getSocketAddress().equals(request.getSocketAddress())||!Arrays.equals(confirmation,
                        Arrays.copyOfRange(verified.getData(),verified.getOffset(),verified.getOffset()+verified.getLength())))
                    throw new AssertionError("Missing UDP client confirmation");
            }
            System.out.println("JAVA_INBOUND_UDP_OK");
        } catch(Throwable error){throw new Exception("Inbound UDP stage "+stage+": "+error,error);}
    }
}
