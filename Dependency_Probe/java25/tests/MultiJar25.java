import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;

public class MultiJar25 {
 private static native void checkpoint(String stage);
 private static void trace(String stage){if(Boolean.getBoolean("ps5.probe.dependencyTrace"))checkpoint("MultiJar25: "+stage);}
 private static String describe(Throwable error){StringBuilder result=new StringBuilder();for(int i=0;error!=null&&i<8;i++){if(i>0)result.append(" | cause: ");result.append(error);error=error.getCause();}return result.toString();}
 public static void main(String[] args) throws Exception {
  String stage="locate packaged dependencies";
  try {
   trace(stage);
   Path jars=Path.of(System.getProperty("ps5.probe.dependencyDir","/app0/assets/java25/jars"));
   stage="manifest Class-Path dependency resolution";trace(stage);
   try(URLClassLoader loader=new URLClassLoader(new URL[]{jars.resolve("application.jar").toUri().toURL()},ClassLoader.getPlatformClassLoader())) {
    Class<?> app=Class.forName("ps5deps.Application",true,loader);
    if(app.getClassLoader()!=loader)throw new AssertionError("Wrong defining loader");
    stage="cross-JAR classes, service provider and UTF-8 resource";trace(stage);
    Object result=app.getMethod("run").invoke(null);
    if(!"DEPENDENCY_OK 4498500 café / 日本語 / 🎮".equals(result))throw new AssertionError("Dependency result "+result);
    stage="resource enumeration and class-path order";trace(stage);
    var resources=loader.getResources("order.txt");
    for(String expected:new String[]{"application","dependency","api"}) {
     if(!resources.hasMoreElements())throw new AssertionError("Missing order resource");
     try(var input=resources.nextElement().openStream()) {if(!new String(input.readAllBytes(),StandardCharsets.UTF_8).strip().equals(expected))throw new AssertionError("Resource order");}
    }
    if(resources.hasMoreElements())throw new AssertionError("Unexpected resource");
   }
   System.out.println("JAVA_MULTI_JAR_OK manifest dependencies services resources order");
  }catch(Throwable error){throw new Exception("MultiJar25 stage "+stage+": "+describe(error),error);}
 }
}
