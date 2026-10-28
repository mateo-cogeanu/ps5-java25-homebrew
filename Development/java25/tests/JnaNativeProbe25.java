/* SPDX-License-Identifier: GPL-3.0-or-later */
import com.sun.jna.*;
/** Real JNA JNI memory, error state and libffi calls; no replacement classes. */
public final class JnaNativeProbe25 {
 public static void main(String[] args){
  if(Native.POINTER_SIZE!=8||Native.LONG_SIZE!=8)throw new AssertionError("Unexpected ABI");
  Native.setLastError(123);if(Native.getLastError()!=123)throw new AssertionError("native last error");
  try(Memory memory=new Memory(64)){
   memory.clear();memory.setLong(0,0x123456789abcdefL);if(memory.getLong(0)!=0x123456789abcdefL)throw new AssertionError("native memory");
   memory.setString(16,"native-jna");if(!memory.getString(16).equals("native-jna"))throw new AssertionError("string memory");
   if(args.length>0&&args[0].equals("host")){
    var process=NativeLibrary.getProcess();if(process.getFunction("strlen").invokeLong(new Object[]{memory.share(16)})!=10)throw new AssertionError("real ffi strlen");
    if(process.getFunction("abs").invokeInt(new Object[]{-73})!=73)throw new AssertionError("real ffi integer call");
    String source=System.getProperty("jnidispatch.path","");if(!source.contains("jna-host"))throw new AssertionError("Stock JNA fallback: "+source);
   }
  }
  System.out.println("PASS actual JNA JNI init/native sizes/error/memory/string"+(args.length>0?" and host libffi calls; forced newly built dispatch":"; PS5 native-bootstrap scope only"));
 }
}
