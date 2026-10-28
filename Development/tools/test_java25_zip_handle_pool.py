#!/usr/bin/env python3
"""Test actual target-built ZipFile classes under a real low descriptor limit."""
from pathlib import Path
import subprocess,resource,zipfile,shutil
r=Path(__file__).resolve().parents[1];w=r/'build/java25/zip-handle-test';w.mkdir(parents=True,exist_ok=True);jdk=Path('/Library/Java/JavaVirtualMachines/openjdk-25.jdk/Contents/Home');patch=w/'patch/java/util/zip';patch.mkdir(parents=True,exist_ok=True)
for p in (r/'.tools/java25/openjdk/build/ps5-bootstrap/jdk/modules/java.base/java/util/zip').glob('ZipFile*.class'):shutil.copy2(p,patch/p.name)
fixtures=w/'fixtures';fixtures.mkdir(exist_ok=True)
for i in range(300):
 with zipfile.ZipFile(fixtures/(str(i)+'.zip'),'w',compression=zipfile.ZIP_DEFLATED if i%2 else zipfile.ZIP_STORED)as z:z.writestr('data',bytes([(i+n)%251 for n in range(32769)]))
(w/'Check.java').write_text(r'''
import java.nio.file.*;import java.io.*;import java.util.*;import java.util.concurrent.*;import java.util.zip.*;import java.lang.reflect.*;
public class Check {
 static Field pool;
 static int size()throws Exception{Object p=pool.get(null);synchronized(p){return ((Map<?,?>)p).size();}}
 static void verify(ZipFile z,int number)throws Exception{try(InputStream in=z.getInputStream(z.getEntry("data"))){byte[] bytes=in.readAllBytes();if(bytes.length!=32769)throw new AssertionError("length");for(int n=0;n<bytes.length;n++)if((bytes[n]&255)!=(number+n)%251)throw new AssertionError("cross-handle data at "+n);}}
 public static void main(String[]args)throws Exception{
  Path root=Path.of(args[0]);var all=new ArrayList<ZipFile>();
  Class<?> source=Class.forName("java.util.zip.ZipFile$Source");pool=source.getDeclaredField("ps5OpenFiles");pool.setAccessible(true);
  for(int i=0;i<300;i++){all.add(new ZipFile(root.resolve(i+".zip").toFile()));if(size()>16)throw new AssertionError("budget");}
  if(args.length>1)throw new AssertionError("default unexpectedly opened all300 under96-fd limit");
  ExecutorService threads=Executors.newFixedThreadPool(6);List<Future<?>> jobs=new ArrayList<>();
  for(int t=0;t<6;t++){final int worker=t;jobs.add(threads.submit(()->{try{for(int n=0;n<150;n++){int id=(n*17+worker*31)%300;verify(all.get(id),id);}}catch(Exception e){throw new RuntimeException(e);}}));}
  for(var job:jobs)job.get();threads.shutdown();
  // A deep recursive world-like tree needs directory streams and real writes
  // while all300 logical archive sources and entry streams remain available.
  Path world=root.resolve("world");Path deep=world;for(int n=0;n<18;n++)deep=deep.resolve("d"+n);Files.createDirectories(deep);Files.writeString(deep.resolve("chunk.dat"),"saved");
  try(var paths=Files.walk(world)){if(paths.count()!=20)throw new AssertionError("walk");}
  if(!Files.readString(deep.resolve("chunk.dat")).equals("saved"))throw new AssertionError("world");
  try(var paths=Files.walk(world)){for(Path p:paths.sorted(Comparator.reverseOrder()).toList())Files.delete(p);}
  // Shared source references and an entry stream survive eviction/reopening.
  try(ZipFile duplicate=new ZipFile(root.resolve("0.zip").toFile());InputStream partial=all.get(0).getInputStream(all.get(0).getEntry("data"))){if(partial.read()!=0)throw new AssertionError();for(int n=1;n<80;n++)verify(all.get(n),n);byte[] remainder=partial.readAllBytes();if(remainder.length!=32768)throw new AssertionError();verify(duplicate,0);}
  verify(all.get(299),299);for(int n=1;n<80;n++)verify(all.get(n),n);
  Files.copy(root.resolve("1.zip"),root.resolve("299.zip"),StandardCopyOption.REPLACE_EXISTING);
  try{verify(all.get(299),299);throw new AssertionError("changed archive accepted");}catch(IOException expected){}
  // OPEN_DELETE preserves a real pinned descriptor and unlink semantics.
  Path deleted=root.resolve("delete.zip");Files.copy(root.resolve("2.zip"),deleted,StandardCopyOption.REPLACE_EXISTING);
  try(ZipFile z=new ZipFile(deleted.toFile(),ZipFile.OPEN_READ|ZipFile.OPEN_DELETE)){if(Files.exists(deleted))throw new AssertionError("OPEN_DELETE");verify(z,2);}
  Path broken=root.resolve("broken.zip");Files.writeString(broken,"broken");int before=size();try{new ZipFile(broken.toFile());throw new AssertionError("invalid ZIP");}catch(ZipException expected){}if(size()>before)throw new AssertionError("failed constructor leaked pool slot");Files.delete(broken);
  for(var z:all)z.close();if(size()!=0)throw new AssertionError("close leaked pool");
  System.out.println("PASS actual target ZipFile:300 simultaneous archives under96-fd cap,16-handle budget,stored/deflated byte checks,6 concurrent readers,partial streams/shared refs,deep world write/read/walk/delete,changed-file rejection,OPEN_DELETE,constructor cleanup and final release");
 }
}
''')
subprocess.run([str(jdk/'bin/javac'),'-d',str(w),str(w/'Check.java')],check=True)
base=[str(jdk/'bin/java'),'-XX:-MaxFDLimit','--patch-module','java.base='+str(w/'patch'),'--add-opens','java.base/java.util.zip=ALL-UNNAMED','-Xverify:all','-cp',str(w),'Check',str(fixtures)]
def limited():
 soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE);resource.setrlimit(resource.RLIMIT_NOFILE,(96,hard))
# First establish a real failure with the feature omitted.
old=subprocess.run([*base,'default'],capture_output=True,text=True,preexec_fn=limited,timeout=60);assert old.returncode!=0 and 'Too many open files'in old.stderr,old.stdout+old.stderr
subprocess.run([*base[:1],'-Dps5.zip.maxOpenFiles=16',*base[1:]],check=True,preexec_fn=limited,timeout=120)
print('PASS omitted-option control actually exhausts descriptors;default core policy unchanged')
