import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public class Ipv6Lan25 {
    private static native void checkpoint(String stage);
    private static void trace(String stage) {if(Boolean.getBoolean("ps5.probe.networkTrace"))checkpoint("IPv6 LAN: "+stage);}
    public static void main(String[] args) throws Exception {
        String stage="bind IPv6 wildcard TCP";
        try {
            trace(stage);
            InetAddress any=Inet6Address.getByAddress(null,new byte[16],-1);
            int tcp=Integer.getInteger("ps5.probe.ipv6TcpPort",38028),udp=Integer.getInteger("ps5.probe.ipv6UdpPort",38029);
            byte[] expected="Mac -> PS5 Java inbound: café / 日本語 / 🎮\n".getBytes(StandardCharsets.UTF_8);
            try(ServerSocket server=new ServerSocket()) {
                server.setReuseAddress(true);server.bind(new InetSocketAddress(any,tcp));server.setSoTimeout(30000);
                stage="accept actual IPv6 LAN client";trace(stage);
                try(Socket peer=server.accept()) {
                    peer.setSoTimeout(5000);
                    if(!(peer.getInetAddress() instanceof Inet6Address)||
                       (peer.getInetAddress().isLoopbackAddress()&&!Boolean.getBoolean("ps5.probe.allowLoopbackTest")))throw new AssertionError("Actual external IPv6 peer required");
                    var input=new DataInputStream(peer.getInputStream());var output=new DataOutputStream(peer.getOutputStream());
                    if(input.readInt()!=expected.length)throw new AssertionError("IPv6 frame size");
                    byte[] data=new byte[expected.length];input.readFully(data);if(!Arrays.equals(data,expected))throw new AssertionError("IPv6 TCP bytes");
                    byte[] reply=("PS5_TCP_ACK "+new String(expected,StandardCharsets.UTF_8)).getBytes(StandardCharsets.UTF_8);
                    output.writeInt(reply.length);output.write(reply);output.flush();
                    if(input.readInt()!=0x25ACCE55)throw new AssertionError("IPv6 TCP confirmation");
                }
            }
            stage="bind IPv6 UDP and receive LAN request";trace(stage);
            try(DatagramSocket server=new DatagramSocket(new InetSocketAddress(any,udp))) {
                server.setSoTimeout(30000);
                DatagramPacket request=new DatagramPacket(new byte[4096],4096);server.receive(request);
                if(!(request.getAddress() instanceof Inet6Address)||
                   (request.getAddress().isLoopbackAddress()&&!Boolean.getBoolean("ps5.probe.allowLoopbackTest")))throw new AssertionError("Actual external IPv6 UDP peer required");
                if(!Arrays.equals(expected,Arrays.copyOf(request.getData(),request.getLength())))throw new AssertionError("IPv6 UDP bytes");
                byte[] reply=("PS5_UDP_ACK "+new String(expected,StandardCharsets.UTF_8)).getBytes(StandardCharsets.UTF_8);
                server.send(new DatagramPacket(reply,reply.length,request.getSocketAddress()));
                server.setSoTimeout(5000);DatagramPacket verified=new DatagramPacket(new byte[128],128);server.receive(verified);
                if(!verified.getSocketAddress().equals(request.getSocketAddress())||!Arrays.equals("MAC_UDP_VERIFIED".getBytes(StandardCharsets.US_ASCII),Arrays.copyOf(verified.getData(),verified.getLength())))throw new AssertionError("IPv6 UDP confirmation");
            }
            System.out.println("JAVA_IPV6_LAN_OK actual IPv6 TCP UDP");
        }catch(Throwable error){throw new Exception("IPv6 LAN stage "+stage+": "+error,error);}
    }
}
