#!/usr/bin/env python3
"""Actual PS5-gated java.io File path policy against real host native metadata."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/relative-file-test';src=w/'src/java/io';src.mkdir(parents=True,exist_ok=True);classes=w/'patch';classes.mkdir(exist_ok=True)
p=src/'UnixFileSystem.java';p.write_text((r/'.tools/java25/openjdk/src/java.base/unix/classes/java/io/UnixFileSystem.java').read_text())
jdk=Path('/opt/homebrew/opt/openjdk@25/bin');subprocess.run([str(jdk/'javac'),'--patch-module','java.base='+str(w/'src'),'-d',str(classes),str(p)],check=True)
for d in ['root','cwd']:(w/d).mkdir(exist_ok=True)
f=w/'RelativeFileCheck.java';f.write_text('''import java.io.*;import java.nio.file.*;
public class RelativeFileCheck {
 public static void main(String[]args)throws Exception {
  Path root=Path.of(args[0]);boolean enabled=Boolean.parseBoolean(args[1]);Path data=root.resolve("whitelist.json");Files.writeString(data,"[]");
  File relative=new File("whitelist.json"),absolute=data.toFile();
  if(!relative.getPath().equals("whitelist.json"))throw new AssertionError("Mutated public path");
  if(!absolute.isFile()||absolute.length()!=2)throw new AssertionError("Absolute path changed");
  if(enabled){
   if(!relative.exists()||!relative.isFile()||!relative.canRead()||relative.length()!=2||relative.lastModified()!=absolute.lastModified())throw new AssertionError("Relative metadata not resolved to user.dir");
   File renamed=new File("moved.json");if(!relative.renameTo(renamed)||!renamed.exists()||relative.exists()||!renamed.delete())throw new AssertionError("Relative rename/delete mismatch");
  }else if(relative.exists()||relative.canRead()||relative.length()!=0)throw new AssertionError("Desktop cwd policy changed");
  Files.deleteIfExists(data);System.out.println("PASS: actual UnixFileSystem class, distinct cwd/user.dir, relative type/read/length/mtime/rename/delete, absolute and public paths preserved; PS5="+enabled);
 }
}''')
subprocess.run([str(jdk/'javac'),'-d',str(w),str(f)],check=True)
for enabled in [True,False]:
 subprocess.run([str(jdk/'java'),'-Xint','--patch-module','java.base='+str(classes),'-Dsun.nio.fs.ps5Sandbox='+str(enabled).lower(),'-Duser.dir='+str(w/'root'),'-cp',str(w),'RelativeFileCheck',str(w/'root'),str(enabled).lower()],cwd=w/'cwd',check=True)
