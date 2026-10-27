#!/usr/bin/env python3
"""Exercise the actual UnixFileSystem move implementation with a denied preflight."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
JDK=Path('/Library/Java/JavaVirtualMachines/openjdk-25.jdk/Contents/Home')
s=(ROOT/'.tools/java25/openjdk/src/java.base/unix/classes/sun/nio/fs/UnixFileSystem.java').read_text()
# Inject only the PS5 access(W_OK) failure; rename and metadata stay host-native.
assert s.count('int errno = access(source, W_OK);')==1
s=s.replace('int errno = access(source, W_OK);','int errno = Boolean.getBoolean("test.deniedDirectoryAccess") ? EISDIR : access(source, W_OK);')
with tempfile.TemporaryDirectory(prefix='ps5-directory-move-')as folder:
 w=Path(folder);p=w/'src/sun/nio/fs/UnixFileSystem.java';p.parent.mkdir(parents=True);p.write_text(s)
 subprocess.run([str(JDK/'bin/javac'),'--patch-module','java.base='+str(w/'src'),'-d',str(w/'patch'),str(p)],check=True)
 test=w/'MoveCheck.java';test.write_text('''import java.nio.file.*;
public class MoveCheck {
 static void check(boolean b)throws Exception{if(!b)throw new AssertionError();}
 public static void main(String[]args)throws Exception{
  Path root=Path.of(args[0]);Files.createDirectories(root);Path live=root.resolve("live"),trash=root.resolve("trash"),world=live.resolve("game/saves/World/level.dat");Files.createDirectories(world.getParent());Files.writeString(world,"world");
  boolean ps5=Boolean.getBoolean("sun.nio.fs.ps5Sandbox");
  if(!ps5){try{Files.move(live,trash);throw new AssertionError("preflight not exercised");}catch(FileSystemException expected){check(Files.readString(world).equals("world"));}System.out.println("PASS desktop preflight preserved");return;}
  Files.move(live,trash);check(!Files.exists(live)&&Files.readString(trash.resolve("game/saves/World/level.dat")).equals("world"));Files.move(trash,live);check(Files.readString(world).equals("world"));
  Files.createDirectory(trash);Files.writeString(trash.resolve("keep"),"keep");try{Files.move(live,trash);throw new AssertionError("overwrote target");}catch(FileAlreadyExistsException expected){}check(Files.readString(world).equals("world")&&Files.readString(trash.resolve("keep")).equals("keep"));
  Files.delete(trash.resolve("keep"));Files.delete(trash);Files.createSymbolicLink(root.resolve("link"),live);Files.move(root.resolve("link"),root.resolve("moved-link"));check(Files.isSymbolicLink(root.resolve("moved-link"))&&Files.readString(world).equals("world"));
  try{Files.move(root.resolve("missing"),root.resolve("other"));throw new AssertionError();}catch(NoSuchFileException expected){}
  System.out.println("PASS actual PS5-gated directory move/undo with denied preflight; contents, conflicts, symbolic-link rename and missing-source semantics");
 }
}''')
 subprocess.run([str(JDK/'bin/javac'),'-d',str(w),str(test)],check=True)
 for ps5 in ('false','true'):
  subprocess.run([str(JDK/'bin/java'),'--patch-module','java.base='+str(w/'patch'),'-Dtest.deniedDirectoryAccess=true','-Dsun.nio.fs.ps5Sandbox='+ps5,'-cp',str(w),'MoveCheck',str(w/ps5)],check=True)
