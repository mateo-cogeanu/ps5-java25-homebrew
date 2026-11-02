#!/usr/bin/env python3
"""Force genuine OpenJDK jdk.management JNI in an isolated host image (macOS/JDK25).

Target-built Java classes are patched into a disposable host runtime. Only that
runtime's management_ext is replaced by the actual pinned OpenJDK C sources.
Library traces must resolve Flag natives to our library; removal must fail.
No PS5/OS telemetry/shader/heap-dump acceptance is implied. No installed JDK changes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
JAVA = r'''
import java.lang.management.ManagementFactory;
import com.sun.management.HotSpotDiagnosticMXBean;
public class ManagementExtensionsCheck {
 public static void main(String[] args){
  var bean=ManagementFactory.getPlatformMXBean(HotSpotDiagnosticMXBean.class);
  if(bean==null)throw new AssertionError("missing bean");
  var option=bean.getVMOption("UseFMA");
  if(!option.getValue().equals(args[0]))throw new AssertionError("wrong real flag");
  if(option.isWriteable())throw new AssertionError("UseFMA unexpectedly writeable");
  try{bean.getVMOption("PS5_No_Such_VM_Option");throw new AssertionError("fabricated option");}catch(IllegalArgumentException expected){}
  try{bean.setVMOption("UseFMA",args[0]);throw new AssertionError("readonly accepted");}catch(IllegalArgumentException expected){}
  if(Boolean.getBoolean("ps5.managementTest.denyMalloc")){
   try{
    Class<?> flag=Class.forName("com.sun.management.internal.Flag");
    var query=flag.getDeclaredMethod("getFlags",String[].class,int.class);query.setAccessible(true);
    String[] names=new String[16];java.util.Arrays.fill(names,"UseFMA");
    if(((java.util.List<?>)query.invoke(null,names,16)).size()!=16)throw new AssertionError("small boundary");
    try{query.invoke(null,new String[17],17);throw new AssertionError("large allocation not refused");}catch(java.lang.reflect.InvocationTargetException expected){if(!(expected.getCause()instanceof OutOfMemoryError))throw new AssertionError(expected);}
   }catch(ReflectiveOperationException failure){throw new AssertionError(failure);}

   try{bean.getDiagnosticOptions();throw new AssertionError("large query should retain refused heap allocation");}catch(OutOfMemoryError expected){}
   java.util.List<Thread> workers=new java.util.ArrayList<>();
   java.util.concurrent.atomic.AtomicReference<Throwable> failure=new java.util.concurrent.atomic.AtomicReference<>();
   for(int n=0;n<8;n++){Thread thread=new Thread(()->{try{for(int i=0;i<1000;i++)if(!bean.getVMOption("UseFMA").getValue().equals(args[0]))throw new AssertionError("concurrent value");}catch(Throwable t){failure.compareAndSet(null,t);}});workers.add(thread);thread.start();}
   for(Thread thread:workers)try{thread.join();}catch(InterruptedException t){throw new AssertionError(t);}
   if(failure.get()!=null)throw new AssertionError(failure.get());
  }else if(bean.getDiagnosticOptions()==null)throw new AssertionError("missing options");
  String client=System.getProperty("ps5.managementTest.class");
  if(client!=null){
   try{
    Class<?> type=Class.forName(client);
    var field=type.getDeclaredField(System.getProperty("ps5.managementTest.field"));field.setAccessible(true);
    if(field.getBoolean(null)!=Boolean.parseBoolean(args[0]))throw new AssertionError("Client flag mismatch");
    System.out.println("PASS original consumer initializer and real VM flag");
   }catch(ReflectiveOperationException failure){throw new AssertionError(failure);}
  }
  System.out.println("PASS genuine diagnostic MXBean UseFMA="+option.getValue()+"; unknown/readonly refused");
 }
}
'''


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--java-home',type=Path,required=True)
 p.add_argument('--cc',type=Path,required=True)
 p.add_argument('--deny-flag-malloc',action='store_true',help='Exercise actual PS5 small-query branch with only Flag.c malloc denied')
 p.add_argument('--class-path',default='',help='Explicit optional original consumer test dependencies; never packaged')
 p.add_argument('--initialize-class',help='Optional original consumer class initializer to exercise')
 p.add_argument('--boolean-field',help='Its static boolean result, compared with actual UseFMA')
 p.add_argument('--output-dir',type=Path,default=ROOT/'build/java25/management-extensions-host-check')
 a=p.parse_args();jdk=a.java_home.resolve();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
 if platform.system()!='Darwin':raise SystemExit('This manual JNI test currently requires macOS; other hosts/PS5 are separate checks')
 if bool(a.initialize_class)!=bool(a.boolean_field):p.error('--initialize-class and --boolean-field must be paired')
 if a.initialize_class and (not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_.$]*',a.initialize_class)or not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*',a.boolean_field)):p.error('Invalid class/field name')
 version=subprocess.check_output([str(jdk/'bin/java'),'-version'],stderr=subprocess.STDOUT,text=True)
 if not re.search(r'version "25[.\"]',version):raise SystemExit('Complete JDK25 required')
 src=ROOT/'.tools/java25/openjdk/src';build=ROOT/'.tools/java25/openjdk/build/ps5-bootstrap'
 module=build/'jdk/modules/jdk.management';assert (module/'com/sun/management/HotSpotDiagnosticMXBean.class').is_file(),'Build target jdk.management-java first'
 units=[*sorted((src/'jdk.management/share/native/libmanagement_ext').glob('*.c')),src/'jdk.management/unix/native/libmanagement_ext/OperatingSystemImpl.c',src/'jdk.management/macosx/native/libmanagement_ext/UnixOperatingSystem.c']
 incs=[jdk/'include',jdk/'include/darwin',src/'java.base/share/native/libjava',src/'java.base/unix/native/libjava',src/'hotspot/share/include',src/'hotspot/os/posix/include',src/'jdk.management/share/native/libmanagement_ext',build/'support/headers/jdk.management']
 with tempfile.TemporaryDirectory(prefix='management-ext-forced-')as tmp:
  work=Path(tmp);runtime=work/'runtime';library=work/'libmanagement_ext.dylib'
  compile_flags=['-std=c11','-D_ALLBSD_SOURCE',*['-I'+str(x)for x in incs]]
  if a.deny_flag_malloc:
   wrapped=work/'flag.o'
   subprocess.run([str(a.cc),*compile_flags,'-D__PROSPERO__','-Dmalloc=ps5_test_flag_malloc','-c',str(next(x for x in units if x.name=='Flag.c')),'-o',str(wrapped)],check=True)
   bridge=work/'refuse.c';bridge.write_text('#include <stdlib.h>\nvoid *ps5_test_flag_malloc(size_t bytes){(void)bytes;return NULL;}\n')
   native_inputs=[str(x)for x in units if x.name!='Flag.c']+[str(wrapped),str(bridge)]
  else:native_inputs=list(map(str,units))
  subprocess.run([str(a.cc),*compile_flags,'-dynamiclib','-undefined','dynamic_lookup',*native_inputs,'-o',str(library)],check=True)
  subprocess.run([str(jdk/'bin/jlink'),'--add-modules','java.base,java.management,jdk.management','--output',str(runtime),'--strip-debug','--no-header-files','--no-man-pages'],check=True)
  installed=runtime/'lib/libmanagement_ext.dylib';shutil.copyfile(library,installed)
  java=work/'ManagementExtensionsCheck.java';java.write_text(JAVA)
  subprocess.run([str(jdk/'bin/javac'),'-d',str(work),str(java)],check=True)
  logs=[]
  for enabled in [False,True]:
   command=[str(runtime/'bin/java'),'-Xcheck:jni','--add-opens=jdk.management/com.sun.management.internal=ALL-UNNAMED',*(['-Dps5.managementTest.denyMalloc=true']if a.deny_flag_malloc else []),'-XX:'+('+'if enabled else'-')+'UseFMA','-Xlog:library=debug','--patch-module','jdk.management='+str(module),*(['-Dps5.managementTest.class='+a.initialize_class,'-Dps5.managementTest.field='+a.boolean_field]if a.initialize_class else []),'-cp',str(work)+(':'+a.class_path if a.class_path else ''),'ManagementExtensionsCheck',str(enabled).lower()]
   result=subprocess.run(command,capture_output=True,text=True,timeout=45);text=result.stdout+result.stderr;name='fma-'+str(enabled).lower();(out/(name+'.log')).write_text(text)
   assert result.returncode==0 and 'PASS genuine diagnostic MXBean'in text,text[-3000:]
   if a.initialize_class:assert 'PASS original consumer initializer and real VM flag'in text
   loaded=re.findall(r'Loaded library ([^\n]+libmanagement_ext.dylib), handle (0x[0-9a-f]+)',text)
   assert len(loaded)==1 and Path(loaded[0][0]).resolve()==installed.resolve(),'Stock extension fallback'
   handle=loaded[0][1]
   for symbol in ['Java_com_sun_management_internal_Flag_initialize','Java_com_sun_management_internal_Flag_getFlags']:
    assert 'Found '+symbol+' in library with handle '+handle in text,'Our JNI not used: '+symbol
   assert 'WARNING in native method'not in text and 'FATAL ERROR in native method'not in text
   logs.append(name);print('PASS forced original management_ext UseFMA='+str(enabled).lower(),flush=True)
  installed.unlink()
  result=subprocess.run(command,capture_output=True,text=True,timeout=45);text=result.stdout+result.stderr;(out/'missing-library.log').write_text(text)
  assert result.returncode!=0 and 'UnsatisfiedLinkError'in text and 'management_ext'in text,'Missing custom library silently fell back'
  audit={'scope':'Actual target-built jdk.management Java + genuine OpenJDK native extension, real host JMM; isolated host-only image. No stock management_ext fallback; stock host java.management core intentionally retained.','source_sha256':{str(x.relative_to(src)):hashlib.sha256(x.read_bytes()).hexdigest()for x in units},'target_class_sha256':{str(x.relative_to(module)):hashlib.sha256(x.read_bytes()).hexdigest()for x in module.rglob('*.class')},'library_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'flag_malloc_denied':a.deny_flag_malloc,'checks':logs+['missing-native refusal','unknown flag refusal','readonly setter refusal','Xcheck:jni'],'ps5':'Not executed; native provider/flag/shader behavior pending'}
  (out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 print('PASS genuine extension JNI/real flag values/default query and refusal controls; PS5 pending')


if __name__=='__main__':main()
