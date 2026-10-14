import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.net.*;
import java.util.concurrent.atomic.AtomicReference;

public class Ipv625 {
    private static native void checkpoint(String stage);
    private static void trace(String stage) {
        if(Boolean.getBoolean("ps5.probe.networkTrace")) checkpoint("IPv6: "+stage);
    }
    public static void main(String[] args) throws Exception {
        String stage="construct IPv6 loopback";
        try {
            trace(stage);
            byte[] bytes=new byte[16];bytes[15]=1;
            InetAddress loop=Inet6Address.getByAddress(null,bytes,-1);
            if(!(loop instanceof Inet6Address))throw new AssertionError("IPv6 required");
            stage="bind IPv6 TCP listener";trace(stage);
            AtomicReference<Throwable> failure=new AtomicReference<>();
            try(ServerSocket server=new ServerSocket()) {
                server.bind(new InetSocketAddress(loop,0));server.setSoTimeout(5000);
                Thread worker=new Thread(()->{
                    try(Socket peer=server.accept()) {
                        peer.setSoTimeout(5000);
                        if(!(peer.getInetAddress() instanceof Inet6Address))throw new AssertionError("Not IPv6 peer");
                        int value=new DataInputStream(peer.getInputStream()).readInt();
                        new DataOutputStream(peer.getOutputStream()).writeInt(value^0x25AABBCC);
                    }catch(Throwable error){failure.set(error);}
                },"IPv6-echo");worker.setDaemon(true);worker.start();
                stage="connect and exchange IPv6 TCP";trace(stage);
                try(Socket client=new Socket()) {
                    client.connect(new InetSocketAddress(loop,server.getLocalPort()),5000);client.setSoTimeout(5000);
                    new DataOutputStream(client.getOutputStream()).writeInt(12345);
                    if(new DataInputStream(client.getInputStream()).readInt()!=(12345^0x25AABBCC))throw new AssertionError("IPv6 TCP bytes");
                }finally{server.close();worker.join(6000);}
                if(worker.isAlive())throw new AssertionError("IPv6 worker stuck");
                if(failure.get()!=null)throw new Exception("IPv6 worker",failure.get());
            }
            stage="IPv6 UDP request/reply";trace(stage);
            try(DatagramSocket a=new DatagramSocket(new InetSocketAddress(loop,0));
                DatagramSocket b=new DatagramSocket(new InetSocketAddress(loop,0))) {
                a.setSoTimeout(5000);b.setSoTimeout(5000);
                byte[] request={25,42,99};
                a.send(new DatagramPacket(request,request.length,loop,b.getLocalPort()));
                DatagramPacket packet=new DatagramPacket(new byte[4],4);b.receive(packet);
                if(!packet.getAddress().equals(loop)||packet.getPort()!=a.getLocalPort()||packet.getLength()!=3)
                    throw new AssertionError("IPv6 UDP source/size");
                b.send(new DatagramPacket(packet.getData(),packet.getLength(),packet.getSocketAddress()));
                a.receive(packet);
                if(packet.getPort()!=b.getLocalPort()||packet.getLength()!=3||packet.getData()[0]!=25||packet.getData()[1]!=42||packet.getData()[2]!=99)
                    throw new AssertionError("IPv6 UDP reply");
            }
            System.out.println("JAVA_IPV6_OK TCP UDP ::1 (LAN IPv6 not tested)");
        }catch(Throwable error){throw new Exception("IPv6 stage "+stage+": "+error,error);}
    }
}
