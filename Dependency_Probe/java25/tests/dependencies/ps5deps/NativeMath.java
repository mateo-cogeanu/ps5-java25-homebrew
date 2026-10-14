package ps5deps;
public class NativeMath {
 static {System.loadLibrary("ps5probe");}
 public static native long sum(byte[] bytes);
}
