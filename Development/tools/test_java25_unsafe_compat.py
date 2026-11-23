#!/usr/bin/env python3
"""Exercise the target-built legacy Unsafe bridge on a matching Java 25 host."""
import argparse, os, subprocess, tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--classes', type=Path, required=True)
parser.add_argument('--java-home', type=Path, default=Path(os.environ.get('JAVA25_BOOT_JDK', '/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')))
a = parser.parse_args()
source = r'''
import sun.misc.Unsafe;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
public class UnsafeCompatCheck {
 static final AtomicInteger count=new AtomicInteger();
 static class Once {static {count.incrementAndGet();}}
 static class Bad {static {if(true)throw new IllegalStateException("expected");}}
 static void check(boolean ok){if(!ok)throw new AssertionError();}
 public static void main(String[] args)throws Exception {
  var field=Unsafe.class.getDeclaredField("theUnsafe");field.setAccessible(true);Unsafe unsafe=(Unsafe)field.get(null);
  unsafe.ensureClassInitialized(String.class);check(count.get()==0);
  var errors=new ConcurrentLinkedQueue<Throwable>();var start=new CountDownLatch(1);var threads=new Thread[8];
  for(int i=0;i<threads.length;i++){threads[i]=new Thread(()->{try{start.await();unsafe.ensureClassInitialized(Once.class);}catch(Throwable t){errors.add(t);}});threads[i].start();}
  start.countDown();for(var thread:threads)thread.join();check(errors.isEmpty()&&count.get()==1);
  unsafe.ensureClassInitialized(Once.class);check(count.get()==1);
  unsafe.ensureClassInitialized(int.class);unsafe.ensureClassInitialized(String[].class);
  try{unsafe.ensureClassInitialized(null);throw new AssertionError();}catch(NullPointerException expected){}
  try{unsafe.ensureClassInitialized(Bad.class);throw new AssertionError();}catch(ExceptionInInitializerError expected){check(expected.getCause() instanceof IllegalStateException);}
  try{unsafe.ensureClassInitialized(Bad.class);throw new AssertionError();}catch(NoClassDefFoundError expected){}
  try{Unsafe.getUnsafe();throw new AssertionError();}catch(SecurityException expected){}
  System.out.println("PASS legacy binary call, concurrent initialization exactly once, primitive/array, null, initialization failure and existing access checks");
 }
}
'''
with tempfile.TemporaryDirectory(prefix='unsafe-compat-') as temporary:
    work = Path(temporary)
    (work/'UnsafeCompatCheck.java').write_text(source)
    patch = ['--patch-module', 'jdk.unsupported='+str(a.classes.resolve())]
    subprocess.run([str(a.java_home/'bin/javac'), *patch, '-d', str(work), str(work/'UnsafeCompatCheck.java')], check=True)
    command = [str(a.java_home/'bin/java'), '-Xverify:all', '-cp', str(work), 'UnsafeCompatCheck']
    baseline = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if baseline.returncode == 0 or 'NoSuchMethodError' not in baseline.stdout:
        raise RuntimeError('Expected unpatched Java 25 to reject the legacy binary call: '+baseline.stdout)
    subprocess.run([command[0], *patch, *command[1:]], check=True)
