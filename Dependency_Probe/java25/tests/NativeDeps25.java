import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;

public class NativeDeps25 {
 private static native void checkpoint(String stage);
 private static void trace(String stage){if(Boolean.getBoolean("ps5.probe.dependencyTrace"))checkpoint("NativeDeps25: "+stage);}
 private static String describe(Throwable error){StringBuilder result=new StringBuilder();for(int i=0;error!=null&&i<8;i++){if(i>0)result.append(" | cause: ");result.append(error);error=error.getCause();}return result.toString();}
 public static void main(String[] args) throws Exception {
  String stage="locate packaged dependencies";
  try {
   trace(stage);
   Path jars=Path.of(System.getProperty("ps5.probe.dependencyDir","/app0/assets/java25/jars"));
   stage="System.loadLibrary discovers embedded JNI fixture";trace(stage);
   try(URLClassLoader loader=new URLClassLoader(new URL[]{jars.resolve("native.jar").toUri().toURL()},ClassLoader.getPlatformClassLoader())) {
    Class<?> math=Class.forName("ps5deps.NativeMath",true,loader);
    var sum=math.getMethod("sum",byte[].class);
    byte[] bytes=new byte[32768];long expected=0;
    for(int i=0;i<bytes.length;i++){bytes[i]=(byte)(i*31+7);expected+=(bytes[i]&255)*(long)(i+1);}
    stage="JNI byte-array transfer and native arithmetic";trace(stage);
    for(int i=0;i<8;i++)if(!Long.valueOf(expected).equals(sum.invoke(null,(Object)bytes)))throw new AssertionError("Native JNI result");
    stage="JNI exception propagation";trace(stage);
    try {sum.invoke(null,(Object)null);throw new AssertionError("Null JNI input accepted");}
    catch(java.lang.reflect.InvocationTargetException error){if(!(error.getCause() instanceof NullPointerException))throw error;}
   }
   stage="missing native library rejects loading";trace(stage);
   try {System.loadLibrary("ps5probe_missing");throw new AssertionError("Missing native library accepted");}
   catch(UnsatisfiedLinkError expected){}
   System.out.println("JAVA_NATIVE_DEPENDENCY_OK resident JNI discovery arrays arithmetic exceptions missing-library rejection");
  }catch(Throwable error){throw new Exception("NativeDeps25 stage "+stage+": "+describe(error),error);}
 }
}
