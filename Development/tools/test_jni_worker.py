#!/usr/bin/env python3
"""Test native worker lifecycle against a real host JVM; leave a reusable fixture runner."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
WORK=ROOT/'build/java25/jni-worker-test';WORK.mkdir(parents=True,exist_ok=True)
java='''public class WorkerCheck {
 public static void main(String[] args)throws Exception {
  if (!Thread.currentThread().getName().equals("PS5-probe-worker"))throw new AssertionError("wrong thread");
  Thread.currentThread().setContextClassLoader(ClassLoader.getSystemClassLoader());
  if(Thread.currentThread().getContextClassLoader()!=WorkerCheck.class.getClassLoader())throw new AssertionError("context loader");
  boolean[] inherited={false};
  Thread child=new Thread(()->{inherited[0]=Thread.currentThread().getContextClassLoader()==WorkerCheck.class.getClassLoader();});
  child.start();child.join();if(!inherited[0])throw new AssertionError("inheritance");
 }
}'''
(WORK/'WorkerCheck.java').write_text(java)
subprocess.run([str(JDK/'bin/javac'),'-d',str(WORK),str(WORK/'WorkerCheck.java')],check=True)
runner=WORK/'jni-worker-check'
subprocess.run(['clang++','-std=c++17','-pthread','-fsanitize=undefined','-I'+str(ROOT/'java25/probe'),'-I'+str(JDK/'include'),'-I'+str(JDK/'include/darwin'),str(ROOT/'tools/test_jni_worker.cpp'),'-L'+str(JDK/'lib/server'),'-Wl,-rpath,'+str(JDK/'lib/server'),'-ljvm','-o',str(runner)],check=True)
subprocess.run([str(runner),'WorkerCheck','-Xint','-Xverify:all','-Djava.class.path='+str(WORK)],check=True)
print('Fixture runner:',runner)
