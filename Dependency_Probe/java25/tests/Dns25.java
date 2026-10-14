import java.io.IOException;
import java.net.InetAddress;
import java.util.concurrent.atomic.AtomicReference;

public class Dns25 {
    private static native void checkpoint(String stage);
    public static void main(String[] args) throws Exception {
        if(Boolean.getBoolean("ps5.probe.networkTrace")) checkpoint("DNS: resolve example.com");
        AtomicReference<InetAddress[]> result=new AtomicReference<>();
        AtomicReference<Throwable> failure=new AtomicReference<>();
        Thread resolver=new Thread(()->{
            try {result.set(InetAddress.getAllByName("example.com"));}
            catch(Throwable error){failure.set(error);}
        },"Java25-DNS-probe");
        resolver.setDaemon(true);resolver.start();resolver.join(8000);
        if(resolver.isAlive()) throw new IOException("DNS lookup exceeded 8 seconds; close app before retry");
        if(failure.get()!=null) throw new IOException("DNS example.com: "+failure.get(),failure.get());
        InetAddress[] addresses=result.get();
        if(addresses==null||addresses.length==0)throw new IOException("DNS returned no addresses");
        for(InetAddress address:addresses)
            if(address.isAnyLocalAddress()||address.isLoopbackAddress())throw new IOException("DNS returned a local address");
        if(Runtime.version().feature()!=25)throw new AssertionError("Need Java 25");
        System.out.println("JAVA_DNS_OK "+addresses.length+" addresses");
    }
}
