import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;

public class SystemClasspath25 {
 private static native void checkpoint(String stage);
 private static void trace(String stage){if(Boolean.getBoolean("ps5.probe.dependencyTrace"))checkpoint("SystemClasspath25: "+stage);}
 private static String describe(Throwable error){StringBuilder result=new StringBuilder();for(int i=0;error!=null&&i<8;i++){if(i>0)result.append(" | cause: ");result.append(error);error=error.getCause();}return result.toString();}
 public static void main(String[] args) throws Exception {
  String stage="locate packaged dependencies";
  try {
   trace(stage);
   Path jars=Path.of(System.getProperty("ps5.probe.dependencyDir","/app0/assets/java25/jars"));
   stage="system class path resolves JAR-only application";trace(stage);
   ClassLoader loader=ClassLoader.getSystemClassLoader();
   Class<?> app=Class.forName("ps5deps.Application",true,loader);
   if(app.getClassLoader()!=loader)throw new AssertionError("Not defined by system class loader");
   stage="system loader executes transitive dependencies";trace(stage);
   Object result=app.getMethod("run").invoke(null);
   if(!"DEPENDENCY_OK 4498500 café / 日本語 / 🎮".equals(result))throw new AssertionError("System class path result "+result);
   stage="missing dependency rejects resolution";trace(stage);
   try {Class.forName("ps5deps.AbsentDependency",true,loader);throw new AssertionError("Missing class accepted");}
   catch(ClassNotFoundException expected){}
   System.out.println("JAVA_SYSTEM_CLASSPATH_OK actual VM class path and missing-class rejection");
  }catch(Throwable error){throw new Exception("SystemClasspath25 stage "+stage+": "+describe(error),error);}
 }
}
