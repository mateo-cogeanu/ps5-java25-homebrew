package ps5deps;
import java.nio.charset.StandardCharsets;
import java.util.ServiceLoader;
import ps5deps.api.Greeting;
public class Application {
 public static String run() throws Exception {
  var providers=ServiceLoader.load(Greeting.class,Application.class.getClassLoader()).iterator();
  if(!providers.hasNext())throw new AssertionError("Missing service provider");
  Greeting greeting=providers.next();if(providers.hasNext())throw new AssertionError("Duplicate service provider");
  String resource;
  try(var input=Application.class.getResourceAsStream("/ps5deps/message.txt")) {
   if(input==null)throw new AssertionError("Missing dependency resource");
   resource=new String(input.readAllBytes(),StandardCharsets.UTF_8).strip();
  }
  if(!resource.equals(greeting.message()))throw new AssertionError("Service/resource mismatch");
  return "DEPENDENCY_OK "+Engine.calculate(3000)+" "+resource;
 }
}
