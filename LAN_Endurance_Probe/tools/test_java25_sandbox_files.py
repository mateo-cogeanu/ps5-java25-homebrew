#!/usr/bin/env python3
"""Test actual patched provider with host native operations; not console evidence."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
jdk=Path('/opt/homebrew/opt/openjdk@25/bin')
work=root/'build/java25/sandbox-files-test'
sources=work/'src';classes=work/'patch'
provider=sources/'sun/nio/fs/UnixFileSystemProvider.java'
provider.parent.mkdir(parents=True,exist_ok=True);classes.mkdir(parents=True,exist_ok=True)
provider.write_text((root/'.tools/java25/openjdk/src/java.base/unix/classes/sun/nio/fs/UnixFileSystemProvider.java').read_text())
subprocess.run([str(jdk/'javac'),'--patch-module','java.base='+str(sources),'-d',str(classes),str(provider)],check=True)
probe=work/'SandboxFilesTest.java'
probe.write_text('''import java.nio.file.*;
public class SandboxFilesTest {
 public static void main(String[] args) throws Exception {
  Path base=Files.createTempDirectory("ps5-delete-test-");
  try {
   Path file=Files.writeString(base.resolve("file"),"content");
   Path link=Files.createSymbolicLink(base.resolve("link"),file);
   Files.delete(link);
   if(!Files.exists(file)) throw new AssertionError("Followed symlink");
   Path dangling=Files.createSymbolicLink(base.resolve("dangling"),base.resolve("absent"));
   Files.delete(dangling);
   Path directory=Files.createDirectory(base.resolve("dir"));
   Path child=Files.writeString(directory.resolve("child"),"x");
   try { Files.delete(directory); throw new AssertionError("Deleted nonempty dir"); }
   catch(DirectoryNotEmptyException expected) {}
   Files.delete(child);Files.delete(directory);Files.delete(file);
   if(Files.deleteIfExists(file)) throw new AssertionError("Missing file deleted");
   try { Files.delete(file);throw new AssertionError("Missing file passed"); }
   catch(NoSuchFileException expected) {}
  } finally {Files.delete(base);}
  System.out.println("PASS: actual patched provider regular/directory/nonempty/symlink/missing semantics");
 }
}
''')
subprocess.run([str(jdk/'javac'),'-d',str(work),str(probe),str(root/'java25/tests/FileIO25.java')],check=True)
options=[str(jdk/'java'),'-Xint','--patch-module','java.base='+str(classes),'-Dsun.nio.fs.ps5Sandbox=true','-Dsun.nio.fs.chdirAllowed=true','-Duser.dir=/app0','-Djava.io.tmpdir='+str(work),'-cp',str(work)]
for name in ['SandboxFilesTest','FileIO25']:
 subprocess.run([*options,name],check=True)
