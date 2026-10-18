package ps5probe;

import java.lang.management.ManagementFactory;
import java.nio.file.Files;
import java.nio.file.Path;

/** Correctness and actual-compilation gate before a consumer starts heavy work. */
public final class JitWarmup25 {
 private static volatile long sink;
 private static final long[] EXPECTED={2737581264511284967L,1085936169014244694L,2602822462824950993L,1152881465267987655L,1874719589371966185L,-2880124599347481107L,630924335933383314L,-6768279547524641561L};
 private static long kernel(int seed){long x=seed;for(int i=0;i<64;i++)x=(x*1664525+1013904223)^(x>>>13);return x;}
 public static void check() throws Exception {
  var flags=ManagementFactory.getRuntimeMXBean().getInputArguments();
  if(!flags.contains("-Xmixed")||!flags.contains("-XX:TieredStopAtLevel=1")||!flags.contains("-XX:CICompilerCount=1"))throw new IllegalStateException("C1 gate requires mixed mode, level 1 and one compiler");
  var compiler=ManagementFactory.getCompilationMXBean();
  if(compiler==null)throw new IllegalStateException("Compiler unavailable");
  Path log=Path.of(System.getProperty("ps5.probe.jitLog","/download0/java25-jit.log"));
  if(Files.exists(log)&&Files.readString(log).contains("ps5probe.JitWarmup25::kernel"))throw new IllegalStateException("Warmup log already contains kernel; require fresh VM/session");
  System.out.println("JIT_WARMUP_BEGIN compiler="+compiler.getName());
  long deadline=System.nanoTime()+30_000_000_000L,calls=0;
  boolean compiled=false;
  do {
   for(int i=0;i<8192;i++){int seed=i&7;long result=kernel(seed);if(result!=EXPECTED[seed])throw new AssertionError("JIT kernel mismatch seed="+seed+" calls="+calls);sink=result;calls++;}
   if(Files.exists(log))for(String line:Files.readAllLines(log))if(line.contains("ps5probe.JitWarmup25::kernel")&&line.matches(".*\\s1\\s+ps5probe\\.JitWarmup25::kernel.*"))compiled=true;
   if(!compiled)Thread.sleep(20);
  }while(!compiled&&System.nanoTime()<deadline);
  if(!compiled)throw new IllegalStateException("No current-run level-1 kernel compilation in "+log);
  // Check compiled entry points after the compilation record, not just warmup.
  for(int i=0;i<32768;i++){int seed=i&7;long result=kernel(seed);if(result!=EXPECTED[seed])throw new AssertionError("Compiled kernel mismatch seed="+seed);sink=result;}
  System.out.println("JIT_WARMUP_OK level=1 checked="+(calls+32768)+" checksum="+sink);
 }
 public static void main(String[] args)throws Exception{check();}
}
