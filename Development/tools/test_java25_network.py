#!/usr/bin/env python3
"""Run the actual packaged loopback fixture repeatedly and check descriptor cleanup."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
CLASSES=ROOT/'build/java25/network-assets/java25/classes'
WORK=ROOT/'build/java25/network-host-test'
WORK.mkdir(parents=True,exist_ok=True)
source=WORK/'Network25HostTest.java'
source.write_text('''import java.lang.management.ManagementFactory;
import com.sun.management.UnixOperatingSystemMXBean;
public class Network25HostTest {
 public static void main(String[] args) throws Exception {
  UnixOperatingSystemMXBean os=(UnixOperatingSystemMXBean)ManagementFactory.getOperatingSystemMXBean();
  Network25.main(new String[0]); // Warm native libraries and selector implementation.
  long before=os.getOpenFileDescriptorCount();
  for(int i=0;i<3;i++) Network25.main(new String[0]);
  long after=os.getOpenFileDescriptorCount();
  if(after>before+1) throw new AssertionError("Network descriptors leaked: "+before+" -> "+after);
  for(Thread thread:Thread.getAllStackTraces().keySet())
   if(thread.isAlive() && thread.getName().equals("Java25-TCP-echo"))
    throw new AssertionError("Echo worker leaked");
  System.out.println("PASS: repeated TCP/UDP/NIO, worker termination, descriptor cleanup "+before+" -> "+after);
 }
}
''')
jdk=Path('/opt/homebrew/opt/openjdk@25/bin')
subprocess.run([str(jdk/'javac'),'-cp',str(CLASSES),'-d',str(WORK),str(source)],check=True)
result=subprocess.run([str(jdk/'java'),'-Xint','-Xms16m','-Xmx128m','-XX:+UseSerialGC',
                       '-XX:ActiveProcessorCount=2','-Djava.net.preferIPv4Stack=true',
                       '-cp',str(WORK)+':'+str(CLASSES),'Network25HostTest'],
                      text=True,capture_output=True,timeout=60)
print(result.stdout,end='')
if result.returncode:
    print(result.stderr,end='')
    raise SystemExit(result.returncode)
assert result.stdout.count('JAVA_NETWORK_OK TCP UDP NIO')==4
