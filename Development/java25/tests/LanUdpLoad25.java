import java.net.*;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public class LanUdpLoad25 {
    private static native void checkpoint(String stage);
    private static void trace(String stage){if(Boolean.getBoolean("ps5.probe.networkTrace"))checkpoint("LAN UDP load: "+stage);}
    public static void main(String[] args) throws Exception {
        int seconds=Integer.getInteger("ps5.probe.loadSeconds",60);
        if(seconds<1||seconds>600)throw new IllegalArgumentException("load duration");
        String stage="bind IPv4 UDP and wait for helper";
        try(DatagramSocket server=new DatagramSocket(new InetSocketAddress(InetAddress.getByAddress(new byte[4]),Integer.getInteger("ps5.probe.loadUdpPort",38031)))) {
            trace(stage);server.setSoTimeout(30000);
            byte[] hello="PS5_LAN_LOAD_UDP".getBytes(StandardCharsets.US_ASCII);
            DatagramPacket packet=new DatagramPacket(new byte[1024],1024);server.receive(packet);
            if(!Arrays.equals(hello,Arrays.copyOf(packet.getData(),packet.getLength())))throw new AssertionError("UDP hello");
            SocketAddress peer=packet.getSocketAddress();
            if(packet.getAddress().isLoopbackAddress()&&!Boolean.getBoolean("ps5.probe.allowLoopbackTest"))throw new AssertionError("External LAN peer required");
            server.send(new DatagramPacket(hello,hello.length,peer));server.setSoTimeout(5000);
            stage="verify 60-second UDP sequence and payload";trace(stage);
            int expected=0,duplicates=0;long start=System.nanoTime();
            while(true) {
                packet.setLength(1024);server.receive(packet);
                if(!packet.getSocketAddress().equals(peer))throw new AssertionError("UDP source changed");
                byte[] data=Arrays.copyOf(packet.getData(),packet.getLength());
                if(Arrays.equals(data,hello)){server.send(new DatagramPacket(hello,hello.length,peer));continue;}
                if(data.length<4)throw new AssertionError("UDP truncated sequence");
                int sequence=ByteBuffer.wrap(data).getInt();
                if(sequence==-1&&data.length==4)break;
                if(data.length!=516||(sequence!=expected&&sequence!=expected-1))throw new AssertionError("UDP sequence/size "+sequence+" expected "+expected);
                for(int i=4;i<data.length;i++)if(data[i]!=(byte)(sequence+i-4))throw new AssertionError("UDP byte "+i);
                if(sequence==expected)expected++;else duplicates++;
                server.send(new DatagramPacket(data,data.length,peer));
                if(System.nanoTime()-start>(seconds+15L)*1_000_000_000L)throw new AssertionError("Duration overrun");
            }
            long elapsed=(System.nanoTime()-start)/1_000_000;
            if(elapsed<seconds*1000L||expected<128)throw new AssertionError("Insufficient UDP duration/frames: "+elapsed+" / "+expected);
            byte[] summary=ByteBuffer.allocate(16).putInt(expected).putLong(elapsed).putInt(duplicates).array();
            server.send(new DatagramPacket(summary,summary.length,peer));
            stage="client final verification";trace(stage);
            packet.setLength(1024);server.receive(packet);
            if(!packet.getSocketAddress().equals(peer)||!Arrays.equals("MAC_UDP_VERIFIED".getBytes(StandardCharsets.US_ASCII),Arrays.copyOf(packet.getData(),packet.getLength())))throw new AssertionError("UDP final verification");
            System.out.println("JAVA_LAN_UDP_LOAD_OK seconds="+seconds+" roundTrips="+expected+" duplicates="+duplicates);
        }catch(Throwable error){throw new Exception("LAN UDP load stage "+stage+": "+error,error);}
    }
}
