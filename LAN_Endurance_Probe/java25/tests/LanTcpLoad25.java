import java.io.*;
import java.net.*;
import java.util.concurrent.atomic.*;

public class LanTcpLoad25 {
    private static native void checkpoint(String stage);
    private static void trace(String stage){if(Boolean.getBoolean("ps5.probe.networkTrace"))checkpoint("LAN TCP load: "+stage);}
    private static String describe(Throwable error){StringBuilder text=new StringBuilder();for(int i=0;error!=null&&i<6;i++){if(i>0)text.append(" | cause: ");text.append(error);error=error.getCause();}return text.toString();}
    public static void main(String[] args) throws Exception {
        int seconds=Integer.getInteger("ps5.probe.loadSeconds",60);
        if(seconds<1||seconds>600)throw new IllegalArgumentException("load duration");
        Socket[] peers=new Socket[4];Thread[] threads=new Thread[4];
        AtomicReference<Throwable> failure=new AtomicReference<>();AtomicInteger ids=new AtomicInteger();AtomicLong total=new AtomicLong();
        String stage="bind IPv4 wildcard listener";
        try(ServerSocket server=new ServerSocket()) {
            trace(stage);server.setReuseAddress(true);
            server.bind(new InetSocketAddress(InetAddress.getByAddress(new byte[4]),Integer.getInteger("ps5.probe.loadTcpPort",38030)),4);server.setSoTimeout(30000);
            stage="accept four external TCP clients";trace(stage);
            for(int w=0;w<4;w++) {
                Socket peer=server.accept();peers[w]=peer;
                threads[w]=new Thread(()->{
                    String phase="configure peer/read worker id";
                    try(peer) {
                        peer.setSoTimeout(5000);peer.setTcpNoDelay(true);
                        if(peer.getInetAddress().isLoopbackAddress()&&!Boolean.getBoolean("ps5.probe.allowLoopbackTest"))throw new AssertionError("External LAN peer required");
                        var input=new DataInputStream(peer.getInputStream());var output=new DataOutputStream(peer.getOutputStream());
                        final int id=input.readInt();if(id<0||id>3||(ids.getAndUpdate(mask->mask|(1<<id))&(1<<id))!=0)throw new AssertionError("Unique worker ids required");
                        byte[] data=new byte[4096];int expected=0;long start=System.nanoTime();
                        while(true) {
                            phase="worker "+id+" frame "+expected;
                            int sequence=input.readInt(),size=input.readInt();
                            if(sequence==-1&&size==0)break;
                            if(sequence!=expected||size!=data.length)throw new AssertionError("Frame sequence/size");
                            input.readFully(data);
                            for(int i=0;i<data.length;i++)if(data[i]!=(byte)(id*31+sequence+i))throw new AssertionError("Payload byte "+i);
                            output.writeInt(sequence);output.writeInt(size);output.write(data);output.flush();expected++;
                            if(System.nanoTime()-start>(seconds+15L)*1_000_000_000L)throw new AssertionError("Duration overrun");
                        }
                        long elapsed=(System.nanoTime()-start)/1_000_000;
                        if(elapsed<seconds*1000L||expected<128)throw new AssertionError("Insufficient duration/frames: "+elapsed+"ms / "+expected);
                        output.writeInt(expected);output.writeLong(elapsed);output.flush();
                        if(input.readInt()!=0x25ACCE55)throw new AssertionError("Client verification missing");
                        total.addAndGet(expected);
                    }catch(Throwable error){failure.compareAndSet(null,new IOException(phase+": "+describe(error),error));}
                },"LAN-load-"+w);threads[w].setDaemon(true);threads[w].start();
            }
            stage="verify 60-second concurrent LAN exchanges";trace(stage);
            long deadline=System.nanoTime()+(seconds+20L)*1_000_000_000L;
            for(Thread worker:threads){long remaining=(deadline-System.nanoTime())/1_000_000;if(remaining>0)worker.join(remaining);if(worker.isAlive())throw new AssertionError("Worker deadline");}
            if(failure.get()!=null)throw new Exception("LAN worker failed: "+describe(failure.get()),failure.get());
            if(ids.get()!=15)throw new AssertionError("Missing worker");
            System.out.println("JAVA_LAN_TCP_LOAD_OK seconds="+seconds+" workers=4 frames="+total.get()+" bytesEachDirection="+(total.get()*4096));
        }catch(Throwable error){throw new Exception("LAN TCP load stage "+stage+": "+describe(error),error);}
        finally{for(Socket peer:peers)if(peer!=null)try{peer.close();}catch(IOException ignored){}for(Thread t:threads)if(t!=null&&t.isAlive())t.join(6000);}
    }
}
