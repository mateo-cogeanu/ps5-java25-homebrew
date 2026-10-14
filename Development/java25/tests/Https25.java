import java.io.InputStream;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyStore;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;

public class Https25 {
    private static native void checkpoint(String stage);
    private static void trace(String stage) {
        if(Boolean.getBoolean("ps5.probe.networkTrace")) checkpoint("HTTPS: "+stage);
    }
    public static void main(String[] args) throws Exception {
        String stage="load bundled CA trust store";
        HttpsURLConnection connection=null;
        try {
            trace(stage);
            KeyStore store=KeyStore.getInstance("JKS");
            try(InputStream input=Files.newInputStream(Path.of(System.getProperty("ps5.probe.trustStore",
                    "/app0/assets/java25/lib/security/cacerts")))) {store.load(input,"changeit".toCharArray());}
            if(store.size()==0) throw new AssertionError("Empty CA store");
            stage="initialize trust managers and TLS context";trace(stage);
            TrustManagerFactory trust=TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
            trust.init(store);
            SSLContext context=SSLContext.getInstance("TLS");context.init(null,trust.getTrustManagers(),null);
            stage="connect HTTPS with certificate and hostname verification";trace(stage);
            URI uri=URI.create(System.getProperty("ps5.probe.httpsUrl","https://example.com/"));
            if(!uri.getScheme().equals("https")) throw new AssertionError("HTTPS required");
            connection=(HttpsURLConnection)uri.toURL().openConnection();
            connection.setSSLSocketFactory(context.getSocketFactory());
            connection.setConnectTimeout(10000);connection.setReadTimeout(10000);
            connection.setInstanceFollowRedirects(false);
            connection.setRequestProperty("User-Agent","PS5-Java25-Network-Probe/1");
            int code=connection.getResponseCode();
            if(code!=200) throw new AssertionError("HTTPS status "+code);
            String cipher=connection.getCipherSuite();
            if(cipher==null||cipher.contains("NULL")||connection.getServerCertificates().length==0)
                throw new AssertionError("No authenticated encryption");
            stage="read bounded HTTPS response";trace(stage);
            byte[] body;
            try(InputStream input=connection.getInputStream()) {body=input.readNBytes(65537);}
            if(body.length==0||body.length>65536) throw new AssertionError("Unexpected body size "+body.length);
            System.out.println("JAVA_HTTPS_OK status="+code+" cipher="+cipher+" bytes="+body.length);
        } catch(Throwable error) {throw new Exception("HTTPS stage "+stage+": "+error,error);}
        finally {if(connection!=null) connection.disconnect();}
    }
}
