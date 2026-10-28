#!/usr/bin/env python3
"""Exercise explicit native storage builds against caller-provided unchanged Java libraries."""
from pathlib import Path
import argparse,subprocess
ROOT=Path(__file__).resolve().parents[1];JDK=Path('/Library/Java/JavaVirtualMachines/openjdk-25.jdk/Contents/Home')
p=argparse.ArgumentParser();p.add_argument('--jar',type=Path,required=True);p.add_argument('--zstd-namespace',required=True);p.add_argument('--sqlite-namespace',required=True);p.add_argument('--jdbc-protocol',required=True);a=p.parse_args();w=ROOT/'build/java25/native-storage/test';w.mkdir(parents=True,exist_ok=True)
source=r'''
import java.util.*;import java.io.*;import java.sql.*;import java.nio.file.*;
public class NativeStorageCheck {
 public static void main(String[]args)throws Exception {
  Class<?> zstd=Class.forName(args[0]+".Zstd");byte[] original=new byte[65549];new Random(112).nextBytes(original);
  byte[] compressed=(byte[])zstd.getMethod("compress",byte[].class,int.class).invoke(null,original,3);
  byte[] restored=(byte[])zstd.getMethod("decompress",byte[].class,int.class).invoke(null,compressed,original.length);if(!Arrays.equals(original,restored))throw new AssertionError("Zstd bytes");
  var bytes=new ByteArrayOutputStream();Class<?> out=Class.forName(args[0]+".ZstdOutputStream");try(var stream=(OutputStream)out.getConstructor(OutputStream.class).newInstance(bytes)){stream.write(original);}
  Class<?> in=Class.forName(args[0]+".ZstdInputStream");try(var stream=(InputStream)in.getConstructor(InputStream.class).newInstance(new ByteArrayInputStream(bytes.toByteArray()))){if(!Arrays.equals(original,stream.readAllBytes()))throw new AssertionError("Zstd stream");}
  Class<?> ctx=Class.forName(args[0]+".ZstdDecompressCtx");try(var context=(AutoCloseable)ctx.getConstructor().newInstance()){byte[] result=(byte[])ctx.getMethod("decompress",byte[].class,int.class).invoke(context,compressed,original.length);if(!Arrays.equals(original,result))throw new AssertionError("Zstd context");}
  Driver driver=(Driver)Class.forName(args[1]+".JDBC").getConstructor().newInstance();Path db=Path.of(args[3]);Files.deleteIfExists(db);String url="jdbc:"+args[2]+":"+db;
  try(Connection c=driver.connect(url,new Properties())){
   try(Statement s=c.createStatement()){s.execute("PRAGMA journal_mode=WAL");s.execute("CREATE TABLE blocks(id INTEGER PRIMARY KEY,payload BLOB)");}
   c.setAutoCommit(false);try(PreparedStatement s=c.prepareStatement("INSERT INTO blocks VALUES(?,?)")){s.setInt(1,1);s.setBytes(2,compressed);s.executeUpdate();}c.commit();
   try(Statement s=c.createStatement()){s.execute("INSERT INTO blocks VALUES(2,x'00')");}c.rollback();
  }
  try(Connection c=driver.connect(url,new Properties());Statement s=c.createStatement();ResultSet rows=s.executeQuery("SELECT id,payload FROM blocks")){if(!rows.next()||rows.getInt(1)!=1||!Arrays.equals(rows.getBytes(2),compressed)||rows.next())throw new AssertionError("SQLite rollback/blob persistence");}
  System.out.println("PASS original Java Zstd arrays/streams/contexts and SQLite JNI prepared statements,WAL,transaction rollback,BLOB persistence/reopen through explicitly built native libraries");
 }
}
'''
(w/'NativeStorageCheck.java').write_text(source);subprocess.run([str(JDK/'bin/javac'),'-d',str(w),str(w/'NativeStorageCheck.java')],check=True)
zstd=ROOT/'build/java25/native-storage'/('zstd-'+a.zstd_namespace+'-host/libzstd.dylib');sqlite=ROOT/'build/java25/native-storage'/('sqlite-'+a.sqlite_namespace+'-host/libsqlite.dylib')
flags=['-Xcheck:jni','-Xverify:all','--enable-native-access=ALL-UNNAMED','-DZstdNativePath='+str(zstd),'-D'+a.sqlite_namespace+'.lib.path='+str(sqlite.parent),'-D'+a.sqlite_namespace+'.lib.name='+sqlite.name]
command=[str(JDK/'bin/java'),*flags,'-cp',str(w)+':'+str(a.jar.resolve()),'NativeStorageCheck',a.zstd_namespace,a.sqlite_namespace,a.jdbc_protocol,str(w/'test.db')]
result=subprocess.run(command,capture_output=True,text=True,timeout=60);(w/'result.log').write_text(result.stdout+result.stderr);print(result.stdout+result.stderr);result.check_returncode()
for error in ['WARNING in native method','FATAL ERROR','Exception in thread']:assert error not in result.stdout+result.stderr,error
bad=[x if not x.startswith('-DZstdNativePath=')else'-DZstdNativePath='+str(w/'missing-library.dylib')for x in command];failed=subprocess.run(bad,capture_output=True,text=True,timeout=30);assert failed.returncode!=0 and 'UnsatisfiedLinkError'in failed.stderr
print('PASS forced missing-native test fails rather than using bundled/stock native fallback')
