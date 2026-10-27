#!/usr/bin/env python3
"""Real headless ImageIO/ICC on a host JVM forced to use our genuine native subset."""
from pathlib import Path
import subprocess,json,hashlib
from PIL import Image
from java25_imageio import ROOT,JDK,build
out=build(host=True);work=ROOT/'build/java25/imageio-test';work.mkdir(parents=True,exist_ok=True)
for mode in ['RGBA','P','L','RGB']:
 im=Image.new(mode,(8,7))
 if mode=='P':im.putpalette([v for n in range(256)for v in (n,255-n,n//2)])
 for y in range(7):
  for x in range(8):im.putpixel((x,y),((x*31,y*37,(x+y)*17,255-x*9) if mode=='RGBA' else (x*31,y*37,(x+y)*17) if mode=='RGB' else (x*31+y*17)%256))
 im.save(work/(mode+'.png'))
(work/'ImageCheck.java').write_text(r'''
import java.nio.file.*;import java.io.*;import javax.imageio.*;import javax.imageio.stream.*;import java.awt.image.*;import java.awt.color.*;import java.security.*;import java.nio.*;
public class ImageCheck {
 public static void main(String[]a)throws Exception {
  if(a.length>1){var field=Class.forName("jdk.internal.loader.NativeLibraries$LibraryPaths").getDeclaredField("SYS_PATHS");field.setAccessible(true);String[] paths=(String[])field.get(null);java.util.Arrays.fill(paths,a[1]);}
  for(int cycle=0;cycle<3;cycle++)for(String mode:new String[]{"RGBA","P","L","RGB"}){
   byte[] body=Files.readAllBytes(Path.of(a[0],mode+".png"));BufferedImage image;
   try(var in=new MemoryCacheImageInputStream(new ByteArrayInputStream(body))){var readers=ImageIO.getImageReaders(in);if(!readers.hasNext())throw new AssertionError("missing PNG reader");var reader=readers.next();try{reader.setInput(in);image=reader.read(0);}finally{reader.dispose();}}
   if(image.getWidth()!=8||image.getHeight()!=7)throw new AssertionError("image dimensions");var bytes=ByteBuffer.allocate(8*7*4);for(int y=0;y<7;y++)for(int x=0;x<8;x++)bytes.putInt(image.getRGB(x,y));
   System.out.println(mode+" "+java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes.array())));
  }
  ICC_Profile p=ICC_Profile.getInstance(ColorSpace.CS_sRGB);byte[] data=p.getData();var copy=ICC_Profile.getInstance(data);if(copy.getNumComponents()!=3)throw new AssertionError("ICC round trip");
  float[] converted=ColorSpace.getInstance(ColorSpace.CS_GRAY).toRGB(new float[]{0.5f});if(converted.length!=3||converted[0]<0.5f||converted[0]>0.9f)throw new AssertionError("LCMS convert");
  try(var invalid=new MemoryCacheImageInputStream(new ByteArrayInputStream(new byte[]{1,2,3}))){if(ImageIO.getImageReaders(invalid).hasNext())throw new AssertionError("invalid image accepted");}
  System.out.println("PASS real PNG memory-stream/Disposer/raster/getRGB across RGBA,palette,gray,RGB,three cycles,ICC profile/LCMS conversion,malformed-input rejection;no GUI/toolkit/JPEG claim");
 }
}''')
subprocess.run([str(JDK/'bin/javac'),'--release','25','-d',str(work),str(work/'ImageCheck.java')],check=True)
command=[str(JDK/'bin/java'),'-Xcheck:jni','-Xverify:all','-Djava.awt.headless=true','-cp',str(work),'ImageCheck',str(work)]
reference=subprocess.check_output(command,text=True,stderr=subprocess.STDOUT)

# Host-only path isolation: make all non-AWT/LCMS base libraries available, then
# redirect the actual bootstrap NativeLibraries search array before ImageIO loads.
for lib in (JDK/'lib').glob('*.dylib'):
 if lib.name.startswith(('libawt','liblcms','libfontmanager')):continue
 dest=out/lib.name
 if not dest.exists():dest.symlink_to(lib)
custom=subprocess.run([command[0],'--add-opens=java.base/jdk.internal.loader=ALL-UNNAMED','-Xlog:library=debug:file='+str(work/'libraries.log'),*command[1:],str(out)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(work/'subset.log').write_text(custom.stdout);custom.check_returncode()
assert [l for l in reference.splitlines()if l.startswith(('RGBA ','P ','L ','RGB '))]==[l for l in custom.stdout.splitlines()if l.startswith(('RGBA ','P ','L ','RGB '))]
loaded=(work/'libraries.log').read_text();assert str(out/'libawt.dylib')in loaded and str(out/'liblcms.dylib')in loaded
assert str(JDK/'lib/libawt.dylib')not in loaded and str(JDK/'lib/liblcms.dylib')not in loaded
print(custom.stdout);print('PASS exact pixel hashes match stock JDK; library trace proves our subset loaded, no fallback awt/lcms')
