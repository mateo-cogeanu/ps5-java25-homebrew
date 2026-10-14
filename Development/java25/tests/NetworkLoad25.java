import java.io.*;
import java.net.*;
import java.util.Arrays;
import java.util.concurrent.atomic.AtomicReference;

public class NetworkLoad25 {
    private static native void checkpoint(String stage);
    private static void trace(String stage) {
        if(Boolean.getBoolean("ps5.probe.networkTrace")) checkpoint("Network load: "+stage);
    }
    public static void main(String[] args) throws Exception {
        String stage="four concurrent TCP workers, 128 frames each";
        int workers=4,frames=128,size=4096;
        AtomicReference<Throwable> failure=new AtomicReference<>();
        Thread[] threads=new Thread[workers];
        try {
            trace(stage);
            InetAddress loop=InetAddress.getByAddress(new byte[]{127,0,0,1});
            for(int w=0;w<workers;w++) {
                final int id=w;
                threads[w]=new Thread(()->{
                    Thread echo=null;
                    try(ServerSocket server=new ServerSocket()) {
                        server.bind(new InetSocketAddress(loop,0));server.setSoTimeout(5000);
                        echo=new Thread(()->{
                            try(Socket peer=server.accept()) {
                                peer.setSoTimeout(5000);
                                var input=new DataInputStream(peer.getInputStream());var output=new DataOutputStream(peer.getOutputStream());
                                byte[] data=new byte[size];
                                for(int f=0;f<frames;f++) {
                                    if(input.readInt()!=size)throw new AssertionError("TCP length");
                                    input.readFully(data);output.writeInt(size);output.write(data);output.flush();
                                }
                            }catch(Throwable error){failure.compareAndSet(null,error);}
                        },"Load-echo-"+id);echo.setDaemon(true);echo.start();
                        try(Socket client=new Socket()) {
                            client.connect(new InetSocketAddress(loop,server.getLocalPort()),5000);client.setSoTimeout(5000);
                            var input=new DataInputStream(client.getInputStream());var output=new DataOutputStream(client.getOutputStream());
                            byte[] data=new byte[size],reply=new byte[size];
                            for(int f=0;f<frames;f++) {
                                for(int i=0;i<size;i++)data[i]=(byte)(id*31+f+i);
                                output.writeInt(size);output.write(data);output.flush();
                                if(input.readInt()!=size)throw new AssertionError("TCP reply size");input.readFully(reply);
                                if(!Arrays.equals(data,reply))throw new AssertionError("TCP worker "+id+" frame "+f);
                            }
                        }finally{server.close();echo.join(6000);}
                        if(echo.isAlive())throw new AssertionError("Echo worker stuck");
                    }catch(Throwable error){failure.compareAndSet(null,error);}
                },"Load-client-"+w);threads[w].setDaemon(true);threads[w].start();
            }
            long deadline=System.nanoTime()+60_000_000_000L;
            for(Thread thread:threads) {
                long remaining=(deadline-System.nanoTime())/1_000_000;
                if(remaining>0)thread.join(remaining);
                if(thread.isAlive())throw new AssertionError("TCP load deadline");
            }
            if(failure.get()!=null)throw new Exception("TCP load worker",failure.get());
            stage="256 verified UDP round trips";trace(stage);
            try(DatagramSocket a=new DatagramSocket(new InetSocketAddress(loop,0));
                DatagramSocket b=new DatagramSocket(new InetSocketAddress(loop,0))) {
                a.setSoTimeout(5000);b.setSoTimeout(5000);
                byte[] data=new byte[512];
                for(int f=0;f<256;f++) {
                    for(int i=0;i<data.length;i++)data[i]=(byte)(f+i);
                    a.send(new DatagramPacket(data,data.length,loop,b.getLocalPort()));
                    DatagramPacket packet=new DatagramPacket(new byte[513],513);b.receive(packet);
                    if(packet.getPort()!=a.getLocalPort()||!packet.getAddress().equals(loop)||packet.getLength()!=512||!Arrays.equals(data,Arrays.copyOf(packet.getData(),512)))throw new AssertionError("UDP request "+f);
                    b.send(new DatagramPacket(packet.getData(),packet.getLength(),packet.getSocketAddress()));a.receive(packet);
                    if(packet.getPort()!=b.getLocalPort()||!packet.getAddress().equals(loop)||packet.getLength()!=512||!Arrays.equals(data,Arrays.copyOf(packet.getData(),512)))throw new AssertionError("UDP reply "+f);
                }
            }
            System.out.println("JAVA_NETWORK_LOAD_OK TCP 4x128x4096 UDP 256x512 (loopback)");
        }catch(Throwable error){throw new Exception("Network load stage "+stage+": "+error,error);}
    }
}
